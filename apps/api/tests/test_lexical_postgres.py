"""OR-with-IDF lexical match against a real PostgreSQL (the SQLite test database has no full-text search).

Skipped unless FLAME_TEST_PG_URL points at a database the test may create a scratch schema in (CI sets it).
"""
import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from flame_api import lexical
from flame_api.models import Base, DocumentChunk, DocumentRecord, FileRecord, SourceRecord

URL = os.environ.get("FLAME_TEST_PG_URL")
pytestmark = pytest.mark.skipif(not URL, reason="FLAME_TEST_PG_URL is not set")

TEXTS = {
    "c1": "Flammability of PMMA in oxygen at reduced pressure.",
    "c2": "Flame spread over PMMA was measured in helium and oxygen mixtures.",
    "c3": "The flame was photographed. The flame front was bright and the flame was stable.",
    "c4": "Heptane droplets burned with a cool flame in microgravity.",
}


@pytest.fixture
def session():
    engine = create_engine(URL)
    connection = engine.connect()
    connection.execute(text("DROP SCHEMA IF EXISTS lexical_test CASCADE"))
    connection.execute(text("CREATE SCHEMA lexical_test"))
    connection.execute(text("SET search_path TO lexical_test"))
    tables = [Base.metadata.tables[name] for name in ("source", "file_record", "document", "document_chunk")]
    Base.metadata.create_all(connection, tables=tables)
    connection.execute(text("ALTER TABLE document_chunk ADD COLUMN search_tsv tsvector "
                            "GENERATED ALWAYS AS (to_tsvector('english', text)) STORED"))
    connection.commit()
    db = Session(connection)
    now = datetime.now(UTC)
    db.add(SourceRecord(source_id="S", title="S", repository="R", access_url="https://example.org", domain="combustion"))
    db.flush()
    db.add(FileRecord(file_id="F", source_id="S", sha256="0" * 64, original_filename="a.pdf", media_type="application/pdf",
                      size_bytes=1, retrieved_at=now))
    db.flush()
    db.add(DocumentRecord(document_id="D", source_id="S", file_id="F", title="T", ingested_at=now))
    db.flush()
    for chunk_id, body in TEXTS.items():
        db.add(DocumentChunk(chunk_id=chunk_id, document_id="D", source_id="S", file_id="F", evidence_id=chunk_id.upper(),
                             page=1, text=body, ingested_at=now))
    db.commit()
    lexical.clear_cache()
    yield db
    db.close()
    connection.execute(text("DROP SCHEMA lexical_test CASCADE"))
    connection.commit()
    connection.close()
    engine.dispose()
    lexical.clear_cache()


def _ranked(session, query):
    matched = lexical.match(session, query)
    if matched is None:
        return None
    condition, score = matched
    rows = session.execute(select(DocumentChunk.chunk_id, score.label("s")).where(condition)
                           .order_by(score.desc(), DocumentChunk.chunk_id)).all()
    return [(chunk_id, round(value, 3)) for chunk_id, value in rows]


def test_a_chunk_matching_only_some_terms_is_found(session):
    ranked = _ranked(session, "What does PMMA do in microgravity?")
    assert {chunk for chunk, _ in ranked} == {"c1", "c2", "c4"}          # the AND query would find none


def test_a_rare_term_outranks_a_common_one(session):
    ranked = _ranked(session, "flame heptane")
    assert [chunk for chunk, _ in ranked][0] == "c4"                      # heptane is in 1 chunk, flame in 3


def test_the_chunk_matching_more_distinctive_terms_ranks_first(session):
    ranked = _ranked(session, "PMMA flame helium")
    assert ranked[0][0] == "c2"


def test_a_question_of_only_stopwords_has_no_match(session):
    assert _ranked(session, "what is the of and") is None


def test_operator_characters_in_the_question_cannot_break_the_query(session):
    assert _ranked(session, "pmma | (flame & !oxygen) <-> ' --") is not None


def test_a_freshly_booted_machine_does_not_see_an_empty_cache_as_fresh(session, monkeypatch):
    # time.monotonic() counts from boot: a cleared cache must not look "recent" just because the machine started a minute ago.
    monkeypatch.setattr(lexical.time, "monotonic", lambda: 10.0)
    lexical.clear_cache()
    assert _ranked(session, "PMMA flame helium")[0][0] == "c2"
