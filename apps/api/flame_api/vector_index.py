"""pgvector chunk index: build, status and nearest-neighbour search.

Documents are embedded with a small ONNX model (fastembed). Everything degrades to lexical search when
the extension, the index, or the embedding runtime is missing, so callers must treat failures as "no index".
"""
from __future__ import annotations

import importlib.util
import logging
import sys
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger("flame_api")

MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIMENSIONS = 384
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
MAX_CHUNK_CHARS = 2000
MIN_SIMILARITY = 0.55


class VectorUnavailableError(Exception):
    pass


@lru_cache(maxsize=1)
def _embedder():
    try:
        from fastembed import TextEmbedding
    except ImportError as exc:
        raise VectorUnavailableError("fastembed is not installed.") from exc
    return TextEmbedding(model_name=MODEL_NAME)


def embed_texts(texts: list[str], *, query: bool = False) -> list[list[float]]:
    model = _embedder()
    prepared = [(QUERY_PREFIX + t if query else t)[:MAX_CHUNK_CHARS] for t in texts]
    return [[float(x) for x in vector] for vector in model.embed(prepared)]


@lru_cache(maxsize=256)
def _embed_query(query: str) -> str:
    return _literal(embed_texts([query], query=True)[0])


def _literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{x:.6g}" for x in vector) + "]"


def index_status(session: Session) -> dict[str, Any]:
    """state: up | stale | missing | unavailable. Never raises."""
    if session.bind.dialect.name != "postgresql":
        return {"state": "unavailable", "message": "Vector search requires PostgreSQL."}
    try:
        manifest = session.execute(
            text("select model, dim, row_count, knowledge_version from vector_index_manifest where id = 1")
        ).first()
        chunks = session.execute(text("select count(*) from document_chunk")).scalar_one()
        rows = session.execute(text("select count(*) from chunk_embedding")).scalar_one()
    except SQLAlchemyError:
        session.rollback()
        return {"state": "missing", "message": "No vector index has been published."}
    if manifest is None or rows == 0:
        return {"state": "missing", "message": "No vector index has been published."}
    base = {"model": manifest.model, "version": manifest.knowledge_version, "rows": rows, "chunks": chunks}
    if manifest.model != MODEL_NAME or manifest.dim != DIMENSIONS:
        return {**base, "state": "stale", "message": "Index was built with a different embedding model."}
    if rows < chunks:
        return {**base, "state": "stale", "message": f"Index covers {rows} of {chunks} chunks; rebuild it."}
    if importlib.util.find_spec("fastembed") is None:
        return {**base, "state": "stale", "message": "Embedding runtime is not installed; queries fall back to lexical search."}
    return {**base, "state": "up", "message": None}


def search_chunks(session: Session, query: str, *, limit: int = 20, min_similarity: float = MIN_SIMILARITY) -> list[tuple[str, float]]:
    """(chunk_id, cosine similarity) for the nearest chunks, best first. Raises VectorUnavailableError."""
    if session.bind.dialect.name != "postgresql":
        raise VectorUnavailableError("Vector search requires PostgreSQL.")
    try:
        vector = _embed_query(query)
        rows = session.execute(
            text(
                "select chunk_id, 1 - (embedding <=> cast(:q as vector)) as sim from chunk_embedding "
                "order by embedding <=> cast(:q as vector) limit :limit"
            ),
            {"q": vector, "limit": limit},
        ).all()
    except SQLAlchemyError as exc:
        session.rollback()
        raise VectorUnavailableError("Vector index could not be queried.") from exc
    return [(row.chunk_id, float(row.sim)) for row in rows if row.sim >= min_similarity]


def build_index(session: Session, *, batch_size: int = 64) -> dict[str, Any]:
    """Embed chunks that have no vector yet, drop vectors of deleted chunks, publish a new version."""
    if session.bind.dialect.name != "postgresql":
        raise VectorUnavailableError("Vector search requires PostgreSQL.")
    session.execute(text("create extension if not exists vector"))
    session.commit()
    pending = session.execute(
        text(
            "select c.chunk_id, c.text from document_chunk c "
            "left join chunk_embedding e on e.chunk_id = c.chunk_id "
            "where e.chunk_id is null or e.model <> :model order by c.chunk_id"
        ),
        {"model": MODEL_NAME},
    ).all()
    session.execute(text("delete from chunk_embedding where model <> :model"), {"model": MODEL_NAME})
    for start in range(0, len(pending), batch_size):
        batch = pending[start:start + batch_size]
        vectors = embed_texts([row.text for row in batch])
        session.execute(
            text(
                "insert into chunk_embedding (chunk_id, model, embedding) values (:id, :model, cast(:v as vector)) "
                "on conflict (chunk_id) do update set model = excluded.model, embedding = excluded.embedding"
            ),
            [{"id": row.chunk_id, "model": MODEL_NAME, "v": _literal(vec)} for row, vec in zip(batch, vectors)],
        )
        session.commit()
        logger.info("vector_index embedded=%d/%d", start + len(batch), len(pending))
    total = session.execute(text("select count(*) from chunk_embedding")).scalar_one()
    built_at = datetime.now(UTC)
    version = f"{MODEL_NAME.split('/')[-1]}-{total}-{built_at:%Y%m%d}"
    session.execute(
        text(
            "insert into vector_index_manifest (id, model, dim, row_count, knowledge_version, built_at) "
            "values (1, :model, :dim, :rows, :version, :built_at) on conflict (id) do update set "
            "model = excluded.model, dim = excluded.dim, row_count = excluded.row_count, "
            "knowledge_version = excluded.knowledge_version, built_at = excluded.built_at"
        ),
        {"model": MODEL_NAME, "dim": DIMENSIONS, "rows": total, "version": version, "built_at": built_at},
    )
    session.commit()
    return {"embedded": len(pending), "total": total, "knowledge_version": version}


def main(argv: list[str]) -> int:
    from flame_api.database import SessionLocal

    logging.basicConfig(level=logging.INFO)
    if argv[:1] != ["build"]:
        print("usage: python -m flame_api.vector_index build")
        return 2
    with SessionLocal() as session:
        print(build_index(session))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
