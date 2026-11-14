import io
import json
import os

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
    from api_contract import assert_contract_component

    mock_queue_and_storage(monkeypatch)
    payload = png_bytes()
    headers = {
        "Authorization": f"Bearer {os.environ['FLAME_WRITE_API_TOKEN']}",
        "Idempotency-Key": "request-key-0001",
    }

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
    headers = {"Authorization": f"Bearer {os.environ['FLAME_WRITE_API_TOKEN']}"}

    unsupported = client.post("/api/analyses", files={"image": ("file.bmp", bmp_bytes(), "image/bmp")}, headers=headers)
    invalid = client.post("/api/analyses", files={"image": ("file.png", b"not-a-png", "image/png")}, headers=headers)

    assert unsupported.status_code == 415
    assert unsupported.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "IMAGE_INVALID"


def test_history_detail_and_original_artifact(client, monkeypatch):
    from api_contract import assert_contract_component

    mock_queue_and_storage(monkeypatch)
    created = client.post(
        "/api/analyses",
        files={"image": ("flame.png", png_bytes(), "image/png")},
        headers={"Authorization": f"Bearer {os.environ['FLAME_WRITE_API_TOKEN']}"},
    )
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


def test_read_token_cannot_upload_and_write_token_is_required(client):
    import os

    read_token_header = f"Bearer {os.environ['FLAME_READ_API_TOKEN']}"
    write_token_header = f"Bearer {os.environ['FLAME_WRITE_API_TOKEN']}"
    read_access = client.get("/api/search", params={"q": "combustion"}, headers={"Authorization": read_token_header})
    missing_read_token = client.get("/api/search", params={"q": "combustion"}, headers={"Authorization": ""})
    write_cannot_read = client.get("/api/search", params={"q": "combustion"}, headers={"Authorization": write_token_header})
    without_token = client.post("/api/analyses", headers={"Authorization": ""})
    read_token_upload = client.post(
        "/api/analyses",
        headers={"Authorization": read_token_header},
    )
    write_token_upload = client.post(
        "/api/analyses",
        headers={"Authorization": write_token_header},
    )

    assert read_access.status_code == 200
    assert missing_read_token.status_code == 401
    assert write_cannot_read.status_code == 401
    assert without_token.status_code == 401
    assert read_token_upload.status_code == 401
    assert without_token.headers["WWW-Authenticate"] == "Bearer"
    assert write_token_upload.status_code == 400
    assert without_token.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

def test_camera_profile_is_validated_stored_and_echoed(client, monkeypatch):
    from api_contract import assert_contract_component

    mock_queue_and_storage(monkeypatch)
    headers = {"Authorization": f"Bearer {os.environ['FLAME_WRITE_API_TOKEN']}"}
    files = {"image": ("flame.png", png_bytes(), "application/octet-stream")}

    created = client.post("/api/analyses", files=files, data={"camera_profile": "flex-colour"}, headers=headers)
    assert created.status_code == 202
    assert created.json()["analysis"]["input"]["camera_profile"] == "flex-colour"
    assert_contract_component(created.json(), "AnalysisResponse")

    plain = client.post("/api/analyses", files={"image": ("f2.png", png_bytes((90, 70)), "application/octet-stream")},
                        headers=headers)
    assert plain.status_code == 202 and plain.json()["analysis"]["input"]["camera_profile"] is None

    unknown = client.post("/api/analyses", files=files, data={"camera_profile": "no-such-camera"}, headers=headers)
    assert unknown.status_code == 400
    assert unknown.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "flex-colour" in json.dumps(unknown.json())
