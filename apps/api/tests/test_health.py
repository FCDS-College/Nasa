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

_AUTH = {"Authorization": f"Bearer {os.environ['FLAME_READ_API_TOKEN']}"}


class _FakeWorkerRedis:
    def ping(self):
        return True


def _stub_services(monkeypatch):
    monkeypatch.setattr(main.engine, "connect", lambda: _database_unavailable())
    monkeypatch.setattr(main.boto3, "client", lambda **_: _object_storage_unavailable())


@pytest.mark.parametrize("workers,expected", [([object()], "up"), ([], "down")])
def test_health_reports_cv_worker_from_rq_registry(monkeypatch, workers, expected):
    _stub_services(monkeypatch)
    monkeypatch.setattr(main.Redis, "from_url", lambda *a, **k: _FakeWorkerRedis())
    monkeypatch.setattr(main.Worker, "all", staticmethod(lambda queue=None: workers))
    monkeypatch.setattr(main.Queue, "count", property(lambda self: 0))

    body = TestClient(main.app).get("/api/health", headers=_AUTH).json()

    assert body["services"]["cv_model"]["status"] == expected
    if expected == "up":
        assert body["services"]["cv_model"]["version"]
    else:
        assert "No CV worker" in body["services"]["cv_model"]["message"]


def test_health_cv_worker_unknown_when_registry_unreadable(monkeypatch):
    _stub_services(monkeypatch)
    monkeypatch.setattr(main.Redis, "from_url", lambda *a, **k: _FakeWorkerRedis())

    def boom(queue=None):
        raise RuntimeError("registry offline")

    monkeypatch.setattr(main.Worker, "all", staticmethod(boom))
    body = TestClient(main.app).get("/api/health", headers=_AUTH).json()
    assert body["services"]["cv_model"]["status"] == "unknown"
