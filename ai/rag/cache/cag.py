"""Cache-Augmented Generation (CAG): versioned keys, manifests, invalidation.

Key pattern (scheme v1):
    rag:v1:corpus:<corpus_ver>:prompt:<prompt_ver>:model:<model>:rerank:<rerank_ver>:<query_hash>

Any change to corpus, prompt, model or reranker version changes the key, so
stale answers are never served; explicit invalidation also removes old
entries (memory hygiene) when a knowledge version is published.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel, Field

from ai.interfaces import CacheService

KEY_SCHEME = "v1"
DEFAULT_TTL_SECONDS = 3600.0
ABSTENTION_TTL_SECONDS = 300.0


def normalize_query(query: str) -> str:
    """Lower-case, trim and collapse whitespace so equivalent queries share one cache key.

    Args:
        query: raw query text.

    Returns:
        The normalised query string."""

    return re.sub(r"\s+", " ", query.strip().lower())


def _clean(part: str) -> str:
    return re.sub(r"[^A-Za-z0-9._@-]", "_", str(part))


def build_cache_key(
    *,
    query: str,
    filters: dict | None,
    top_k: int,
    corpus_version: str,
    prompt_version: str,
    model: str,
    reranker_version: str,
    namespace: str = "rag",
) -> str:
    """Build the versioned cache key. Same inputs always give the same key."""
    payload = json.dumps(
        {"q": normalize_query(query), "f": filters or {}, "k": top_k},
        sort_keys=True,
        ensure_ascii=False,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
    return (
        f"{namespace}:{KEY_SCHEME}:corpus:{_clean(corpus_version)}:prompt:{_clean(prompt_version)}"
        f":model:{_clean(model)}:rerank:{_clean(reranker_version)}:{digest}"
    )


class DependencyManifest(BaseModel):
    """What a cached entry was built from. Stored with every entry."""

    schema_version: str = "1.0.0"
    corpus_version: str
    document_versions: dict[str, str] = Field(default_factory=dict)
    chunk_ids: list[str] = Field(default_factory=list)
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    model: str = ""
    embedding_model: str = ""
    reranker_version: str = ""
    provider: str = ""
    execution_mode: str = ""  # "local" or "cloud"; empty when unknown


def is_cacheable(answer: Any) -> bool:
    """Answers that used session memory are personal context: never cached."""
    used = getattr(answer, "memory_used", None)
    if used is None and isinstance(answer, dict):
        used = answer.get("memory_used")
    return not used


def ttl_for(answer: Any) -> float:
    """Return the cache lifetime in seconds for an answer.

    Abstentions (status insufficient_evidence or conflicting_evidence) get ABSTENTION_TTL_SECONDS (300); every other answer gets DEFAULT_TTL_SECONDS (3600).

    Args:
        answer: a GroundedAnswer or a dict with a `status` key."""

    status = getattr(answer, "status", None) or (answer.get("status") if isinstance(answer, dict) else None)
    if status in ("insufficient_evidence", "conflicting_evidence"):
        return ABSTENTION_TTL_SECONDS
    return DEFAULT_TTL_SECONDS


@dataclass
class _Entry:
    value: Any
    expires_at: float
    manifest: dict
    compute_ms: float
    created_at: float = field(default_factory=time.time)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round(pct / 100 * (len(ordered) - 1)))))
    return ordered[idx]


class InMemoryCacheService(CacheService):
    """Process-local cache. Same interface a Redis implementation would use."""

    def __init__(self, clock: Callable[[], float] = time.time):
        self._clock = clock
        self._entries: dict[str, _Entry] = {}
        self.hits = 0
        self.misses = 0
        self._saved_ms: list[float] = []

    def get(self, key: str):
        """Return the cached value for `key`, or None on a miss or expiry.

        Expired entries are deleted. A hit increments `hits` and records the entry's stored compute time as time saved; a miss increments `misses`."""

        entry = self._entries.get(key)
        if entry is None or entry.expires_at <= self._clock():
            if entry is not None:
                del self._entries[key]
            self.misses += 1
            return None
        self.hits += 1
        self._saved_ms.append(entry.compute_ms)
        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: float, manifest: dict, compute_ms: float = 0.0) -> None:
        """Store `value` under `key` with a TTL and a dependency manifest.

        Args:
            key: key from build_cache_key.
            value: the object to cache.
            ttl_seconds: lifetime in seconds.
            manifest: dict that must contain `corpus_version`.
            compute_ms: time it took to compute the value (used for the saved-time metrics).

        Raises:
            ValueError: if ttl_seconds <= 0 or the manifest lacks corpus_version."""

        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0")
        if not manifest or "corpus_version" not in manifest:
            raise ValueError("manifest with corpus_version is required")
        self._entries[key] = _Entry(
            value=value,
            expires_at=self._clock() + ttl_seconds,
            manifest=dict(manifest),
            compute_ms=compute_ms,
            created_at=self._clock(),
        )

    def invalidate_corpus(self, current_corpus_version: str) -> int:
        """Called when a new knowledge version is published."""
        stale = [k for k, e in self._entries.items() if e.manifest.get("corpus_version") != current_corpus_version]
        for k in stale:
            del self._entries[k]
        return len(stale)

    def invalidate_document(self, document_id: str, new_version: str | None = None) -> int:
        """Drop entries that depend on a document (optionally only older versions)."""
        stale = []
        for k, e in self._entries.items():
            deps = e.manifest.get("document_versions", {})
            if document_id in deps and (new_version is None or deps[document_id] != new_version):
                stale.append(k)
        for k in stale:
            del self._entries[k]
        return len(stale)

    def __len__(self) -> int:
        return len(self._entries)

    def metrics(self) -> dict:
        """Return cache metrics as a dict.

        Keys: hits, misses, hit_rate (hits / (hits + misses), 0.0 when empty), saved_ms_p50, saved_ms_p95 (percentiles of compute time saved by hits), entries."""

        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": (self.hits / total) if total else 0.0,
            "saved_ms_p50": _percentile(self._saved_ms, 50),
            "saved_ms_p95": _percentile(self._saved_ms, 95),
            "entries": len(self._entries),
        }


def cached_call(
    cache: CacheService,
    key: str,
    manifest: DependencyManifest,
    compute: Callable[[], Any],
) -> tuple[Any, bool]:
    """Return (value, cache_hit). `cache_hit` is Flame's own value.

    On a miss, `compute()` runs and the result is stored unless it is not
    cacheable (see `is_cacheable`).
    """
    hit = cache.get(key)
    if hit is not None:
        return hit, True
    started = time.perf_counter()
    value = compute()
    elapsed_ms = (time.perf_counter() - started) * 1000
    if is_cacheable(value):
        cache.set(key, value, ttl_for(value), manifest.model_dump(), compute_ms=elapsed_ms)
    return value, False
