"""Flame's own OpenCV pipeline (``cv/flame_cv.py``) as the local vision provider."""
from __future__ import annotations

import importlib.util
import time

from ai.providers.contracts.base import Capability, HealthStatus, Locality, ProviderInfo
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
from ai.providers.contracts.vision import ImageAnalysisRequest, ImageAnalysisResponse


class FlameCvProvider:
    def __init__(self) -> None:
        self.info = ProviderInfo(
            name="flame_cv", runtime="opencv", locality=Locality.LOCAL,
            capabilities=frozenset({Capability.VISION}), model="flame_cv", version=self._version(),
            modalities=frozenset({"image"}),
        )

    @staticmethod
    def _version() -> str | None:
        try:
            from cv.flame_cv import PIPELINE_VERSION
        except ImportError:
            return None
        return PIPELINE_VERSION

    def health(self, timeout_s: float) -> HealthStatus:
        started = time.perf_counter()
        missing = [name for name in ("cv2", "numpy", "PIL") if importlib.util.find_spec(name) is None]
        latency = round((time.perf_counter() - started) * 1000, 1)
        if missing:
            return HealthStatus("down", latency, "dependency_missing", model_present=False)
        return HealthStatus("up", latency, model_present=True)

    def analyze_image(self, request: ImageAnalysisRequest) -> ImageAnalysisResponse:
        try:
            from cv.flame_cv import CVConfig, CVError, analyze_image
        except ImportError as exc:
            raise ProviderError(ProviderErrorCode.MODEL_MISSING, "The local CV pipeline is not installed.",
                                provider="flame_cv", request_sent=False) from exc
        config = CVConfig(max_pixels=request.max_pixels) if request.max_pixels else CVConfig()
        try:
            analysis = analyze_image(
                {"imagePath": str(request.image_path), "imageId": request.image_id,
                 "metadata": {"mmPerPixel": request.mm_per_pixel, "cameraProfile": request.camera_profile}},
                request.work_dir / "processed", request.work_dir / "masks", cfg=config,
            )
        except CVError as exc:
            code = ProviderErrorCode.UNAVAILABLE if exc.retryable else ProviderErrorCode.INVALID_REQUEST
            raise ProviderError(code, exc.message, provider="flame_cv") from exc
        except MemoryError as exc:
            raise ProviderError(ProviderErrorCode.RESOURCE_EXHAUSTED, "The image is too large for local CV.",
                                provider="flame_cv") from exc
        return ImageAnalysisResponse(analysis=analysis, provider="flame_cv",
                                     pipeline_version=analysis.get("pipelineVersion"))
