import json
from urllib.error import HTTPError

import pytest
from pydantic import SecretStr

from flame_api import aura_integration
from flame_api.config import Settings


AURA_TOKEN = "svc-flame-secret-that-is-not-a-real-credential"
ANALYSIS_ID = "01J9Z3Q9D3F5H7K9N1R3T5W7Y9"
EVIDENCE_ID = "01J9Z3N5B8C1E3G5J7M9P1R3T5"


class FakeResponse:
    status = 200

    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size=-1):
        return self.body[:size]


def aura_settings():
    return Settings(
        api_auth_enabled=False,
        aura_enabled=True,
        aura_base_url="https://aura-ai-production-03a4.up.railway.app",
        aura_service_token=SecretStr(AURA_TOKEN),
    )


def test_interpretation_uses_data_channel_and_filters_untrusted_claims(monkeypatch):
    sent = {}

    def fake_urlopen(request, timeout):
        sent["request"] = request
        sent["timeout"] = timeout
        return FakeResponse(
            {
                "data": {
                    "statements": [
                        {
                            "text": "The observed image may be consistent with a stable flame.",
                            "claim_class": "inferred",
                            "evidence_ids": [EVIDENCE_ID],
                        },
                        {
                            "text": "The temperature was high.",
                            "claim_class": "hypothesized",
                            "evidence_ids": [],
                        },
                        {
                            "text": "The test may have ended in extinction.",
                            "claim_class": "inferred",
                            "evidence_ids": [EVIDENCE_ID],
                        },
                        {
                            "text": "No further conclusion is supported.",
                            "claim_class": "unsupported",
                            "evidence_ids": [],
                        },
                    ]
                },
                "model": "local-test-model",
            }
        )

    monkeypatch.setattr(aura_integration, "urlopen", fake_urlopen)
    measured_context = [
        {
            "id": EVIDENCE_ID,
            "source": "flame/image_measurement",
            "text": '{"area_px":12}',
        }
    ]

    result = aura_integration.interpret_analysis(
        aura_settings(),
        analysis_id=ANALYSIS_ID,
        context=measured_context,
        allowed_evidence_ids={EVIDENCE_ID},
    )

    request_body = json.loads(sent["request"].data)
    assert sent["request"].full_url.endswith("/api/v3/chat")
    assert sent["request"].get_header("Authorization") == f"Bearer {AURA_TOKEN}"
    assert sent["request"].get_header("X-correlation-id") == ANALYSIS_ID
    assert sent["request"].get_header("Idempotency-key") == ANALYSIS_ID
    assert sent["timeout"] == 120
    assert request_body["plan"] is False
    assert request_body["use_tools"] is False
    assert request_body["use_memory"] is False
    assert request_body["use_knowledge"] is False
    assert request_body["require_local"] is True
    assert request_body["context"] == measured_context
    assert "NASA" not in request_body["message"]
    assert len(result["statements"]) == 2
    assert result["rejected_statement_count"] == 2
    assert result["model"] == "local-test-model"


@pytest.mark.parametrize("status_code", [429, 503])
def test_interpretation_http_errors_are_isolated(monkeypatch, status_code):
    def unavailable(*_, **__):
        raise HTTPError(
            "https://aura.example/api/v3/chat",
            status_code,
            "unavailable",
            {},
            None,
        )

    monkeypatch.setattr(aura_integration, "urlopen", unavailable)

    with pytest.raises(aura_integration.AuraIntegrationError) as error:
        aura_integration.interpret_analysis(
            aura_settings(),
            analysis_id=ANALYSIS_ID,
            context=[],
            allowed_evidence_ids=set(),
        )

    assert error.value.status_code == status_code
    assert AURA_TOKEN not in str(error.value)


def test_interpretation_rejects_malformed_structured_output(monkeypatch):
    monkeypatch.setattr(
        aura_integration,
        "urlopen",
        lambda *_, **__: FakeResponse({"data": {"statements": "not-an-array"}}),
    )

    with pytest.raises(aura_integration.AuraIntegrationError):
        aura_integration.interpret_analysis(
            aura_settings(),
            analysis_id=ANALYSIS_ID,
            context=[],
            allowed_evidence_ids=set(),
        )


