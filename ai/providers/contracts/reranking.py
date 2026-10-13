"""Reranking (query, passage) pairs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ai.providers.contracts.base import Provider


@dataclass(frozen=True, slots=True)
class RerankRequest:
    query: str
    documents: tuple[tuple[str, str], ...]   # (id, text)
    top_k: int | None = None


@dataclass(frozen=True, slots=True)
class RerankResponse:
    scores: tuple[tuple[str, float], ...]    # (id, score), best first
    model: str


@runtime_checkable
class RerankProvider(Provider, Protocol):
    def rerank(self, request: RerankRequest) -> RerankResponse: ...
