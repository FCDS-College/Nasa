"""Scientific image analysis. Measurements come from CV code, never from a language model."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ai.providers.contracts.base import Provider


@dataclass(frozen=True, slots=True)
class ImageAnalysisRequest:
    image_path: Path
    image_id: str
    media_type: str
    work_dir: Path
    mm_per_pixel: float | None = None
    max_pixels: int | None = None
    camera_profile: str | None = None    # a cv/configs/camera_profiles.json key (exclusion zones)


@dataclass(frozen=True, slots=True)
class ImageAnalysisResponse:
    analysis: dict[str, Any]                 # cv/flame_cv.py's result shape (preprocessing/segmentation/provenance)
    provider: str
    pipeline_version: str | None = None
    artifacts: dict[str, Path] = field(default_factory=dict)


@runtime_checkable
class VisionProvider(Provider, Protocol):
    def analyze_image(self, request: ImageAnalysisRequest) -> ImageAnalysisResponse: ...
