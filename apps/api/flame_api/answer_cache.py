"""Flame's own answer cache (CAG, M4) for /api/chat.

Entries are keyed by the knowledge version, the instruction version, the execution mode and
the normalised question (``ai.rag.cache.cag``), so a published knowledge version can never be
answered from an older entry. ``cache_hit`` in the response comes from this cache, not from a provider.
Degraded or fallback answers are never cached. The store is per process; Redis is Planned.
"""
from __future__ import annotations

import copy
import hashlib
import time
from threading import Lock
from typing import Any

from ai.rag.cache.cag import DependencyManifest, InMemoryCacheService, build_cache_key, ttl_for

_cache = InMemoryCacheService()
_lock = Lock()
_last_version: str | None = None
RERANKER = "none@1"   # no reranking (FLAME_RERANKER_ENABLED=false)


def reranker_version(model: str | None, depth: int | None) -> str:
    """The cache's reranker dimension (ADR-006): a different reranker or window is a different answer."""
    return RERANKER if not model else f"{model}@depth{depth}"


def prompt_version(instructions: str) -> str:
    return "chat-" + hashlib.sha256(instructions.encode("utf-8")).hexdigest()[:8]


def make_key(question: str, *, knowledge_version: str, instructions: str, mode: str, reranker: str = RERANKER) -> str:
    return build_cache_key(
        query=question, filters=None, top_k=6, corpus_version=knowledge_version,
        prompt_version=prompt_version(instructions), model=f"router-{mode}", reranker_version=reranker,
    )


def lookup(key: str, knowledge_version: str) -> dict[str, Any] | None:
    global _last_version
    with _lock:
        if _last_version != knowledge_version:
            _cache.invalidate_corpus(knowledge_version)
            _last_version = knowledge_version
        hit = _cache.get(key)
    return copy.deepcopy(hit) if hit is not None else None


def store(key: str, response: dict[str, Any], *, knowledge_version: str, instructions: str, started: float,
          reranker: str = RERANKER) -> None:
    entry = {k: v for k, v in response.items() if k != "request_id"}
    manifest = DependencyManifest(
        corpus_version=knowledge_version,
        prompt_versions={"chat": prompt_version(instructions)},
        model=f"{response['model']['provider']}:{response['model']['name']}",
        provider=response["model"]["provider"],
        execution_mode=(response.get("execution") or {}).get("locality", ""),
        reranker_version=reranker,
    )
    with _lock:
        _cache.set(key, copy.deepcopy(entry), ttl_for({"status": "answered"}), manifest.model_dump(),
                   compute_ms=(time.perf_counter() - started) * 1000)


def metrics() -> dict[str, Any]:
    with _lock:
        return _cache.metrics()


def reset() -> None:
    global _last_version
    with _lock:
        _cache.__init__()
        _last_version = None
