"""The local video provider and its routing (Workstream A, 2H Task 3). Real OpenCV, tiny synthetic video."""
import cv2
import numpy as np
import pytest

from ai.providers.contracts.base import Capability
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
from ai.providers.contracts.video import VideoAnalysisRequest, VideoProvider
from ai.providers.local.flame_cv_video import FlameCvVideoProvider
from ai.routing import CircuitBreaker, ExecutionMode, HealthMonitor, ProviderRegistry, Router
from cv import video_analysis
from cv.video_ingestion import VideoConfig


def make_video(path, frames=12, fps=20.0, size=(320, 240)):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, size)
    for i in range(frames):
        img = np.zeros((size[1], size[0], 3), np.uint8)
        cv2.ellipse(img, (160, 120), (50 + i % 3, 60), 0, 0, 360, (80, 200, 255), -1)
        writer.write(cv2.GaussianBlur(img, (0, 0), 3))
    writer.release()
    return path


@pytest.fixture
def allow_test_codec(monkeypatch):
    real = video_analysis.analyze_video

    def lenient(video_path, work_dir, video_cfg=None, **kwargs):
        cfg = VideoConfig(allowed_codecs=None, sample_every=video_cfg.sample_every, max_frames=video_cfg.max_frames)
        return real(video_path, work_dir, video_cfg=cfg, **kwargs)

    monkeypatch.setattr(video_analysis, "analyze_video", lenient)


def router():
    registry = ProviderRegistry()
    registry.register(FlameCvVideoProvider())
    return Router(registry, mode=ExecutionMode.OFFLINE_ONLY, breaker=CircuitBreaker(threshold=3, cooldown_s=30),
                  monitor=HealthMonitor())


def test_provider_satisfies_the_contract_and_is_local():
    provider = FlameCvVideoProvider()
    assert isinstance(provider, VideoProvider)
    assert provider.info.capabilities == frozenset({Capability.VIDEO}) and "video" in provider.info.modalities
    assert provider.health(1.0).state == "up"


def test_video_task_routes_offline_and_returns_frames(tmp_path, allow_test_codec):
    video = make_video(tmp_path / "flame.avi")
    request = VideoAnalysisRequest(video, "vid-1", tmp_path / "work", sample_every_n_frames=2)
    routed = router().route("video.analyze", lambda p: p.analyze_video(request))
    assert routed.metadata.provider == "flame_cv_video" and routed.metadata.locality == "local"
    assert len(routed.value.frames) == 6
    assert routed.value.summary["temporalSummary"]


def test_resuming_the_same_work_dir_reuses_the_checkpoint(tmp_path, allow_test_codec):
    video = make_video(tmp_path / "flame.avi")
    request = VideoAnalysisRequest(video, "vid-1", tmp_path / "work", sample_every_n_frames=1, max_frames=4)
    provider = FlameCvVideoProvider()
    first = provider.analyze_video(request)
    second = provider.analyze_video(request)
    assert first.summary["analysisId"] == second.summary["analysisId"]
    assert len(first.frames) == len(second.frames) == 4


def test_rejected_input_is_an_invalid_request(tmp_path):
    bad = tmp_path / "not-a-video.avi"
    bad.write_bytes(b"nope")
    with pytest.raises(ProviderError) as err:
        FlameCvVideoProvider().analyze_video(VideoAnalysisRequest(bad, "vid-2", tmp_path / "work"))
    assert err.value.code is ProviderErrorCode.INVALID_REQUEST

def test_camera_profile_reaches_the_video_pipeline(tmp_path, monkeypatch):
    seen = {}

    def fake_analyze_video(video_path, work_dir, cfg=None, video_cfg=None, **kwargs):
        seen["cfg"] = cfg
        return {"frameMeasurements": [], "pipelineVersion": "x"}

    monkeypatch.setattr(video_analysis, "analyze_video", fake_analyze_video)
    video = make_video(tmp_path / "flame.avi")
    FlameCvVideoProvider().analyze_video(VideoAnalysisRequest(video, "vid-3", tmp_path / "w", camera_profile="flex-colour"))
    assert seen["cfg"].camera_profile == "flex-colour" and seen["cfg"].exclude_regions
    FlameCvVideoProvider().analyze_video(VideoAnalysisRequest(video, "vid-4", tmp_path / "w2"))
    assert seen["cfg"] is None or not seen["cfg"].exclude_regions


def test_image_provider_applies_the_camera_profile(tmp_path):
    from ai.providers.contracts.vision import ImageAnalysisRequest
    from ai.providers.local.flame_cv import FlameCvProvider
    img = np.zeros((480, 640, 3), np.uint8)
    cv2.ellipse(img, (320, 440), (60, 15), 0, 180, 360, (60, 60, 230), 6)
    path = tmp_path / "arc.png"
    cv2.imwrite(str(path), img)
    (tmp_path / "w").mkdir()
    response = FlameCvProvider().analyze_image(
        ImageAnalysisRequest(path, "arc", "image/png", tmp_path / "w", camera_profile="flex-colour"))
    assert response.analysis["preprocessing"]["cameraProfile"] == "flex-colour"
    assert response.analysis["detection"]["status"] == "ABSENT"
