"""pgvector chunk index: build, status and nearest-neighbour search.

Documents are embedded with a small ONNX model (fastembed). Everything degrades to lexical search when
the extension, the index, or the embedding runtime is missing, so callers must treat failures as "no index".
"""
from __future__ import annotations

import hashlib
import importlib.util
import logging
import sys
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ai.providers.contracts.embeddings import EmbeddingRequest
from ai.providers.contracts.errors import ProviderError
from ai.providers.local.fastembed_embeddings import DIMENSIONS, MAX_CHUNK_CHARS, MODEL_NAME, QUERY_PREFIX  # noqa: F401
from ai.rag.ingestion.windows import split_windows
from ai.rag.retrieval.aggregate import aggregate_windows
from ai.routing import NoCompatibleProvider

logger = logging.getLogger("flame_api")

MIN_SIMILARITY = 0.55


class VectorUnavailableError(Exception):
    pass


def embed_texts(texts: list[str], *, query: bool = False) -> list[list[float]]:
    """Embed through the router (2H Task 2): a local model in every mode, never a silent download offline."""
    from flame_api import ai_runtime

    task = "embed.query" if query else "embed.documents"
    try:
        routed = ai_runtime.get_router().route(task, lambda provider: provider.embed(EmbeddingRequest(texts=tuple(texts), query=query)))
    except (NoCompatibleProvider, ProviderError) as exc:
        raise VectorUnavailableError("No embedding model is available.") from exc
    if routed.value.model != MODEL_NAME:
        # The index was built with MODEL_NAME; vectors from another model are not comparable.
        raise VectorUnavailableError("The available embedding model does not match the index.")
    return [list(vector) for vector in routed.value.vectors]


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


def indexed_chunk_count(session: Session) -> int:
    """Chunks with a vector in the published index (model of the manifest). Raises SQLAlchemyError.

    0 means there is truly no published index: not PostgreSQL, tables absent, or no manifest row.
    """
    if session.bind.dialect.name != "postgresql":
        return 0
    if not session.execute(text("select to_regclass('vector_index_manifest') is not null and to_regclass('chunk_embedding') is not null")).scalar_one():
        return 0
    model = session.execute(text("select model from vector_index_manifest where id = 1")).scalar_one_or_none()
    if model is None:
        return 0
    return session.execute(
        text("select count(*) from chunk_embedding e join document_chunk c on c.chunk_id = e.chunk_id where e.model = :model"),
        {"model": model},
    ).scalar_one()


def search_chunks(session: Session, query: str, *, limit: int = 20, min_similarity: float = MIN_SIMILARITY) -> list[tuple[str, float]]:
    """(chunk_id, cosine similarity) for the nearest chunks, best first. Raises VectorUnavailableError."""
    from ai.routing.tracing import span

    with span("retrieval.vector", **{"flame.limit": limit}):
        return _search_chunks(session, query, limit=limit, min_similarity=min_similarity)


def _search_chunks(session: Session, query: str, *, limit: int, min_similarity: float) -> list[tuple[str, float]]:
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
    from flame_api.config import get_settings
    from flame_api.knowledge_version import publish

    publish(session, version, trigger="vector_index_build", counts={"chunk_embeddings": total, "embedded": len(pending)},
            redis_url=get_settings().redis_url)
    return {"embedded": len(pending), "total": total, "knowledge_version": version}


# --- window-level index (roadmap item 11; FLAME_DENSE_GRANULARITY=window) ---------------------------------------------------
WINDOW_HITS = 30     # windows fetched before they are aggregated to pages


def _text_sha(text_: str) -> str:
    return hashlib.sha256(text_.encode("utf-8")).hexdigest()[:16]


def window_index_status(session: Session) -> dict[str, Any]:
    """state: up | stale | missing | unavailable. Never raises. `up` = every page has windows of the current model and text."""
    if session.bind.dialect.name != "postgresql":
        return {"state": "unavailable", "message": "Vector search requires PostgreSQL."}
    try:
        covered = session.execute(text(
            "select count(distinct w.chunk_id) from chunk_window_embedding w join document_chunk c on c.chunk_id = w.chunk_id "
            "where w.model = :model"), {"model": MODEL_NAME}).scalar_one()
        chunks = session.execute(text("select count(*) from document_chunk")).scalar_one()
    except SQLAlchemyError:
        session.rollback()
        return {"state": "missing", "message": "No window index has been built."}
    if covered == 0:
        return {"state": "missing", "message": "No window index has been built."}
    if covered < chunks:
        return {"state": "stale", "pages": covered, "chunks": chunks, "message": f"Window index covers {covered} of {chunks} pages."}
    return {"state": "up", "pages": covered, "chunks": chunks, "message": None}


