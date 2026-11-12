"""P2-4: analyses left in `processing` by a dead worker are re-queued, capped, and never double-claimed."""
import io
import os
from datetime import UTC, datetime, timedelta

import pytest
from PIL import Image

from api_contract import assert_contract_component
from flame_api import analysis, worker
from flame_api.models import AnalysisRecord

WRITE = {"Authorization": f"Bearer {os.environ['FLAME_WRITE_API_TOKEN']}"}
NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


class FakeJob:
    def __init__(self, status):
        self.status = status

    def get_status(self, refresh=True):
        return self.status


class FakeQueue:
    """Stands in for the RQ queue: enqueue records the call and makes the job visible to fetch_job."""

    def __init__(self, live=()):
        self.jobs = []
        self.live = {analysis_id: FakeJob("queued") for analysis_id in live}

    def fetch_job(self, job_id):
        return self.live.get(job_id)

    def enqueue(self, job, analysis_id, **kwargs):
        self.jobs.append((job, analysis_id, kwargs))
        self.live[analysis_id] = FakeJob("queued")


def _payload(analysis_id, analysis_type, status, updated_at, warnings=()):
    stamp = updated_at.isoformat().replace("+00:00", "Z")
    video = analysis_type == "flame_video"
    return {
        "analysis_id": analysis_id, "analysis_type": analysis_type, "status": status,
        "created_at": stamp, "updated_at": stamp, "started_at": stamp if status == "processing" else None,
        "completed_at": None,
        "input": {"media_type": "video/mp4" if video else "image/png"},
        "pipeline": None, "result": None,
        "interpretation": {"status": "not_requested", "provider": None, "model": None, "statements": [],
                           "rejected_statement_count": 0, "generated_at": None},
        "artifacts": [], "warnings": list(warnings), "failure": None, "poll_after_ms": 2000 if video else 1000,
    }


def _recovered(attempt):
    return {"code": "JOB_RECOVERED", "severity": "info", "message": f"re-queued (attempt {attempt} of 3)."}


@pytest.fixture
def rows(session_factory, monkeypatch):
    monkeypatch.setattr(worker, "SessionLocal", session_factory)

    def add(analysis_id, *, status="processing", age_s=10_000, analysis_type="flame_image", warnings=()):
        updated = NOW - timedelta(seconds=age_s)
        with session_factory() as session:
            session.add(AnalysisRecord(
                analysis_id=analysis_id, status=status, created_at=updated, updated_at=updated,
                image_sha256="0" * 64, original_filename="x", payload=_payload(analysis_id, analysis_type, status, updated, warnings),
                artifacts={},
            ))
            session.commit()

    return add


def _get(session_factory, analysis_id):
    with session_factory() as session:
        return session.get(AnalysisRecord, analysis_id)


def test_a_crashed_image_job_is_requeued_once(rows, session_factory):
    rows("01JCRASHED0000000000000000", age_s=600)
    queue = FakeQueue()

    assert worker.recover(queue=queue, now=NOW) == {"requeued": 1, "failed": 0, "skipped": 0, "cancelled": 0}

    record = _get(session_factory, "01JCRASHED0000000000000000")
    assert record.status == "queued" and record.payload["status"] == "queued"
    assert record.payload["started_at"] is None
    assert [w["code"] for w in record.payload["warnings"]] == ["JOB_RECOVERED"]
    assert "attempt 1 of 3" in record.payload["warnings"][0]["message"]
    assert_contract_component(record.payload["warnings"][0], "Warning")
    (job, analysis_id, kwargs), = queue.jobs
    assert (job, analysis_id) == ("flame_api.worker.process_analysis", "01JCRASHED0000000000000000")
    assert kwargs["job_id"] == analysis_id and "job_timeout" not in kwargs   # RQ default, as at submission

    # Idempotent: the row is now queued with a live job, so a second run (even much later) does nothing.
    assert worker.recover(queue=queue, now=NOW + timedelta(hours=1)) == {"requeued": 0, "failed": 0, "skipped": 1, "cancelled": 0}
    assert len(queue.jobs) == 1


def test_video_jobs_use_the_video_timeout(rows, session_factory):
    timeout = worker.settings.video_job_timeout_s
    rows("01JVIDEOOLD000000000000000", analysis_type="flame_video", age_s=timeout + 120)
    rows("01JVIDEORUNNING00000000000", analysis_type="flame_video", age_s=timeout - 60)   # still within its timeout
    queue = FakeQueue()

    assert worker.recover(queue=queue, now=NOW) == {"requeued": 1, "failed": 0, "skipped": 1, "cancelled": 0}

    (job, analysis_id, kwargs), = queue.jobs
    assert (job, analysis_id) == ("flame_api.worker.process_video_analysis", "01JVIDEOOLD000000000000000")
    assert kwargs["job_timeout"] == timeout
    assert _get(session_factory, "01JVIDEORUNNING00000000000").status == "processing"


def test_fresh_processing_and_terminal_rows_are_untouched(rows, session_factory):
    rows("01JFRESH000000000000000000", age_s=30)
    rows("01JDONE0000000000000000000", status="completed", age_s=100_000)
    rows("01JFAILED00000000000000000", status="failed", age_s=100_000)
    queue = FakeQueue()

    assert worker.recover(queue=queue, now=NOW) == {"requeued": 0, "failed": 0, "skipped": 0, "cancelled": 0}
    assert queue.jobs == []
    assert _get(session_factory, "01JFRESH000000000000000000").status == "processing"


