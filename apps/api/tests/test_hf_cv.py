import base64
import io
import json
import sys
from pathlib import Path

import pytest
from pydantic import SecretStr

from flame_api.config import Settings
from flame_api.hf_cv import HfCvError, analyze_image_on_hf


PNG = b"\x89PNG\r\n\x1a\nsmall test image"


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size=-1):
        return self.body[:size]


def hf_settings(**overrides):
    return Settings(
        api_auth_enabled=False,
        cv_provider="hf_space",
        cv_hf_space_url="https://flame-cv.hf.space",
        cv_hf_token=SecretStr("hf_read_token"),
        **overrides,
    )


def valid_reply():
    return {
        "analysis": {
            "preprocessing": {},
            "segmentation": {},
            "provenance": {},
        },
        "artifacts": {"preprocessed": base64.b64encode(PNG).decode("ascii")},
    }


def test_hf_cv_uploads_image_and_calibration(monkeypatch):
    sent = {}

    def fake_urlopen(request, timeout):
        sent["request"] = request
        sent["body"] = request.data
        sent["timeout"] = timeout
        return FakeResponse(json.dumps(valid_reply()).encode())

    monkeypatch.setattr("ai.providers.cloud.hf_space_cv.urlopen", fake_urlopen)

    analysis, artifacts = analyze_image_on_hf(
        hf_settings(),
        b"image bytes",
        media_type="image/png",
        mm_per_pixel=0.5,
    )

    assert analysis["preprocessing"] == {}
    assert artifacts == {"preprocessed": PNG}
    assert sent["request"].full_url == "https://flame-cv.hf.space/api/analyze"
    assert sent["request"].get_header("Authorization") == "Bearer hf_read_token"
    assert sent["timeout"] == 300.0
    assert b'name="mm_per_pixel"\r\n\r\n0.5' in sent["body"]
    assert b'name="image"; filename="input.png"' in sent["body"]
    assert b"image bytes" in sent["body"]


def test_hf_cv_rejects_invalid_artifact_and_unsupported_media(monkeypatch):
    malformed = valid_reply()
    malformed["artifacts"]["preprocessed"] = "not base64!"
    monkeypatch.setattr(
        "ai.providers.cloud.hf_space_cv.urlopen",
        lambda *_args, **_kwargs: FakeResponse(json.dumps(malformed).encode()),
    )

    with pytest.raises(HfCvError, match="invalid artifact data"):
        analyze_image_on_hf(
            hf_settings(),
            b"image bytes",
            media_type="image/jpeg",
            mm_per_pixel=None,
        )

    with pytest.raises(HfCvError, match="JPEG and PNG"):
        analyze_image_on_hf(
            hf_settings(),
            b"image bytes",
            media_type="image/gif",
            mm_per_pixel=None,
        )


def test_hf_space_endpoint_returns_analysis_and_artifacts(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from PIL import Image

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from cv.hf_space.app import app

    image = io.BytesIO()
    Image.new("RGB", (64, 64), (255, 90, 15)).save(image, format="PNG")
    response = TestClient(app).post(
        "/api/analyze",
        files={"image": ("flame.png", image.getvalue(), "image/png")},
        data={"mm_per_pixel": "0.5"},
    )

    assert response.status_code == 200
    body = response.json()
    from cv.flame_cv import PIPELINE_VERSION

    assert body["analysis"]["pipelineVersion"] == PIPELINE_VERSION
    assert body["analysis"]["provenance"]["inputUri"] == "uploaded-image"
    assert body["analysis"]["preprocessing"]["derivedUri"] is None
    assert base64.b64decode(body["artifacts"]["preprocessed"]).startswith(b"\x89PNG")

    monkeypatch.setattr(
        "ai.providers.cloud.hf_space_cv.urlopen",
        lambda *_args, **_kwargs: FakeResponse(response.content),
    )
    legacy, artifacts = analyze_image_on_hf(
        hf_settings(),
        image.getvalue(),
        media_type="image/png",
        mm_per_pixel=0.5,
    )
    source_path = tmp_path / "source.png"
    source_path.write_bytes(image.getvalue())
    legacy["provenance"]["inputUri"] = str(source_path)
    for name, content in artifacts.items():
        artifact_path = tmp_path / f"{name}.png"
        artifact_path.write_bytes(content)
        if name == "preprocessed":
            legacy["preprocessing"]["derivedUri"] = str(artifact_path)
        elif name == "mask":
            legacy["segmentation"]["maskUri"] = str(artifact_path)
        elif name == "overlay":
            legacy["segmentation"]["overlayArtifactUri"] = str(artifact_path)

    from flame_api.worker import _adapt_result
    from api_contract import assert_contract_component

    adapted = _adapt_result(
        legacy,
        {
            "width": 64,
            "height": 64,
            "calibration": {
                "state": "present",
                "scale_px_per_mm": 2.0,
                "scale_source": "test",
            },
        },
        tmp_path,
    )
    assert adapted["result"]["detection"]["status"] == "present"
    assert_contract_component(adapted["result"], "FlameAnalysisResult")