def search_window_chunks(session: Session, query: str, *, limit: int = 10, min_similarity: float = MIN_SIMILARITY) -> list[tuple[str, float]]:
    """(chunk_id, best window similarity) for the nearest pages, best first. Falls back to the page index when there are no windows."""
    if session.bind.dialect.name != "postgresql":
        raise VectorUnavailableError("Vector search requires PostgreSQL.")
    try:
        vector = _embed_query(query)
        rows = session.execute(
            text(
                "select chunk_id, 1 - (embedding <=> cast(:q as vector)) as sim from chunk_window_embedding "
                "order by embedding <=> cast(:q as vector) limit :limit"
            ),
            {"q": vector, "limit": WINDOW_HITS},
        ).all()
    except SQLAlchemyError:
        session.rollback()
        logger.warning("window_index=unavailable; using the page index")
        return search_chunks(session, query, limit=limit, min_similarity=min_similarity)
    if not rows:
        return search_chunks(session, query, limit=limit, min_similarity=min_similarity)
    return [(chunk_id, sim) for chunk_id, sim in aggregate_windows(((row.chunk_id, float(row.sim)) for row in rows), limit=limit)
            if sim >= min_similarity]


def build_window_index(session: Session, *, batch_size: int = 64) -> dict[str, Any]:
    """Embed the windows of every page that has none, or whose text or model changed; drop windows of changed pages."""
    if session.bind.dialect.name != "postgresql":
        raise VectorUnavailableError("Vector search requires PostgreSQL.")
    existing = {row.chunk_id: (row.text_sha, row.model) for row in session.execute(
        text("select distinct chunk_id, text_sha, model from chunk_window_embedding"))}
    pending: list[tuple[str, str]] = []
    for row in session.execute(text("select chunk_id, text from document_chunk order by chunk_id")).all():
        if existing.get(row.chunk_id) != (_text_sha(row.text), MODEL_NAME):
            pending.append((row.chunk_id, row.text))
    embedded = 0
    for start in range(0, len(pending), batch_size):
        batch = pending[start:start + batch_size]
        windows = [(chunk_id, text_, window) for chunk_id, text_ in batch for window in split_windows(text_)]
        for chunk_id, _ in batch:
            session.execute(text("delete from chunk_window_embedding where chunk_id = :id"), {"id": chunk_id})
        vectors = embed_texts([window.text for _, _, window in windows]) if windows else []
        if windows:
            session.execute(
                text(
                    "insert into chunk_window_embedding (window_id, chunk_id, ordinal, char_start, char_end, text_sha, model, embedding) "
                    "values (:wid, :cid, :ord, :s, :e, :sha, :model, cast(:v as vector))"
                ),
                [{"wid": f"{chunk_id}#w{window.ordinal}", "cid": chunk_id, "ord": window.ordinal, "s": window.start, "e": window.end,
                  "sha": _text_sha(text_), "model": MODEL_NAME, "v": _literal(vec)}
                 for (chunk_id, text_, window), vec in zip(windows, vectors)],
            )
        session.commit()
        embedded += len(windows)
        logger.info("window_index pages=%d/%d windows=%d", min(start + batch_size, len(pending)), len(pending), embedded)
    total = session.execute(text("select count(*) from chunk_window_embedding")).scalar_one()
    return {"pages_embedded": len(pending), "windows_embedded": embedded, "windows_total": total}


def main(argv: list[str]) -> int:
    from flame_api.database import SessionLocal

    logging.basicConfig(level=logging.INFO)
    if argv[:1] not in (["build"], ["build-windows"]):
        print("usage: python -m flame_api.vector_index build | build-windows")
        return 2
    with SessionLocal() as session:
        print(build_window_index(session) if argv[0] == "build-windows" else build_index(session))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
