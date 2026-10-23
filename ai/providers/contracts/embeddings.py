"""Embedding generation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ai.providers.contracts.base import Provider


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    texts: tuple[str, ...]
    query: bool = False


@dataclass(frozen=True, slots=True)
class EmbeddingResponse:
    vectors: tuple[tuple[float, ...], ...]
    model: str
    dimensions: int


@runtime_checkable
class EmbeddingProvider(Provider, Protocol):
    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse: ...
