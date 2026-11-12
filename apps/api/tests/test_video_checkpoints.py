"""ADR-008: video jobs checkpoint per segment, resume after a crash, and can be cancelled."""
import io
import os
from datetime import UTC, datetime

import pytest
from PIL import Image
from sqlalchemy import select

from api_contract import assert_contract_component
from flame_api import analysis, worker
from flame_api.models import AnalysisRecord, EvidenceRecord, VideoCheckpointFrame
from test_video_analysis import FakeQueue, Storage, _h264_video

WRITE = {"Authorization": f"Bearer {os.environ['FLAME_WRITE_API_TOKEN']}"}
READ = {"Authorization": f"Bearer {os.environ['FLAME_READ_API_TOKEN']}"}


class Crash(BaseException):
    """A worker killed mid-job (SIGKILL, OOM, container replaced): no `except Exception` sees it."""


class Queue:
    def __init__(self):
        self.jobs = []

    def fetch_job(self, job_id):
        return None

    def enqueue(self, job, analysis_id, **kwargs):
        self.jobs.append(analysis_id)


@pytest.fixture
def storage(monkeypatch, session_factory):
    """As in test_video_analysis: in-memory object storage, no Redis, the worker on the test database."""
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


@pytest.fixture
def every_two(monkeypatch):
    monkeypatch.setattr(worker.settings, "video_checkpoint_every_frames", 2)


def _video(client, tmp_path, frames="10"):
    content = _h264_video(tmp_path / "flame.mp4")
    created = client.post("/api/analyses", files={"video": ("flame.mp4", content)},
                          data={"sample_every_n_frames": "2", "max_frames": frames}, headers=WRITE)
    assert created.status_code == 202
    return created.json()["analysis"]["analysis_id"]


def _checkpoint_rows(session_factory, analysis_id):
    with session_factory() as session:
        return list(session.scalars(select(VideoCheckpointFrame.frame_index)
                                    .where(VideoCheckpointFrame.analysis_id == analysis_id)
                                    .order_by(VideoCheckpointFrame.frame_index)))


def _crash_after(monkeypatch, frames):
    """Let flushes through until `frames` sampled frames are stored, then kill the worker."""
    original = worker.VideoCheckpoint.flush

    def flush(self):
        original(self)
        if self.done >= frames:
            raise Crash()

    monkeypatch.setattr(worker.VideoCheckpoint, "flush", flush)


def test_a_crashed_video_job_resumes_after_its_last_segment(client, storage, session_factory, tmp_path, monkeypatch,
                                                            every_two):
    reference_id = _video(client, tmp_path)
    worker.process_video_analysis(reference_id)
    reference = client.get(f"/api/analyses/{reference_id}").json()["analysis"]["result"]

    analysis_id = _video(client, tmp_path)
    with monkeypatch.context() as patch:
        _crash_after(patch, 4)
        with pytest.raises(Crash):
            worker.process_video_analysis(analysis_id)

    # The dead job is still `processing`, with two segments of two frames stored and visible progress.
    assert _checkpoint_rows(session_factory, analysis_id) == [0, 2, 4, 6]
    running = client.get(f"/api/analyses/{analysis_id}")
    assert_contract_component(running.json(), "AnalysisResponse")
    body = running.json()["analysis"]
    assert body["status"] == "processing"
    assert {k: body["progress"][k] for k in ("frames_done", "frames_total")} == {"frames_done": 4, "frames_total": 10}

    # Recovery re-queues it; the next run measures only the six missing frames.
    queue = Queue()
    seen = []
    original_call = worker.VideoCheckpoint.__call__

    def record(self, event):
        seen.append((event["event"], event["done"]))
        original_call(self, event)

    monkeypatch.setattr(worker.VideoCheckpoint, "__call__", record)
    assert worker.recover(older_than=0, queue=queue) == {"requeued": 1, "failed": 0, "skipped": 0, "cancelled": 0}
    assert queue.jobs == [analysis_id]
    worker.process_video_analysis(analysis_id)

    assert seen[0] == ("start", 4) and [done for event, done in seen if event == "frame"] == [5, 6, 7, 8, 9, 10]
    detail = client.get(f"/api/analyses/{analysis_id}").json()
    assert_contract_component(detail, "AnalysisResponse")
    body = detail["analysis"]
    assert body["status"] == "completed"
    # The resumed result is the uninterrupted one, frame for frame.
    assert body["result"]["frames"] == reference["frames"]
    assert body["result"]["temporal_summary"] == reference["temporal_summary"]
    resumed = [w for w in body["warnings"] if w["code"] == "JOB_RESUMED_FROM_CHECKPOINT"]
    assert len(resumed) == 1 and "4 of 10 sampled frames" in resumed[0]["message"]
    assert {w["code"] for w in body["warnings"]} >= {"JOB_RECOVERED"}
    # A finished job keeps no checkpoint.
    assert _checkpoint_rows(session_factory, analysis_id) == []


