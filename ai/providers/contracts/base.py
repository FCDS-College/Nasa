"""Capabilities, locality and the minimal shape every provider shares."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable


class Capability(str, Enum):
    CHAT = "chat"                      # free-text generation
    STRUCTURED = "structured"          # JSON output constrained by a schema
    EMBEDDINGS = "embeddings"
    RERANKING = "reranking"
    VISION = "vision"                  # scientific image analysis (measurements, masks)
    VIDEO = "video"
    TRANSCRIPTION = "transcription"


class Locality(str, Enum):
    """Network location, not hardware: a vLLM server on the same disconnected LAN is LOCAL."""

    LOCAL = "local"
    EXTERNAL = "external"


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    name: str                              # stable id, e.g. "ollama", "aura", "fastembed"
    runtime: str                           # "ollama", "vllm", "llama.cpp", "aura", "fastembed", "flame_cv", ...
    locality: Locality
    capabilities: frozenset[Capability]
    model: str | None = None
    version: str | None = None
    context_window: int | None = None
    # Text-only providers must never be handed a vision task; the router checks this flag too.
    modalities: frozenset[str] = field(default_factory=lambda: frozenset({"text"}))


@dataclass(frozen=True, slots=True)
class HealthStatus:
    state: str                             # "up" | "down" | "degraded" | "unknown"
    latency_ms: float | None = None
    detail: str | None = None              # low-cardinality reason code, never vendor text
    model_present: bool | None = None

    @property
    def usable(self) -> bool:
        return self.state in {"up", "degraded", "unknown"}


@runtime_checkable
class Provider(Protocol):
    info: ProviderInfo

    def health(self, timeout_s: float) -> HealthStatus:
        """A bounded readiness probe. Must not raise and must return within ``timeout_s`` (+ε)."""
        ...
