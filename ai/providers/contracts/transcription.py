"""Speech transcription. Contract only: transcription is not in the first offline feature set."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from ai.providers.contracts.base import Provider


@dataclass(frozen=True, slots=True)
class TranscriptionRequest:
    audio_path: Path
    language: str | None = None


@dataclass(frozen=True, slots=True)
class TranscriptionResponse:
    text: str
    segments: tuple[dict, ...]
    model: str
    provider: str


@runtime_checkable
class TranscriptionProvider(Provider, Protocol):
    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResponse: ...
