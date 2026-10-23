"""Abstract interfaces for the Flame AI layer.

Every concrete service (retriever, reranker, LLM, cache, memory, composer)
implements one of these ABCs so the API layer can swap implementations and
tests can inject fakes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class EmbeddingProvider(ABC):
    """Turns text into vectors. Must expose name/version for provenance."""

    name: str = "unknown"
    version: str = "0"

    @abstractmethod
    def embed_text(self, text: str):
        """Return one embedding vector for `text`."""

    @abstractmethod
    def embed_batch(self, texts: list[str]):
        """Return an array of embeddings, one row per input text."""


class Retriever(ABC):
    @abstractmethod
    def retrieve(self, request, chunks):
        """Take a RetrievalRequest and candidate chunks; return an EvidenceBundle."""


class Reranker(ABC):
    name: str = "unknown"
    version: str = "0"

    @abstractmethod
    def rerank(self, query: str, results: list[dict], top_k: int = 5) -> list[dict]:
        """Return `results` re-ordered by relevance, each with `rerank_score`."""


class LLMProvider(ABC):
    name: str = "unknown"
    version: str = "0"

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return the raw model output (expected to be JSON for the composer)."""


class CacheService(ABC):
    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Return the cached value or None (miss/expired)."""

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: float, manifest: dict, compute_ms: float = 0.0) -> None:
        """Store `value` with its dependency manifest."""

    @abstractmethod
    def invalidate_corpus(self, current_corpus_version: str) -> int:
        """Drop every entry built on a different corpus version. Return count."""


class MemoryStore(ABC):
    @abstractmethod
    def add(self, record):
        """Persist a memory record."""

    @abstractmethod
    def search(self, user_id: str, conversation_id: str, query: str, top_k: int = 5):
        """Return relevant, unexpired memory visible to exactly this user+conversation."""

    @abstractmethod
    def delete_conversation(self, user_id: str, conversation_id: str) -> int:
        """Delete all memory for a conversation. Return count."""


class AnswerComposer(ABC):
    @abstractmethod
    def compose(self, question: str, bundle, memory=None):
        """Return a GroundedAnswer built only from `bundle` evidence."""
