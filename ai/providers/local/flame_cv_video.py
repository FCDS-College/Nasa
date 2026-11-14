"""Flame's resumable video pipeline (``cv/video_analysis.py``) as the local video provider."""
from __future__ import annotations

import importlib.util
import time

from ai.providers.contracts.base import Capability, HealthStatus, Locality, ProviderInfo
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
from ai.providers.contracts.video import VideoAnalysisRequest, VideoAnalysisResponse


class FlameCvVideoProvider:
    def __init__(self) -> None:
        self.info = ProviderInfo(
            name="flame_cv_video", runtime="opencv", locality=Locality.LOCAL,
            capabilities=frozenset({Capability.VIDEO}), model="flame_cv_video", version=self._version(),
            modalities=frozenset({"video"}),
        )

    @staticmethod
    def _version() -> str | None:
        try:
            from cv.video_analysis import VIDEO_PIPELINE_VERSION
        except ImportError:
            return None
        return VIDEO_PIPELINE_VERSION

    def health(self, timeout_s: float) -> HealthStatus:
        started = time.perf_counter()
        missing = [name for name in ("cv2", "numpy", "PIL") if importlib.util.find_spec(name) is None]
        latency = round((time.perf_counter() - started) * 1000, 1)
        if missing:
            return HealthStatus("down", latency, "dependency_missing", model_present=False)
        return HealthStatus("up", latency, model_present=True)

    def analyze_video(self, request: VideoAnalysisRequest) -> VideoAnalysisResponse:
        try:
            from cv.flame_cv import CVConfig, CVError, with_camera_profile
            from cv.video_analysis import analyze_video, seed_checkpoint
            from cv.video_ingestion import VideoConfig
        except ImportError as exc:
            raise ProviderError(ProviderErrorCode.MODEL_MISSING, "The local video pipeline is not installed.",
                                provider="flame_cv_video", request_sent=False) from exc
        config = VideoConfig(sample_every=max(1, request.sample_every_n_frames), max_frames=request.max_frames)
        try:
            # Re-running with the same work_dir resumes from the JSONL checkpoint (L-6 job recovery); a
            # checkpoint the caller kept elsewhere is written back into the work_dir first (ADR-008).
            seed = request.resume_from
            if seed and seed.get("rows"):
                seed_checkpoint(request.work_dir, seed["video_id"], seed["digest"], list(seed["rows"]))
            cfg = with_camera_profile(CVConfig(), request.camera_profile) if request.camera_profile else None
            result = analyze_video(request.video_path, request.work_dir, cfg=cfg, video_cfg=config,
                                   on_frame=request.on_frame)
        except CVError as exc:
            code = ProviderErrorCode.UNAVAILABLE if exc.retryable else ProviderErrorCode.INVALID_REQUEST
            raise ProviderError(code, exc.message, provider="flame_cv_video") from exc
        except MemoryError as exc:
            raise ProviderError(ProviderErrorCode.RESOURCE_EXHAUSTED, "The video is too large for local CV.",
                                provider="flame_cv_video") from exc
        return VideoAnalysisResponse(
            frames=tuple(result["frameMeasurements"]), provider="flame_cv_video",
            pipeline_version=result.get("pipelineVersion"),
            summary={k: result[k] for k in ("videoId", "analysisId", "temporalSummary", "videoMetadata", "artifacts")
                     if k in result},
        )