def test_a_checkpoint_from_another_job_digest_is_ignored(client, storage, session_factory, tmp_path, every_two):
    analysis_id = _video(client, tmp_path)
    with session_factory() as session:
        record = session.get(AnalysisRecord, analysis_id)
        session.add(VideoCheckpointFrame(analysis_id=analysis_id, frame_index=0, video_id="vid_stale", job_digest="0" * 16,
                                         row={"frameIndex": 0, "detectionStatus": "ABSENT"}, created_at=record.created_at))
        session.commit()

    worker.process_video_analysis(analysis_id)

    body = client.get(f"/api/analyses/{analysis_id}").json()["analysis"]
    assert body["status"] == "completed" and body["result"]["sampling"]["frames_analyzed"] == 10
    assert body["result"]["frames"][0]["detection_status"] == "present"
    assert "JOB_RESUMED_FROM_CHECKPOINT" not in {w["code"] for w in body["warnings"]}


def test_a_queued_analysis_is_cancelled_at_once_and_never_runs(client, storage, session_factory, tmp_path):
    analysis_id = _video(client, tmp_path)

    response = client.post(f"/api/analyses/{analysis_id}/cancel", headers=WRITE)

    assert response.status_code == 200
    assert_contract_component(response.json(), "AnalysisResponse")
    body = response.json()["analysis"]
    assert body["status"] == "cancelled" and body["poll_after_ms"] is None and body["completed_at"] is not None
    assert body["failure"] == {"code": "CANCELLED", "message": "The analysis was cancelled on request.", "retryable": False}
    assert body["cancel_requested_at"] is not None
    worker.process_video_analysis(analysis_id)   # the RQ job still runs; it must do nothing
    assert client.get(f"/api/analyses/{analysis_id}").json()["analysis"] == body
    again = client.post(f"/api/analyses/{analysis_id}/cancel", headers=WRITE)
    assert again.status_code == 200 and again.json()["analysis"] == body


def test_a_running_video_stops_at_its_next_checkpoint(client, storage, session_factory, tmp_path, monkeypatch,
                                                     every_two):
    analysis_id = _video(client, tmp_path)
    original = worker.VideoCheckpoint.flush
    replies = []

    def flush(self):
        original(self)
        if self.done == 2:   # someone cancels while the job runs
            replies.append(client.post(f"/api/analyses/{analysis_id}/cancel", headers=WRITE))

    monkeypatch.setattr(worker.VideoCheckpoint, "flush", flush)
    worker.process_video_analysis(analysis_id)

    accepted = replies[0]
    assert accepted.status_code == 202 and accepted.headers["Retry-After"] == "1"
    assert_contract_component(accepted.json(), "AnalysisResponse")
    assert accepted.json()["analysis"]["status"] == "processing"
    assert accepted.json()["analysis"]["cancel_requested_at"] is not None
    body = client.get(f"/api/analyses/{analysis_id}").json()
    assert_contract_component(body, "AnalysisResponse")
    analysis = body["analysis"]
    assert analysis["status"] == "cancelled" and analysis["failure"]["code"] == "CANCELLED"
    assert analysis["result"] is None
    assert analysis["progress"]["frames_done"] == 4   # it stopped at the next segment, not at the end
    assert _checkpoint_rows(session_factory, analysis_id) == []
    with session_factory() as session:
        assert session.scalars(select(EvidenceRecord).where(EvidenceRecord.analysis_id == analysis_id)).first() is None