@pytest.mark.parametrize("failure", [TimeoutError(), OSError("network unavailable")])
def test_interpretation_transport_failures_are_isolated(monkeypatch, failure):
    def unavailable(*_, **__):
        raise failure

    monkeypatch.setattr(aura_integration, "urlopen", unavailable)

    with pytest.raises(aura_integration.AuraIntegrationError):
        aura_integration.interpret_analysis(
            aura_settings(),
            analysis_id=ANALYSIS_ID,
            context=[],
            allowed_evidence_ids=set(),
        )


def test_aura_readiness_reports_non_success_as_down(monkeypatch):
    def unavailable(*_, **__):
        raise HTTPError("https://aura.example/health/ready", 503, "not ready", {}, None)

    monkeypatch.setattr(aura_integration, "urlopen", unavailable)

    status, latency = aura_integration.check_aura_ready(aura_settings())

    assert status == "down"
    assert latency >= 0


def test_image_measurement_becomes_citable_evidence(
    client, session_factory
):
    from datetime import UTC, datetime

    from conftest import assert_contract_component
    from flame_api.models import AnalysisRecord
    from flame_api.worker import _aura_request_context, _image_measurement_evidence

    analysis = AnalysisRecord(
        analysis_id=ANALYSIS_ID,
        status="completed",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        experiment_id=None,
        image_sha256="a" * 64,
        original_filename="flame.png",
        payload={},
        artifacts={},
    )
    pipeline = {"pipeline_version": "cv-test-v1"}
    result = {
        "pipeline": pipeline,
        "result": {"measurements": {"geometry_px": {"area": {"value": 12}}}},
    }

    with session_factory() as session:
        evidence = _image_measurement_evidence(
            session,
            analysis,
            result,
            {"frame_index": None},
            datetime.now(UTC),
        )
        evidence_id = evidence.evidence_id
        analysis.payload = {
            "pipeline": pipeline,
            "result": {
                "detection": {"status": "present"},
                "measurements": {
                    "geometry_px": {
                        "area": {
                            "value": 12,
                            "unit": "px2",
                            "classification": "measured",
                            "method": "mask_pixel_count",
                        }
                    },
                    "geometry_physical": None,
                    "appearance": {},
                },
                "quality_flags": {"calibration_absent": True},
                "segmentation": {"contours": [[{"x": 1, "y": 2}] * 4000]},
            },
        }
        context = _aura_request_context(session, analysis, evidence)
        assert len(context["context"][0]["text"]) <= 2000
        assert "contours" not in context["context"][0]["text"]
        assert evidence_id in context["evidence_ids"]
        session.add(evidence)
        session.commit()

    response = client.get(f"/api/evidence/{evidence_id}")

    assert response.status_code == 200
    assert_contract_component(response.json(), "EvidenceResponse")
    assert response.json()["evidence"]["kind"] == "image_measurement"
    assert response.json()["evidence"]["origin"] == "calculated_measurement"
    assert response.json()["evidence"]["analysis_id"] == ANALYSIS_ID


def test_aura_outage_keeps_completed_analysis_completed(monkeypatch, session_factory):
    from datetime import UTC, datetime

    from flame_api import worker
    from flame_api.models import AnalysisRecord

    now = datetime.now(UTC)
    record = AnalysisRecord(
        analysis_id=ANALYSIS_ID,
        status="completed",
        created_at=now,
        updated_at=now,
        completed_at=now,
        experiment_id=None,
        image_sha256="b" * 64,
        original_filename="flame.png",
        payload={
            "status": "completed",
            "warnings": [],
            "interpretation": {
                "status": "pending",
                "provider": "aura",
                "model": None,
                "statements": [],
                "rejected_statement_count": 0,
                "generated_at": None,
            },
        },
        artifacts={},
    )
    with session_factory() as session:
        session.add(record)
        session.commit()

    def unavailable(*_, **__):
        raise aura_integration.AuraIntegrationError("AURA unavailable.", status_code=503)

    monkeypatch.setattr(worker, "SessionLocal", session_factory)
    monkeypatch.setattr(worker, "interpret_analysis", unavailable)

    worker._run_aura_interpretation(
        ANALYSIS_ID,
        context=[],
        evidence_ids=set(),
    )

    with session_factory() as session:
        stored = session.get(AnalysisRecord, ANALYSIS_ID)
        assert stored.status == "completed"
        assert stored.payload["interpretation"]["status"] == "unavailable"
        assert stored.payload["warnings"][0]["code"] == "INTERPRETATION_UNAVAILABLE"
