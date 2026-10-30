"""flame_video analyses on /api/analyses (ADR-005, contract 0.3.0): upload validation, worker, persistence."""
import io
import os
import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image

from api_contract import assert_contract_component
from flame_api import analysis, worker
from flame_api.models import AnalysisRecord, EvidenceRecord

WRITE = {"Authorization": f"Bearer {os.environ['FLAME_WRITE_API_TOKEN']}"}


def _h264_video(path, frames=24, fps=12, size=(128, 96)):
    """A small H.264 MP4 with a bright, pulsing blob (the pipeline only accepts H.264/H.265)."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is not installed")
    width, height = size
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{width}x{height}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    raw = bytearray()
    yy, xx = np.mgrid[0:height, 0:width]
    for index in range(frames):
        frame = np.zeros((height, width, 3), np.uint8)
        radius = 14 + 4 * (index % 4)
        frame[(xx - width // 2) ** 2 + (yy - height // 2) ** 2 <= radius ** 2] = (255, 210, 120)
        raw += frame.tobytes()
    completed = subprocess.run(command, input=bytes(raw), capture_output=True)
    if completed.returncode != 0:
        pytest.skip("ffmpeg cannot encode H.264 (libx264 missing)")
    return path.read_bytes()


class Storage:
    def __init__(self):
        self.objects = {}

    def put_file(self, key, path, media_type):
        with open(path, "rb") as handle:
            self.objects[key] = handle.read()

    def get_bytes(self, key):
        return self.objects[key]


class FakeQueue:
    jobs = []

    def __init__(self, *args, **kwargs):
        pass

    def enqueue(self, *args, **kwargs):
        self.jobs.append((args, kwargs))


@pytest.fixture
def storage(monkeypatch, session_factory):
    store = Storage()
    FakeQueue.jobs.clear()
    monkeypatch.setattr(analysis, "put_file", store.put_file)
    monkeypatch.setattr(analysis, "put_bytes", lambda key, content, media_type: store.objects.__setitem__(key, content))
    monkeypatch.setattr(analysis, "Queue", FakeQueue)
    monkeypatch.setattr(analysis.Redis, "from_url", lambda *args, **kwargs: object())
    monkeypatch.setattr(worker, "get_bytes", store.get_bytes)
    monkeypatch.setattr(worker, "put_file", store.put_file)
    monkeypatch.setattr(worker, "SessionLocal", session_factory)
    return store


def test_video_upload_is_probed_queued_and_contract_valid(client, storage, tmp_path):
    content = _h264_video(tmp_path / "flame.mp4")

    response = client.post("/api/analyses", files={"video": ("flame.mp4", content, "application/octet-stream")},
                           data={"sample_every_n_frames": "4", "max_frames": "5"}, headers=WRITE)

    assert response.status_code == 202, response.json()
    assert_contract_component(response.json(), "AnalysisResponse")
    body = response.json()["analysis"]
    assert body["analysis_type"] == "flame_video"
    assert body["input"]["media_type"] == "video/mp4"
    assert body["input"]["video"]["codec"] in {"h264", "avc1"}
    assert body["input"]["video"]["frame_count"] == 24
    assert body["input"]["video"]["sample_every_n_frames"] == 4
    assert body["artifacts"][0]["media_type"] == "video/mp4"
    (args, kwargs), = FakeQueue.jobs
    assert args == ("flame_api.worker.process_video_analysis", body["analysis_id"])
    assert kwargs["job_timeout"] >= 60
    assert f"analyses/{body['analysis_id']}/original.mp4" in storage.objects


def test_video_upload_rejections(client, storage, tmp_path):
    content = _h264_video(tmp_path / "flame.mp4")
    png = io.BytesIO()
    Image.new("RGB", (80, 72), (240, 190, 90)).save(png, format="PNG")

    def post(files, data=None):
        return client.post("/api/analyses", files=files, data=data or {}, headers=WRITE)

    both = post({"video": ("v.mp4", content), "image": ("i.png", png.getvalue())})
    not_video = post({"video": ("v.mp4", b"definitely not a video container")})
    broken = post({"video": ("v.mp4", b"\x00\x00\x00\x18ftypisom" + b"\x00" * 64)})
    scaled = post({"video": ("v.mp4", content)}, {"scale_px_per_mm": "2", "scale_source": "ruler"})
    too_many = post({"video": ("v.mp4", content)}, {"max_frames": "100000"})
    sampling_on_image = post({"image": ("i.png", png.getvalue())}, {"sample_every_n_frames": "2"})

    assert (both.status_code, both.json()["error"]["code"]) == (400, "VALIDATION_ERROR")
    assert (not_video.status_code, not_video.json()["error"]["code"]) == (415, "UNSUPPORTED_MEDIA_TYPE")
    assert (broken.status_code, broken.json()["error"]["code"]) == (422, "VIDEO_INVALID")
    assert scaled.status_code == 400 and too_many.status_code == 400 and sampling_on_image.status_code == 400
    assert FakeQueue.jobs == []
    for response in (both, not_video, broken, scaled, too_many, sampling_on_image):
        assert_contract_component(response.json(), "ErrorResponse")


def test_worker_produces_a_time_ordered_temporal_result_with_evidence(client, storage, session_factory, tmp_path):
    content = _h264_video(tmp_path / "flame.mp4")
    created = client.post("/api/analyses", files={"video": ("flame.mp4", content)},
                          data={"sample_every_n_frames": "2", "max_frames": "10"}, headers=WRITE)
    analysis_id = created.json()["analysis"]["analysis_id"]

    worker.process_video_analysis(analysis_id)

    detail = client.get(f"/api/analyses/{analysis_id}")
    assert_contract_component(detail.json(), "AnalysisResponse")
    body = detail.json()["analysis"]
    assert body["status"] == "completed", body["failure"]
    result = body["result"]
    assert result["sampling"]["frames_analyzed"] == 10
    indexes = [frame["frame_index"] for frame in result["frames"]]
    assert indexes == sorted(indexes) == list(range(0, 20, 2))
    assert [frame["timestamp_s"] for frame in result["frames"]] == sorted(frame["timestamp_s"] for frame in result["frames"])
    assert result["temporal_summary"]["persistence_rate"] > 0
    # 12 fps sampled every 2nd frame = 0.167 s apart, inside the 0.5 s tracking gap, so tracking is reported
    assert result["temporal_summary"]["track_sessions"] >= 1 and result["temporal_summary"]["tracking_note"] is None
    assert body["pipeline"]["execution"]["provider"] == "flame_cv_video"
    assert body["pipeline"]["execution"]["locality"] == "local"
    assert {w["code"] for w in body["warnings"]} >= {"TEMPERATURE_NOT_AVAILABLE", "SCALE_CALIBRATION_ABSENT"}
    evidence_id = result["observations"][0]["evidence_ids"][0]
    with session_factory() as session:
        evidence = session.get(EvidenceRecord, evidence_id)
        assert evidence.kind == "video_measurement" and evidence.analysis_id == analysis_id
    evidence_response = client.get(f"/api/evidence/{evidence_id}")
    assert evidence_response.status_code == 200
    assert_contract_component(evidence_response.json(), "EvidenceResponse")
    listed = client.get("/api/analyses").json()["items"][0]
    assert listed["analysis_type"] == "flame_video"


def test_tracking_is_not_estimable_when_sampled_frames_are_too_far_apart(client, storage, tmp_path):
    content = _h264_video(tmp_path / "flame.mp4")
    created = client.post("/api/analyses", files={"video": ("flame.mp4", content)},
                          data={"sample_every_n_frames": "12", "max_frames": "2"}, headers=WRITE)
    analysis_id = created.json()["analysis"]["analysis_id"]

    worker.process_video_analysis(analysis_id)

    body = client.get(f"/api/analyses/{analysis_id}").json()
    assert_contract_component(body, "AnalysisResponse")
    summary = body["analysis"]["result"]["temporal_summary"]
    assert summary["track_sessions"] is None and summary["tracking_stability_px2"] is None
    assert "1.000 s exceeds" in summary["tracking_note"]


def test_worker_marks_a_video_the_pipeline_rejects_as_failed(client, storage, session_factory, tmp_path, monkeypatch):
    from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
    from ai.routing import ExecutionMode, NoCompatibleProvider

    content = _h264_video(tmp_path / "flame.mp4")
    analysis_id = client.post("/api/analyses", files={"video": ("flame.mp4", content)}, headers=WRITE).json()["analysis"]["analysis_id"]

    class Rejecting:
        def route(self, task, call):
            error = ProviderError(ProviderErrorCode.INVALID_REQUEST, "bad stream", provider="flame_cv_video")
            raise NoCompatibleProvider(task, ExecutionMode.LOCAL_FIRST, [], last_error=error)

    monkeypatch.setattr(worker.ai_runtime, "get_router", lambda *_: Rejecting())
    with pytest.raises(NoCompatibleProvider):
        worker.process_video_analysis(analysis_id)

    with session_factory() as session:
        record = session.get(AnalysisRecord, analysis_id)
        assert record.status == "failed"
        assert record.payload["failure"] == {"code": "VIDEO_DECODE_FAILED", "message": "Video analysis could not be completed.",
                                             "retryable": False}


def test_unexpected_interpretation_error_keeps_the_image_analysis_completed(client, storage, session_factory, monkeypatch):
    stream = io.BytesIO()
    image = Image.new("RGB", (160, 120), (0, 0, 0))
    image.paste((255, 200, 120), (60, 40, 100, 80))
    image.save(stream, format="PNG")
    analysis_id = client.post("/api/analyses", files={"image": ("flame.png", stream.getvalue())}, headers=WRITE).json()["analysis"]["analysis_id"]
    with session_factory() as session:
        record = session.get(AnalysisRecord, analysis_id)
        record.payload = {**record.payload, "interpretation": {**record.payload["interpretation"], "status": "pending"}}
        session.commit()

    def broken(*_args, **_kwargs):
        raise RuntimeError("bug in interpretation code")

    monkeypatch.setattr(worker, "_run_aura_interpretation", broken)
    worker.process_analysis(analysis_id)

    with session_factory() as session:
        record = session.get(AnalysisRecord, analysis_id)
        assert record.status == "completed"
        assert record.payload["interpretation"]["status"] == "unavailable"


def test_method_not_allowed_has_a_stable_code(client):
    response = client.delete("/api/health", headers=WRITE)

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert_contract_component(response.json(), "ErrorResponse")