def test_an_image_job_with_a_cancel_request_stores_no_result(client, storage, session_factory, monkeypatch):
    stream = io.BytesIO()
    image = Image.new("RGB", (160, 120), (0, 0, 0))
    image.paste((255, 200, 120), (60, 40, 100, 80))
    image.save(stream, format="PNG")
    analysis_id = client.post("/api/analyses", files={"image": ("flame.png", stream.getvalue())},
                              headers=WRITE).json()["analysis"]["analysis_id"]
    original = worker._adapt_result

    def adapt_then_cancel(*args, **kwargs):
        adapted = original(*args, **kwargs)
        assert client.post(f"/api/analyses/{analysis_id}/cancel", headers=WRITE).status_code == 202
        return adapted

    monkeypatch.setattr(worker, "_adapt_result", adapt_then_cancel)
    worker.process_analysis(analysis_id)

    body = client.get(f"/api/analyses/{analysis_id}").json()
    assert_contract_component(body, "AnalysisResponse")
    assert body["analysis"]["status"] == "cancelled" and body["analysis"]["result"] is None
    assert "progress" not in body["analysis"]


def test_finished_unknown_and_unauthorised_cancels_are_refused(client, storage, session_factory, tmp_path):
    analysis_id = _video(client, tmp_path, frames="2")
    worker.process_video_analysis(analysis_id)

    finished = client.post(f"/api/analyses/{analysis_id}/cancel", headers=WRITE)
    assert finished.status_code == 409
    assert_contract_component(finished.json(), "ErrorResponse")
    assert finished.json()["error"]["code"] == "ANALYSIS_NOT_CANCELLABLE"
    assert "already completed" in finished.json()["error"]["message"]
    assert client.get(f"/api/analyses/{analysis_id}").json()["analysis"]["status"] == "completed"

    unknown = client.post("/api/analyses/01J9Z3Q9D3F5H7K9N1R3T5W7Y9/cancel", headers=WRITE)
    assert unknown.status_code == 404 and unknown.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"
    assert client.post(f"/api/analyses/{analysis_id}/cancel", headers=READ).status_code == 401


def test_recovery_cancels_a_stuck_job_that_had_a_cancel_request(client, storage, session_factory, tmp_path, monkeypatch,
                                                                every_two):
    analysis_id = _video(client, tmp_path)
    with monkeypatch.context() as patch:
        _crash_after(patch, 2)
        with pytest.raises(Crash):
            worker.process_video_analysis(analysis_id)
    assert client.post(f"/api/analyses/{analysis_id}/cancel", headers=WRITE).status_code == 202
    assert _checkpoint_rows(session_factory, analysis_id) == [0, 2]

    queue = Queue()
    counts = worker.recover(older_than=0, queue=queue, now=datetime.now(UTC))

    assert counts == {"requeued": 0, "failed": 0, "skipped": 0, "cancelled": 1} and queue.jobs == []
    body = client.get(f"/api/analyses/{analysis_id}").json()
    assert_contract_component(body, "AnalysisResponse")
    assert body["analysis"]["status"] == "cancelled" and body["analysis"]["failure"]["code"] == "CANCELLED"
    assert _checkpoint_rows(session_factory, analysis_id) == []


def test_a_failed_video_job_keeps_no_checkpoint(client, storage, session_factory, tmp_path, monkeypatch, every_two):
    analysis_id = _video(client, tmp_path)
    original = worker.VideoCheckpoint.flush

    def flush(self):
        original(self)
        if self.done >= 4:
            raise RuntimeError("disk full")

    monkeypatch.setattr(worker.VideoCheckpoint, "flush", flush)
    with pytest.raises(RuntimeError):
        worker.process_video_analysis(analysis_id)

    assert client.get(f"/api/analyses/{analysis_id}").json()["analysis"]["status"] == "failed"
    assert _checkpoint_rows(session_factory, analysis_id) == []

