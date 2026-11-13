"""D1: run the source-linked NLP extractors over ingested chunks and store the records.

    python -m flame_api.nlp_extract run [--document-id ID]
    python -m flame_api.nlp_extract status

Records are candidates (`machine_extracted`). A human's `human_verified` / `rejected` decision survives a re-run; a changed
chunk, a new extractor version or a deleted chunk marks the old records `superseded`, never edits them.

The extractors read `DocumentChunk.text`, the normalised index text (ai/rag/ingestion/normalize.py): offsets are relative to it.
"""
from __future__ import annotations

import logging
import sys
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ai.rag.nlp.figures import associate_captions
from ai.rag.nlp.pipeline import DERIVED_EXTRACTORS, default_extractors, extract_chunk
from ai.rag.nlp.records import ChunkInput, Extractor, NlpRecord
from ai.rag.nlp.vocab import load_vocabulary
from flame_api.models import DocumentChunk, KnowledgeEntity, NlpRecordRow

logger = logging.getLogger("flame_api.nlp_extract")
PROTECTED = frozenset({"human_verified", "rejected"})
MIN_NAME_CHARS = 3
_VOCAB_TYPES = {"fuel": "fuel", "phenomenon": "phenomenon", "investigation": "investigation"}


def _now() -> datetime:
    return datetime.now(UTC)


def graph_vocabulary(session: Session) -> dict[str, dict[str, list]]:
    """Names the graph already knows (fuels, phenomena, investigations), so the vocabulary never drifts from it.

    An investigation is keyed by its display name (`FLEX`) and matched only in that case: names such as SAME are also words.
    """
    vocabulary: dict[str, dict[str, list]] = {}
    entities = session.scalars(select(KnowledgeEntity).where(KnowledgeEntity.entity_type.in_(_VOCAB_TYPES),
                                                             KnowledgeEntity.merged_into.is_(None)))
    for entity in entities:
        record_type = _VOCAB_TYPES[entity.entity_type]
        display = (entity.properties or {}).get("display_name") or entity.canonical_name
        names = [n for n in dict.fromkeys([display, *(entity.aliases or [])]) if len(n) >= MIN_NAME_CHARS]
        if not names:
            continue
        if record_type == "investigation":
            vocabulary.setdefault(record_type, {})[display] = [{"text": n, "case_sensitive": True} for n in names]
        else:
            vocabulary.setdefault(record_type, {})[entity.canonical_name] = names
    return vocabulary


def build_extractors(session: Session) -> list[Extractor]:
    return default_extractors(load_vocabulary(graph_vocabulary(session)))


def _chunk_input(chunk: DocumentChunk) -> ChunkInput:
    parts = chunk.chunk_id.split(":")
    return ChunkInput(chunk.chunk_id, chunk.document_id, parts[1] if len(parts) > 1 else "v1", chunk.page, chunk.text)


def persist(session: Session, records: list[NlpRecord]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    now = _now()
    for record in records:
        row = session.get(NlpRecordRow, record.record_id)
        values = {**record.model_dump(exclude={"review_status"}), "updated_at": now}
        if row is None:
            session.add(NlpRecordRow(record_id=record.record_id, review_status=record.review_status, created_at=now, **values))
            counts["created"] += 1
        else:
            for key, value in values.items():
                setattr(row, key, value)
            if row.review_status not in PROTECTED:
                row.review_status = record.review_status   # also revives a superseded row that reappeared
            counts["updated"] += 1
    session.flush()
    return dict(counts)


def reconcile(session: Session, document_id: str, ran: set[str], produced_ids: set[str]) -> int:
    """Supersede this document's live rows from extractors that ran and did not produce them again."""
    rows = session.scalars(select(NlpRecordRow).where(
        NlpRecordRow.document_id == document_id, NlpRecordRow.extractor.in_(ran), NlpRecordRow.review_status != "superseded"))
    stale = [row for row in rows if row.record_id not in produced_ids]
    for row in stale:
        row.review_status = "superseded"
        row.updated_at = _now()
    return len(stale)


def supersede_missing_chunks(session: Session) -> int:
    result = session.execute(update(NlpRecordRow).where(
        NlpRecordRow.review_status != "superseded", ~NlpRecordRow.chunk_id.in_(select(DocumentChunk.chunk_id)),
    ).values(review_status="superseded", updated_at=_now()))
    return result.rowcount or 0


def run(session: Session, *, document_id: str | None = None) -> dict[str, int]:
    extractors = build_extractors(session)
    ran = {e.name for e in extractors} | set(DERIVED_EXTRACTORS)
    counts: Counter[str] = Counter()
    query = select(DocumentChunk.document_id).distinct().order_by(DocumentChunk.document_id)
    for doc in ([document_id] if document_id else session.scalars(query).all()):
        records: list[NlpRecord] = []
        chunks = session.scalars(select(DocumentChunk).where(DocumentChunk.document_id == doc)
                                 .order_by(DocumentChunk.page, DocumentChunk.chunk_id)).all()
        for chunk in chunks:
            found, dropped = extract_chunk(_chunk_input(chunk), extractors)
            records.extend(found)
            for name, number in dropped.items():
                counts[f"dropped:{name}"] += number
        records = associate_captions(records)
        counts.update(persist(session, records))
        counts["superseded"] += reconcile(session, doc, ran, {r.record_id for r in records})
        counts["documents"] += 1
        counts["chunks"] += len(chunks)
    counts["superseded"] += supersede_missing_chunks(session)
    session.commit()
    counts.setdefault("created", 0)
    logger.info("nlp_extract %s", dict(counts))
    return dict(counts)


def status(session: Session) -> dict[str, dict[str, int]]:
    rows = session.execute(select(NlpRecordRow.record_type, NlpRecordRow.review_status, func.count())
                           .group_by(NlpRecordRow.record_type, NlpRecordRow.review_status)).all()
    out: dict[str, dict[str, int]] = {}
    for record_type, review_status, number in rows:
        out.setdefault(record_type, {})[review_status] = number
    return out


def main(argv: list[str]) -> int:
    from flame_api.database import SessionLocal

    logging.basicConfig(level=logging.INFO)
    if argv[:1] not in (["run"], ["status"]):
        print("usage: python -m flame_api.nlp_extract run [--document-id ID] | status")
        return 2
    with SessionLocal() as session:
        if argv[0] == "status":
            print(status(session))
        else:
            doc = argv[argv.index("--document-id") + 1] if "--document-id" in argv else None
            print(run(session, document_id=doc))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
