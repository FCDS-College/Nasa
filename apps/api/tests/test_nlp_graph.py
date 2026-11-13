"""D1: NLP records become unreviewed, association-only edges in the knowledge graph (docs/data/KNOWLEDGE_GRAPH_SCHEMA.md)."""
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from flame_api import knowledge_graph as kg
from flame_api import nlp_graph
from flame_api.models import DocumentChunk, DocumentRecord, EvidenceRecord, KnowledgeEntity, KnowledgeRelation, NlpRecordRow
from test_knowledge_graph import _ingested

NOW = datetime(2026, 11, 13, tzinfo=UTC)


@pytest.fixture
def graphed():
    engine, sessions, _ = _ingested()
    yield sessions
    engine.dispose()


def _investigations(session):
    return session.scalars(select(KnowledgeEntity).where(KnowledgeEntity.entity_type == "investigation")
                           .order_by(KnowledgeEntity.entity_id)).all()


def _record(session, n, record_type, normalized, chunk_id="c1", document_id="NTRS1", page=1, confidence=1.0):
    session.add(NlpRecordRow(record_id=f"nr_{n}", record_type=record_type, text=normalized, normalized=normalized,
                             document_id=document_id, document_version="v1", page=page, char_start=n, char_end=n + 3,
                             chunk_id=chunk_id, extractor="vocabulary-lookup", extractor_version="v", method="rule",
                             confidence=confidence, review_status="machine_extracted", payload={}, created_at=NOW,
                             updated_at=NOW))


def _chunk(session, chunk_id="c1", evidence_id="EV1", document_id="NTRS1", page=1):
    session.add(DocumentChunk(chunk_id=chunk_id, document_id=document_id, source_id="S", file_id="F", evidence_id=evidence_id,
                              page=page, text="x" * 50, ingested_at=NOW))


def _document(session, document_id="NTRS1", document_type="technical_report", source_id="FF-NTRS-1"):
    session.add(DocumentRecord(document_id=document_id, source_id=source_id, file_id="F", title="A report", document_type=document_type,
                               ingested_at=NOW))


def _edges(session, predicate):
    return session.scalars(select(KnowledgeRelation).where(KnowledgeRelation.predicate == predicate,
                                                            KnowledgeRelation.extraction_method == "nlp_extraction")).all()


def test_co_occurrence_becomes_an_unreviewed_ran_on_edge(graphed):
    with graphed() as session:
        name = _investigations(session)[0].canonical_name
        _chunk(session)
        _record(session, 1, "investigation", name)
        _record(session, 2, "platform", "International Space Station", confidence=0.9)
        session.commit()
        counts = nlp_graph.build_nlp_edges(session)
        [edge] = _edges(session, "ran_on")
        assert (edge.review_status, edge.evidence_id, edge.confidence) == ("unreviewed", "EV1", 0.9)
        assert edge.properties["basis"] == "co_occurrence_in_chunk" and counts["relations_created"] >= 1
        assert edge.extractor_version == nlp_graph.NLP_EXTRACTOR_VERSION


def test_an_instrument_becomes_a_measured_with_edge(graphed):
    with graphed() as session:
        name = _investigations(session)[0].canonical_name
        _chunk(session)
        _record(session, 1, "investigation", name)
        _record(session, 2, "instrument", "high-speed camera")
        session.commit()
        nlp_graph.build_nlp_edges(session)
        assert len(_edges(session, "measured_with")) == 1


def test_two_investigations_in_one_chunk_are_ambiguous(graphed):
    with graphed() as session:
        names = [e.canonical_name for e in _investigations(session)][:2]
        _chunk(session)
        _record(session, 1, "investigation", names[0])
        _record(session, 2, "investigation", names[1])
        _record(session, 3, "platform", "drop tower")
        session.commit()
        counts = nlp_graph.build_nlp_edges(session)
        assert not _edges(session, "ran_on") and counts["ambiguous_chunks"] == 1


def test_unknown_investigation_is_skipped_not_created(graphed):
    with graphed() as session:
        before = len(session.scalars(select(KnowledgeEntity)).all())
        _chunk(session)
        _record(session, 1, "investigation", "NOT-IN-GRAPH")
        _record(session, 2, "platform", "drop tower")
        session.commit()
        counts = nlp_graph.build_nlp_edges(session)
        assert counts["investigation_not_in_graph"] == 1 and len(session.scalars(select(KnowledgeEntity)).all()) == before


def test_a_report_on_its_first_page_describes_the_investigation_it_names(graphed):
    with graphed() as session:
        name = _investigations(session)[0].canonical_name
        _document(session)
        _chunk(session, page=1)
        _record(session, 1, "investigation", name, page=1)
        session.commit()
        nlp_graph.build_nlp_edges(session)
        [edge] = _edges(session, "describes")
        assert edge.review_status == "unreviewed" and edge.properties["basis"] == "named_in_document"


def test_dataset_documentation_already_has_table_parse_describes_edges(graphed):
    with graphed() as session:
        name = _investigations(session)[0].canonical_name
        _document(session, document_type="dataset_documentation")
        _chunk(session, page=1)
        _record(session, 1, "investigation", name, page=1)
        session.commit()
        nlp_graph.build_nlp_edges(session)
        assert _edges(session, "describes") == []


def test_table_rebuild_and_a_second_nlp_build_keep_the_edges(graphed):
    with graphed() as session:
        name = _investigations(session)[0].canonical_name
        session.add(EvidenceRecord(evidence_id="EV1", kind="passage", origin="verbatim_text", payload={}, created_at=NOW))
        _chunk(session)
        _record(session, 1, "investigation", name)
        _record(session, 2, "instrument", "high-speed camera")
        session.commit()
        nlp_graph.build_nlp_edges(session)
        kg.build_graph(session, knowledge_version="kv-test")
        again = nlp_graph.build_nlp_edges(session)
        assert len(_edges(session, "measured_with")) == 1 and again.get("relations_created", 0) == 0
        assert kg.check_consistency(session)["ok"]


def test_the_new_predicates_are_accepted_by_traversal_filters():
    assert {"ran_on", "measured_with"} <= set(kg.PREDICATES) and {"platform", "instrument"} <= set(kg.ENTITY_TYPES)
