"""Speech transcription, implemented locally by `ai/providers/local/faster_whisper_transcription.py`.

``audio_path`` may be a WAV or any media file with an audio track; the provider decodes it itself."""
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
    language: str | None = None   # detected (or requested) language code, e.g. "en"


@runtime_checkable
class TranscriptionProvider(Provider, Protocol):
    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResponse: ...
