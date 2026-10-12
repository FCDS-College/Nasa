"""Video analysis (Workstream A). Contract only: no adapter implements it yet."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ai.providers.contracts.base import Provider


@dataclass(frozen=True, slots=True)
class VideoAnalysisRequest:
    video_path: Path
    video_id: str
    work_dir: Path
    sample_every_n_frames: int = 30
    max_frames: int | None = None


@dataclass(frozen=True, slots=True)
class VideoAnalysisResponse:
    frames: tuple[dict[str, Any], ...]
    provider: str
    pipeline_version: str | None = None
    summary: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class VideoProvider(Provider, Protocol):
    def analyze_video(self, request: VideoAnalysisRequest) -> VideoAnalysisResponse: ...
