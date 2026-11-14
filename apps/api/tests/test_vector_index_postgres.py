"""Page-level vector index against real PostgreSQL + pgvector, with deterministic fake embeddings (no model download).

Skipped unless FLAME_TEST_PG_URL is set and the server has the pgvector extension available (CI's pgvector/pgvector:pg16 does).
Runs the real migrations 0003 and 0013 in a scratch schema, then `build_index` and the knowledge-version publication.

KB audit 2026-11-13, finding 4: the version was `<model>-<rows>-<YYYYMMDD>`, so a same-day rebuild after a text change kept
the version (publish is a no-op for a known version) and the changed page kept its old vector.
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

from flame_api import knowledge_version, vector_index
from flame_api.models import Base, DocumentChunk, DocumentRecord, FileRecord, SourceRecord

URL = os.environ.get("FLAME_TEST_PG_URL")
VERSIONS = Path(__file__).parents[1] / "migrations" / "versions"
MIGRATIONS = ("0003_vector_index.py", "0013_chunk_embedding_text_sha.py")
TABLES = ("source", "file_record", "document", "document_chunk", "knowledge_publication")
SCHEMA = "page_index_test"
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


def fake_embed(texts):
    """Bag of words hashed into 384 dimensions, L2-normalised."""
    vectors = np.zeros((len(texts), DIMENSIONS))
    for row, body in enumerate(texts):
        for word in body.lower().split():
            vectors[row, zlib.crc32(word.encode()) % DIMENSIONS] += 1.0
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return (vectors / np.where(norms == 0, 1, norms)).tolist()


def _migration(name: str):
    spec = importlib.util.spec_from_file_location(f"migration_{name}", VERSIONS / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def session(monkeypatch):
    engine = create_engine(URL)
    connection = engine.connect()
    try:
        yield from _scratch_session(connection, monkeypatch)
    finally:
        # Also on a setup failure: an open transaction would hold its locks and hang the next test's CREATE SCHEMA.
        connection.rollback()
        connection.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
        connection.commit()
        connection.close()
        engine.dispose()


def _scratch_session(connection, monkeypatch):
    connection.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
    connection.execute(text(f"CREATE SCHEMA {SCHEMA}"))
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    connection.execute(text(f"SET search_path TO {SCHEMA}, public"))       # the vector type lives in public
    # checkfirst=False: in CI `public` already holds the real tables; a check-first create would write to the real data.
    Base.metadata.create_all(connection, tables=[Base.metadata.tables[name] for name in TABLES], checkfirst=False)
    for name in TABLES:
        assert connection.execute(text("SELECT to_regclass(:n)"), {"n": f"{SCHEMA}.{name}"}).scalar_one() is not None
    with Operations.context(MigrationContext.configure(connection)):
        for name in MIGRATIONS:
            _migration(name).upgrade()
    for name in ("chunk_embedding", "vector_index_manifest"):
        assert connection.execute(text("SELECT to_regclass(:n)"), {"n": f"{SCHEMA}.{name}"}).scalar_one() is not None
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
    for chunk_id, body in {"a": "The flame front spread across the acrylic sheet.", "b": "Droplet burning in microgravity."}.items():
        db.add(DocumentChunk(chunk_id=chunk_id, document_id="D", source_id="S", file_id="F", evidence_id=chunk_id.upper(),
                             page=1, text=body, ingested_at=now))
    db.commit()
    embedded: list[str] = []

    def embed(texts, *, query=False):
        embedded.extend(texts)
        return fake_embed(list(texts))

    monkeypatch.setattr(vector_index, "embed_texts", embed)
    monkeypatch.setattr(knowledge_version, "_announce", lambda event, redis_url: False)
    db.embedded = embedded
    yield db
    db.close()


def _publications(session) -> int:
    return session.execute(text("SELECT count(*) FROM knowledge_publication")).scalar_one()


def test_a_rebuild_with_nothing_changed_embeds_nothing_and_keeps_the_version(session):
    first = vector_index.build_index(session)
    second = vector_index.build_index(session)
    assert first["embedded"] == 2 and second["embedded"] == 0
    assert second["knowledge_version"] == first["knowledge_version"] and _publications(session) == 1


def test_a_changed_page_is_re_embedded_and_publishes_a_new_version_on_the_same_day(session):
    first = vector_index.build_index(session)
    session.execute(text("UPDATE document_chunk SET text = :t WHERE chunk_id = 'b'"), {"t": "Droplet extinction at low oxygen."})
    session.commit()
    session.embedded.clear()
    second = vector_index.build_index(session)
    assert second["embedded"] == 1 and session.embedded == ["Droplet extinction at low oxygen."]
    assert second["total"] == first["total"] == 2                       # same row count, same day: the old version string
    assert second["knowledge_version"] != first["knowledge_version"]
    assert knowledge_version.current_knowledge_version(session) == second["knowledge_version"]
    manifest = session.execute(text("SELECT knowledge_version, row_count FROM vector_index_manifest")).one()
    assert tuple(manifest) == (second["knowledge_version"], 2)


def test_the_version_names_the_model_and_the_row_count(session):
    version = vector_index.build_index(session)["knowledge_version"]
    assert version.startswith("bge-small-en-v1.5-2-") and len(version.rsplit("-", 1)[1]) == 12


def test_vectors_built_before_migration_0013_are_re_embedded_once(session):
    vector_index.build_index(session)
    session.execute(text("UPDATE chunk_embedding SET text_sha = NULL"))      # rows written by the old build have no hash
    session.commit()
    assert vector_index.build_index(session)["embedded"] == 2
    assert vector_index.build_index(session)["embedded"] == 0


def test_migration_0013_is_repeatable_and_reversible(session):
    connection = session.connection()
    session.commit()
    module = _migration("0013_chunk_embedding_text_sha.py")
    column = text("SELECT count(*) FROM information_schema.columns WHERE table_schema = :s AND table_name = 'chunk_embedding' "
                  "AND column_name = 'text_sha'")
    with Operations.context(MigrationContext.configure(connection)):
        module.upgrade()                         # add-if-missing: a second run changes nothing
        assert connection.execute(column, {"s": SCHEMA}).scalar_one() == 1
        module.downgrade()
    connection.commit()
    assert session.execute(column, {"s": SCHEMA}).scalar_one() == 0
