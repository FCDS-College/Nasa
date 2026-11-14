"""Video analysis (Workstream A), implemented locally by `ai/providers/local/flame_cv_video.py`."""
from __future__ import annotations

from collections.abc import Callable
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
    camera_profile: str | None = None    # a cv/configs/camera_profiles.json key (exclusion zones)
    # ADR-008: a checkpoint kept by the caller ({"video_id", "digest", "rows"}) to resume from, and a
    # hook called with each progress event. The hook may raise to stop the job (cancellation); the
    # frames checkpointed so far survive. Neither takes part in equality.
    resume_from: dict[str, Any] | None = field(default=None, compare=False)
    on_frame: Callable[[dict[str, Any]], None] | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class VideoAnalysisResponse:
    frames: tuple[dict[str, Any], ...]
    provider: str
    pipeline_version: str | None = None
    summary: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class VideoProvider(Provider, Protocol):
    def analyze_video(self, request: VideoAnalysisRequest) -> VideoAnalysisResponse: ...
