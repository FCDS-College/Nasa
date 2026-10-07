import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from flame_api import main


def test_health_contract_shape_and_request_id_echo(monkeypatch):
    monkeypatch.setattr(main.engine, "connect", lambda: _database_unavailable())
    monkeypatch.setattr(main.boto3, "client", lambda **_: _object_storage_unavailable())
    monkeypatch.setattr(main.Redis, "from_url", lambda *args, **kwargs: _cache_unavailable())

    response = TestClient(main.app).get(
        "/api/health",
        headers={
            "Authorization": f"Bearer {os.environ['FLAME_READ_API_TOKEN']}",
            "X-Request-ID": "health-test_1",
        },
    )
    body = response.json()

    assert response.headers["X-Request-ID"] == "health-test_1"
    assert body["meta"]["request_id"] == "health-test_1"
    assert body["meta"]["api_version"] == "0.1.0"
    assert set(body["services"]) == {
        "api", "database", "vector_index", "object_storage", "cache", "cv_model", "llm", "aura"
    }
    assert body["services"]["aura"]["status"] == "disabled"
    assert response.status_code in {200, 503}
    assert body["status"] in {"healthy", "degraded", "unhealthy"}


@pytest.mark.parametrize("aura_status", ["up", "down"])
def test_health_reports_aura_readiness_when_enabled(monkeypatch, aura_status):
    from pydantic import SecretStr

    from flame_api.config import Settings

    monkeypatch.setattr(main.engine, "connect", lambda: _database_unavailable())
    monkeypatch.setattr(main.boto3, "client", lambda **_: _object_storage_unavailable())
    monkeypatch.setattr(main.Redis, "from_url", lambda *args, **kwargs: _cache_unavailable())
    monkeypatch.setattr(main, "check_aura_ready", lambda *_: (aura_status, 12.0))
    monkeypatch.setattr(
        main,
        "settings",
        Settings(
            api_auth_enabled=False,
            aura_enabled=True,
            aura_service_token=SecretStr("fake-service-token"),
        ),
    )

    response = TestClient(main.app).get("/api/health")

    assert response.status_code == 503
    assert response.json()["services"]["aura"]["status"] == aura_status
    assert response.json()["services"]["aura"]["latency_ms"] == 12.0


def _database_unavailable():
    raise SQLAlchemyError("offline")


def _object_storage_unavailable():
    raise RuntimeError("offline")


def _cache_unavailable():
    raise RuntimeError("offline")