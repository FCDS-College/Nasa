import io

from PIL import Image

from flame_api import analysis


class FakeQueue:
    jobs = []

    def __init__(self, *args, **kwargs):
        pass

    def enqueue(self, *args, **kwargs):
        self.jobs.append((args, kwargs))


def png_bytes(size=(80, 72)):
    stream = io.BytesIO()
    Image.new("RGB", size, (240, 190, 90)).save(stream, format="PNG")
    return stream.getvalue()


def bmp_bytes():
    stream = io.BytesIO()
    Image.new("RGB", (80, 72), (20, 40, 60)).save(stream, format="BMP")
    return stream.getvalue()


def mock_queue_and_storage(monkeypatch):
    FakeQueue.jobs.clear()
    monkeypatch.setattr(analysis, "put_bytes", lambda *args, **kwargs: None)
    monkeypatch.setattr(analysis, "Queue", FakeQueue)
    monkeypatch.setattr(analysis.Redis, "from_url", lambda *args, **kwargs: object())


def test_upload_returns_queued_analysis_and_is_idempotent(client, monkeypatch):
    from conftest import assert_contract_component

    mock_queue_and_storage(monkeypatch)
    payload = png_bytes()
    headers = {"Idempotency-Key": "request-key-0001"}

    first = client.post("/api/analyses", files={"image": ("flame.png", payload, "application/octet-stream")}, headers=headers)
    second = client.post("/api/analyses", files={"image": ("flame.png", payload, "application/octet-stream")}, headers=headers)

    assert first.status_code == 202
    assert first.json()["analysis"]["status"] == "queued"
    assert first.json()["analysis"]["input"]["media_type"] == "image/png"
    assert first.json()["analysis"]["input"]["width"] == 80
    assert first.headers["Location"] == f"/api/analyses/{first.json()['analysis']['analysis_id']}"
    assert first.headers["Retry-After"] == "1"
    assert_contract_component(first.json(), "AnalysisResponse")
    assert second.status_code == 202
    assert second.json()["analysis"]["analysis_id"] == first.json()["analysis"]["analysis_id"]
    assert len(FakeQueue.jobs) == 1


def test_upload_rejects_unsupported_and_undecodable_content(client, monkeypatch):
    mock_queue_and_storage(monkeypatch)

    unsupported = client.post("/api/analyses", files={"image": ("file.bmp", bmp_bytes(), "image/bmp")})
    invalid = client.post("/api/analyses", files={"image": ("file.png", b"not-a-png", "image/png")})

    assert unsupported.status_code == 415
    assert unsupported.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "IMAGE_INVALID"


def test_history_detail_and_original_artifact(client, monkeypatch):
    from conftest import assert_contract_component

    mock_queue_and_storage(monkeypatch)
    created = client.post("/api/analyses", files={"image": ("flame.png", png_bytes(), "image/png")})
    analysis_id = created.json()["analysis"]["analysis_id"]
    monkeypatch.setattr(
        analysis,
        "storage_client",
        lambda: type("Storage", (), {"get_object": lambda self, **kwargs: {"Body": io.BytesIO(b"original-bytes")}})(),
    )

    history = client.get("/api/analyses")
    detail = client.get(f"/api/analyses/{analysis_id}")
    original = client.get(f"/api/analyses/{analysis_id}/artifacts/original")

    assert history.status_code == 200
    assert history.json()["items"][0]["analysis_id"] == analysis_id
    assert_contract_component(history.json(), "AnalysisListResponse")
    assert detail.json()["analysis"]["status"] == "queued"
    assert original.status_code == 200
    assert original.content == b"original-bytes"
    assert original.headers["cache-control"].endswith("immutable")