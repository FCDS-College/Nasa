"""D1: the extraction runner stores source-linked candidates and keeps them honest across re-runs."""
from datetime import UTC, datetime

from sqlalchemy import func, select

from flame_api import nlp_extract
from flame_api.models import DocumentChunk, NlpRecordRow

NOW = datetime(2026, 11, 13, tzinfo=UTC)


def _chunk(session, chunk_id, text, document_id="D1", page=1):
    session.merge(DocumentChunk(chunk_id=chunk_id, document_id=document_id, source_id="S", file_id="F", evidence_id="E1",
                                page=page, text=text, ingested_at=NOW))
    session.commit()


def _rows(session, **where):
    query = select(NlpRecordRow)
    for key, value in where.items():
        query = query.where(getattr(NlpRecordRow, key) == value)
    return session.scalars(query).all()


def test_second_run_creates_nothing(session_factory):
    with session_factory() as session:
        _chunk(session, "abc:v1:1", "In run FX-0042 the flame speed was 3.2 cm/s.")
        first = nlp_extract.run(session)
        second = nlp_extract.run(session)
        assert first["created"] > 0 and second["created"] == 0
        assert {r.record_type for r in _rows(session)} >= {"experiment", "measurement"}


def test_every_stored_record_points_at_its_source_span(session_factory):
    with session_factory() as session:
        text = "In run FX-0042 the flame speed was 3.2 cm/s at 0.1 atm."
        _chunk(session, "abc:v1:7", text, page=7)
        nlp_extract.run(session)
        for row in _rows(session):
            assert row.chunk_id == "abc:v1:7" and row.document_id == "D1" and row.page == 7
            assert text[row.char_start:row.char_end] == row.text
            assert row.review_status == "machine_extracted" and row.extractor and row.extractor_version and row.method


def test_human_review_survives_re_extraction(session_factory):
    with session_factory() as session:
        _chunk(session, "abc:v1:1", "In run FX-0042 it burned.")
        nlp_extract.run(session)
        row = _rows(session, record_type="experiment")[0]
        row.review_status = "human_verified"
        session.commit()
        nlp_extract.run(session)
        assert _rows(session, record_type="experiment")[0].review_status == "human_verified"


def test_changed_chunk_text_supersedes_old_records(session_factory):
    with session_factory() as session:
        _chunk(session, "abc:v1:1", "In run FX-0042 it burned.")
        nlp_extract.run(session)
        _chunk(session, "abc:v1:1", "Earlier text. In run FX-0042 it burned.")   # same id, new offsets: what normalisation or OCR does
        nlp_extract.run(session)
        live = [r for r in _rows(session, record_type="experiment") if r.review_status != "superseded"]
        assert len(live) == 1 and live[0].char_start == len("Earlier text. In run ")
        assert any(r.review_status == "superseded" for r in _rows(session, record_type="experiment"))


def test_reconcile_only_touches_extractors_that_ran(session_factory):
    with session_factory() as session:
        _chunk(session, "abc:v1:1", "In run FX-0042 it burned.")
        nlp_extract.run(session)
        session.add(NlpRecordRow(record_id="nr_llm", record_type="research_finding", text="x", document_id="D1",
                                 document_version="v1", char_start=0, char_end=1, chunk_id="abc:v1:1", extractor="llm-spans",
                                 extractor_version="1", method="llm", confidence=0.5, review_status="machine_extracted",
                                 payload={}, created_at=NOW, updated_at=NOW))
        session.commit()
        nlp_extract.run(session)
        assert session.get(NlpRecordRow, "nr_llm").review_status == "machine_extracted"


def test_records_of_a_deleted_chunk_are_superseded_but_kept(session_factory):
    with session_factory() as session:
        _chunk(session, "abc:v1:1", "In run FX-0042 it burned.")
        nlp_extract.run(session)
        session.query(DocumentChunk).delete()
        session.commit()
        assert nlp_extract.supersede_missing_chunks(session) > 0
        assert not [r for r in _rows(session) if r.review_status != "superseded"]
        assert session.scalar(select(func.count()).select_from(NlpRecordRow)) > 0   # history is kept


def test_table_and_figure_references_are_linked_across_the_pages_of_a_document(session_factory):
    with session_factory() as session:
        _chunk(session, "abc:v1:1", "Spread rates are given in Table 3.", page=1)
        _chunk(session, "abc:v1:2", "Table 3. Flame spread rates\n", page=2)
        nlp_extract.run(session)
        reference = _rows(session, record_type="table_reference")[0]
        assert reference.payload["caption_chunk_id"] == "abc:v1:2" and reference.payload["ambiguous"] is False


def test_the_graph_vocabulary_makes_investigation_names_findable(session_factory):
    from flame_api.models import KnowledgeEntity

    with session_factory() as session:
        session.add(KnowledgeEntity(entity_id="E" * 26, entity_type="investigation", canonical_name="flex", aliases=[],
                                    properties={"display_name": "FLEX"}, evidence_ids=[], review_status="unreviewed",
                                    created_at=NOW, updated_at=NOW))
        _chunk(session, "abc:v1:1", "The FLEX experiment ran on the International Space Station.")
        nlp_extract.run(session)
        found = {(r.record_type, r.normalized) for r in _rows(session)}
        assert ("investigation", "FLEX") in found and ("platform", "International Space Station") in found


def test_derived_condition_records_are_superseded_when_their_chunk_changes(session_factory):
    # `environmental_condition` records for a pressure come from a later step, not from an extractor in the list.
    with session_factory() as session:
        _chunk(session, "abc:v1:1", "Tests were run at 0.1 atm.")
        nlp_extract.run(session)
        assert [r.text for r in _rows(session, record_type="environmental_condition")] == ["0.1 atm"]
        _chunk(session, "abc:v1:1", "Tests were run at ambient pressure.")
        nlp_extract.run(session)
        assert all(r.review_status == "superseded" for r in _rows(session, record_type="environmental_condition"))


def test_the_ingest_hook_records_counts_and_never_raises(session_factory, monkeypatch):
    from flame_api import ingest

    with session_factory() as session:
        _chunk(session, "abc:v1:1", "In run FX-0042 the flame speed was 3.2 cm/s.")
        totals: dict[str, int] = {}
        ingest._extract_nlp(session, totals)
        assert totals["nlp_records_created"] > 0 and "nlp_extract_failed" not in totals

        def boom(*args, **kwargs):
            raise RuntimeError("extractor bug")

        monkeypatch.setattr(nlp_extract, "run", boom)
        failed: dict[str, int] = {}
        ingest._extract_nlp(session, failed)       # derived data: the ingestion it follows must not fail
        assert failed == {"nlp_extract_failed": 1}
