"""Structured (JSON-schema constrained) output."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from ai.providers.contracts.base import Provider
from ai.providers.contracts.chat import ChatRequest


@dataclass(frozen=True, slots=True)
class StructuredRequest:
    chat: ChatRequest
    schema: dict[str, Any]


@dataclass(frozen=True, slots=True)
class StructuredResponse:
    data: dict[str, Any]
    model: str
    provider: str
    cached: bool = False
    usage: dict = field(default_factory=dict)


@runtime_checkable
class StructuredProvider(Provider, Protocol):
    def generate_structured(self, request: StructuredRequest) -> StructuredResponse:
        """Returns a JSON object. Callers still validate it: a provider's schema support is a hint."""
        ...
