"""Window index against real PostgreSQL + pgvector, with deterministic fake embeddings (no model download).

Skipped unless FLAME_TEST_PG_URL is set and the server has the pgvector extension available (CI's pgvector/pgvector:pg16 does).
Runs the real migration 0011 in a scratch schema, then `build_window_index` and `search_window_chunks`.
"""
import importlib.util
import os
import zlib
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from ai.rag.ingestion.windows import split_windows
from flame_api import vector_index
from flame_api.models import Base, DocumentChunk, DocumentRecord, FileRecord, SourceRecord

URL = os.environ.get("FLAME_TEST_PG_URL")
MIGRATION = Path(__file__).parents[1] / "migrations" / "versions" / "0011_chunk_window_embedding.py"
DIMENSIONS = 384


def _has_pgvector() -> bool:
    if not URL:
        return False
    try:
        engine = create_engine(URL)
        with engine.connect() as connection:
            return bool(connection.execute(text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")).first())
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _has_pgvector(), reason="needs FLAME_TEST_PG_URL pointing at a server with pgvector")

FLAME = "The flame front spread slowly across the acrylic sheet under reduced pressure. " * 14
XENON = "A xenon ion thruster plume was imaged with a high speed camera in the vacuum chamber. " * 14
LONG_PAGE = FLAME + XENON          # about 2,200 characters: the xenon part starts after the first 1,100


def fake_embed(texts):
    """Bag of words hashed into 384 dimensions, L2-normalised: texts sharing words are close, unrelated texts are not."""
    vectors = np.zeros((len(texts), DIMENSIONS))
    for row, body in enumerate(texts):
        for word in body.lower().split():
            vectors[row, zlib.crc32(word.encode()) % DIMENSIONS] += 1.0
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return (vectors / np.where(norms == 0, 1, norms)).tolist()


@pytest.fixture
def session(monkeypatch):
    engine = create_engine(URL)
    connection = engine.connect()
    connection.execute(text("DROP SCHEMA IF EXISTS window_test CASCADE"))
    connection.execute(text("CREATE SCHEMA window_test"))
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    connection.execute(text("SET search_path TO window_test, public"))       # the vector type lives in public
    tables = [Base.metadata.tables[name] for name in ("source", "file_record", "document", "document_chunk")]
    Base.metadata.create_all(connection, tables=tables)
    spec = importlib.util.spec_from_file_location("migration_0011", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with Operations.context(MigrationContext.configure(connection)):
        module.upgrade()
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
    for chunk_id, body in {"long": LONG_PAGE, "short": "Droplet burning in microgravity was recorded."}.items():
        db.add(DocumentChunk(chunk_id=chunk_id, document_id="D", source_id="S", file_id="F", evidence_id=chunk_id.upper(),
                             page=1, text=body, ingested_at=now))
    db.commit()
    monkeypatch.setattr(vector_index, "embed_texts", lambda texts, *, query=False: fake_embed(list(texts)))
    monkeypatch.setattr(vector_index, "_embed_query", lambda query: vector_index._literal(fake_embed([query])[0]))
    yield db
    db.close()
    connection.execute(text("DROP SCHEMA window_test CASCADE"))
    connection.commit()
    connection.close()
    engine.dispose()


def _count(session, where=""):
    return session.execute(text(f"SELECT count(*) FROM chunk_window_embedding {where}")).scalar_one()


def test_building_embeds_every_window_of_every_page(session):
    expected = len(split_windows(LONG_PAGE)) + len(split_windows("Droplet burning in microgravity was recorded."))
    summary = vector_index.build_window_index(session)
    assert summary["pages_embedded"] == 2 and summary["windows_embedded"] == expected == _count(session)
    assert len(split_windows(LONG_PAGE)) >= 2


def test_a_second_build_embeds_nothing(session):
    vector_index.build_window_index(session)
    assert vector_index.build_window_index(session)["pages_embedded"] == 0


def test_a_changed_page_is_re_embedded_and_its_old_windows_are_removed(session):
    vector_index.build_window_index(session)
    session.execute(text("UPDATE document_chunk SET text = :t WHERE chunk_id = 'short'"), {"t": "A completely different short page."})
    session.commit()
    summary = vector_index.build_window_index(session)
    assert summary["pages_embedded"] == 1
    assert _count(session, "WHERE chunk_id = 'short'") == 1


def test_a_page_is_found_by_a_window_that_is_not_its_first(session):
    vector_index.build_window_index(session)
    hits = vector_index.search_window_chunks(session, "xenon ion thruster plume vacuum chamber", limit=5, min_similarity=0.2)
    assert hits and hits[0][0] == "long"
    assert 0.2 <= hits[0][1] <= 1.0 and len({chunk for chunk, _ in hits}) == len(hits)     # one entry per page


def test_the_similarity_floor_removes_unrelated_pages(session):
    vector_index.build_window_index(session)
    assert vector_index.search_window_chunks(session, "completely unrelated query words", limit=5, min_similarity=0.9) == []


def test_deleting_a_page_cascades_to_its_windows(session):
    vector_index.build_window_index(session)
    session.execute(text("DELETE FROM document_chunk WHERE chunk_id = 'long'"))
    session.commit()
    assert _count(session, "WHERE chunk_id = 'long'") == 0


def test_migration_0011_is_repeatable_and_reversible(session):
    connection = session.connection()
    session.commit()
    spec = importlib.util.spec_from_file_location("migration_0011b", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with Operations.context(MigrationContext.configure(connection)):
        module.upgrade()                         # create-if-missing: a second run changes nothing
        module.downgrade()
    connection.commit()
    assert session.execute(text("SELECT to_regclass('chunk_window_embedding')")).scalar_one() is None
