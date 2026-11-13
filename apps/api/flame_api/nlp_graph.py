"""D1: turn NLP records into unreviewed, association-only edges in the knowledge graph.

    python -m flame_api.nlp_graph build

Only what two stored NLP records say together, by position, with the evidence ID of the chunk they were read from
(`extraction_method = "nlp_extraction"`). Nothing here is a claim that the report *reports* the investigation's result:

| Edge | When | `properties.basis` |
|---|---|---|
| investigation `ran_on` platform | one investigation and a platform are named in the same chunk | `co_occurrence_in_chunk` |
| investigation `measured_with` instrument | one investigation and an instrument are named in the same chunk | `co_occurrence_in_chunk` |
| document `describes` investigation | a document that is not dataset documentation names exactly one investigation on its first page | `named_in_document` |

A chunk that names two or more investigations is **ambiguous**: no edge is written, because the platform or instrument cannot be
tied to one of them. An investigation the graph does not already know is skipped, never created: the tables are the authority for
which investigations exist. Edge confidence is the lower of the two records' confidences. Rejected and superseded records
produce nothing; a human's review of an edge survives a rebuild (the same rules as the table-derived edges).
"""
from __future__ import annotations

import json
import logging
import sys
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from flame_api import knowledge_graph as kg
from flame_api.models import DocumentChunk, DocumentRecord, KnowledgeEntity, NlpRecordRow

logger = logging.getLogger("flame_api.nlp_graph")

NLP_METHOD = "nlp_extraction"
NLP_EXTRACTOR_VERSION = "nlp-cooccurrence-1.0.0"
LIVE = ("machine_extracted", "human_verified")
_EDGE_FOR = {"platform": "ran_on", "instrument": "measured_with"}
TABLE_DOCUMENTED = "dataset_documentation"   # its `describes` edges come from the ISA-Tab tables already


def _find_investigation(session: Session, name: str) -> str | None:
    """The live entity ID for an investigation name the graph already holds (id, then alias), else None."""
    identifier = kg.entity_id("investigation", name)
    entity = kg.resolve(session, identifier)
    if entity is not None:
        return entity.entity_id
    wanted = kg.canonical(name)
    for candidate in session.scalars(select(KnowledgeEntity).where(KnowledgeEntity.entity_type == "investigation",
                                                                   KnowledgeEntity.merged_into.is_(None))):
        if any(kg.canonical(alias) == wanted for alias in candidate.aliases or []):
            return candidate.entity_id
    return None


def build_nlp_edges(session: Session, knowledge_version: str | None = None) -> dict[str, int]:
    """(Re)build the NLP-derived edges from the live NLP records. Commits."""
    if knowledge_version is None:
        from flame_api.knowledge_version import current_knowledge_version

        knowledge_version = current_knowledge_version(session)
    builder = kg._Builder(session, knowledge_version)
    rows = session.execute(
        select(NlpRecordRow, DocumentChunk).join(DocumentChunk, DocumentChunk.chunk_id == NlpRecordRow.chunk_id)
        .where(NlpRecordRow.review_status.in_(LIVE),
               NlpRecordRow.record_type.in_(("investigation", "platform", "instrument")))
        .order_by(NlpRecordRow.document_id, NlpRecordRow.page, NlpRecordRow.chunk_id, NlpRecordRow.char_start)).all()
    chunks: dict[str, dict] = defaultdict(lambda: {"investigation": {}, "platform": {}, "instrument": {}})
    for record, chunk in rows:
        group = chunks[chunk.chunk_id]
        group["chunk"] = chunk
        # the highest confidence wins when the same name is found twice in one chunk
        names = group[record.record_type]
        names[record.normalized] = max(names.get(record.normalized, 0.0), record.confidence)
    documents = {d.document_id: d for d in session.scalars(select(DocumentRecord))}
    describes_seen: set[tuple[str, str]] = set()
    for chunk_id, group in sorted(chunks.items()):
        chunk, investigations = group["chunk"], group["investigation"]
        if not investigations:
            continue
        targets = group["platform"] or group["instrument"]
        if len(investigations) > 1:
            if targets:
                builder.counts["ambiguous_chunks"] += 1
            continue
        [(name, confidence)] = investigations.items()
        investigation = _find_investigation(session, name)
        if investigation is None:
            builder.counts["investigation_not_in_graph"] += 1
            continue
        for record_type, predicate in _EDGE_FOR.items():
            for target_name, target_confidence in group[record_type].items():
                target = builder.entity(record_type, target_name, evidence_ids=[chunk.evidence_id], alias=None)
                builder.edge(investigation, predicate, target, chunk.evidence_id,
                             {"basis": "co_occurrence_in_chunk", "chunk_id": chunk_id, "page": chunk.page},
                             confidence=min(confidence, target_confidence))
        document = documents.get(chunk.document_id)
        if (document is not None and chunk.page == 1 and document.document_type != TABLE_DOCUMENTED
                and (document.document_id, investigation) not in describes_seen):
            describes_seen.add((document.document_id, investigation))
            node = builder.entity("document", document.document_id, source_id=document.source_id,
                                  properties={"document_id": document.document_id, "title": document.title},
                                  evidence_ids=[chunk.evidence_id], alias="")
            builder.edge(node, "describes", investigation, chunk.evidence_id,
                         {"basis": "named_in_document", "chunk_id": chunk_id, "page": chunk.page}, confidence=confidence)
    builder.write_edges(NLP_METHOD, NLP_EXTRACTOR_VERSION)
    session.commit()
    counts = dict(builder.counts)
    logger.info("nlp_graph_built %s", json.dumps(counts, sort_keys=True))
    return counts


def main(argv: list[str]) -> int:
    from flame_api.database import SessionLocal

    logging.basicConfig(level=logging.INFO)
    if argv[:1] != ["build"]:
        print("usage: python -m flame_api.nlp_graph build")
        return 2
    with SessionLocal() as session:
        print(json.dumps(build_nlp_edges(session), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