def test_older_than_overrides_the_timeout(rows, session_factory):
    rows("01JFRESH000000000000000000", age_s=30)
    queue = FakeQueue()

    assert worker.recover(older_than=10, queue=queue, now=NOW)["requeued"] == 1
    assert _get(session_factory, "01JFRESH000000000000000000").status == "queued"


def test_queued_rows_are_requeued_only_without_a_live_rq_job(rows, session_factory):
    rows("01JQUEUEDLOST0000000000000", status="queued", age_s=300)    # Redis lost the job
    rows("01JQUEUEDWAIT0000000000000", status="queued", age_s=300)    # waiting in a backlog
    rows("01JQUEUEDNEW00000000000000", status="queued", age_s=5)      # enqueue not reached yet
    queue = FakeQueue(live=["01JQUEUEDWAIT0000000000000"])

    assert worker.recover(queue=queue, now=NOW) == {"requeued": 1, "failed": 0, "skipped": 1, "cancelled": 0}
    assert [analysis_id for _, analysis_id, _ in queue.jobs] == ["01JQUEUEDLOST0000000000000"]


def test_the_attempt_cap_marks_the_analysis_failed(rows, session_factory):
    rows("01JCAPPED00000000000000000", warnings=[_recovered(1), _recovered(2), _recovered(3)])
    queue = FakeQueue()

    assert worker.recover(queue=queue, now=NOW) == {"requeued": 0, "failed": 1, "skipped": 0, "cancelled": 0}

    record = _get(session_factory, "01JCAPPED00000000000000000")
    assert record.status == "failed" and record.payload["status"] == "failed"
    assert record.payload["failure"]["code"] == "PIPELINE_ERROR"
    assert record.payload["failure"]["retryable"] is False
    assert record.payload["poll_after_ms"] is None and record.completed_at is not None
    assert queue.jobs == []
    assert worker.recover(queue=queue, now=NOW) == {"requeued": 0, "failed": 0, "skipped": 0, "cancelled": 0}


def test_two_recoverers_claim_a_row_only_once(rows, session_factory, monkeypatch):
    """The second recoverer runs between the first one's read and its conditional UPDATE."""
    rows("01JRACE0000000000000000000", status="queued", age_s=300)
    queue = FakeQueue()
    real_has_live_job = worker._has_live_job
    raced = []

    def interleave(q, analysis_id):
        if not raced:
            raced.append(None)
            raced[0] = worker.recover(queue=queue, now=NOW + timedelta(seconds=1))
            return False   # the first recoverer read the row before the other enqueued it
        return real_has_live_job(q, analysis_id)

    monkeypatch.setattr(worker, "_has_live_job", interleave)

    first = worker.recover(queue=queue, now=NOW)

    assert raced == [{"requeued": 1, "failed": 0, "skipped": 0, "cancelled": 0}]
    assert first == {"requeued": 0, "failed": 0, "skipped": 1, "cancelled": 0}
    assert len(queue.jobs) == 1
    assert len(_get(session_factory, "01JRACE0000000000000000000").payload["warnings"]) == 1


def test_a_recovered_image_analysis_completes_and_keeps_the_warning(client, session_factory, monkeypatch):
    pytest.importorskip("cv2")
    objects = {}
    monkeypatch.setattr(analysis, "put_bytes", lambda key, content, media_type: objects.__setitem__(key, content))
    monkeypatch.setattr(analysis, "Queue", lambda *args, **kwargs: FakeQueue())
    monkeypatch.setattr(analysis.Redis, "from_url", lambda *args, **kwargs: object())
    monkeypatch.setattr(worker, "get_bytes", objects.__getitem__)
    monkeypatch.setattr(worker, "put_file", lambda key, path, media_type: objects.__setitem__(key, open(path, "rb").read()))
    monkeypatch.setattr(worker, "SessionLocal", session_factory)
    stream = io.BytesIO()
    image = Image.new("RGB", (160, 120), (0, 0, 0))
    image.paste((255, 200, 120), (60, 40, 100, 80))
    image.save(stream, format="PNG")
    analysis_id = client.post("/api/analyses", files={"image": ("flame.png", stream.getvalue())}, headers=WRITE).json()["analysis"]["analysis_id"]
    with session_factory() as session:   # the worker died right after marking the row processing
        record = session.get(AnalysisRecord, analysis_id)
        record.status = "processing"
        record.updated_at = datetime.now(UTC) - timedelta(hours=1)
        record.payload = {**record.payload, "status": "processing"}
        session.commit()
    queue = FakeQueue()

    assert worker.recover(queue=queue)["requeued"] == 1
    worker.process_analysis(analysis_id)

    body = client.get(f"/api/analyses/{analysis_id}").json()["analysis"]
    assert body["status"] == "completed"
    assert "JOB_RECOVERED" in [w["code"] for w in body["warnings"]]
    assert_contract_component(body, "Analysis")


def test_the_recover_command_parses_its_options(monkeypatch, capsys):
    seen = {}
    monkeypatch.setattr(worker, "recover", lambda **kwargs: seen.update(kwargs) or {"requeued": 0, "failed": 0, "skipped": 0, "cancelled": 0})

    assert worker.main(["recover", "--older-than", "900"]) == 0
    assert seen == {"older_than": 900}
    assert '"requeued": 0' in capsys.readouterr().out
    with pytest.raises(SystemExit):
        worker.main(["recover", "--older-than", "-1"])
