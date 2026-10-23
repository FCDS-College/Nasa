"""Execution modes, task → capability map, and candidate ordering.

Modes (2H §7A.5):
* ``cloud_preferred`` — external providers first, local fallback.
* ``local_first``     — local providers first, external fallback where permitted.
* ``offline_only``    — external providers are never contacted (the egress guarantee).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ai.providers.contracts.base import Capability, Locality, Provider


class ExecutionMode(str, Enum):
    CLOUD_PREFERRED = "cloud_preferred"
    LOCAL_FIRST = "local_first"
    OFFLINE_ONLY = "offline_only"


@dataclass(frozen=True, slots=True)
class Task:
    name: str
    capability: Capability
    modality: str = "text"          # a vision task needs a provider whose modalities include "image"
    idempotent: bool = True         # safe to resend to another provider after it may have been received
    needs_internet: bool = False    # the operation is meaningless without external data


TASKS: dict[str, Task] = {
    t.name: t
    for t in (
        Task("chat.answer", Capability.STRUCTURED),
        Task("analysis.interpret", Capability.STRUCTURED),
        Task("text.generate", Capability.CHAT),
        Task("embed.query", Capability.EMBEDDINGS),
        Task("embed.documents", Capability.EMBEDDINGS),
        Task("rerank", Capability.RERANKING),
        Task("vision.analyze", Capability.VISION, modality="image"),
        Task("video.analyze", Capability.VIDEO, modality="video"),
        Task("speech.transcribe", Capability.TRANSCRIPTION, modality="audio"),
    )
}


def permitted(provider: Provider, mode: ExecutionMode) -> bool:
    return not (mode is ExecutionMode.OFFLINE_ONLY and provider.info.locality is Locality.EXTERNAL)


def compatible(provider: Provider, task: Task) -> bool:
    info = provider.info
    if task.capability not in info.capabilities:
        return False
    # Never hand a scientific vision/video/audio task to a text-only model.
    return task.modality == "text" or task.modality in info.modalities


def order(candidates: list[tuple[int, Provider]], mode: ExecutionMode) -> list[Provider]:
    """Sort by (locality preference for the mode, registered priority, name) — deterministic."""

    def key(item: tuple[int, Provider]) -> tuple[int, int, str]:
        priority, provider = item
        local = provider.info.locality is Locality.LOCAL
        locality_rank = (0 if local else 1) if mode is not ExecutionMode.CLOUD_PREFERRED else (1 if local else 0)
        return (locality_rank, priority, provider.info.name)

    return [provider for _, provider in sorted(candidates, key=key)]
