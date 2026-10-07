from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from flame_api import main


def test_health_contract_shape_and_request_id_echo(monkeypatch):
    monkeypatch.setattr(main.engine, "connect", lambda: _database_unavailable())
    monkeypatch.setattr(main.boto3, "client", lambda **_: _object_storage_unavailable())
    monkeypatch.setattr(main.Redis, "from_url", lambda *args, **kwargs: _cache_unavailable())

    response = TestClient(main.app).get("/api/health", headers={"X-Request-ID": "health-test_1"})
    body = response.json()

    assert response.headers["X-Request-ID"] == "health-test_1"
    assert body["meta"]["request_id"] == "health-test_1"
    assert body["meta"]["api_version"] == "0.1.0"
    assert set(body["services"]) == {
        "api", "database", "vector_index", "object_storage", "cache", "cv_model", "llm", "aura"
    }
    assert response.status_code in {200, 503}
    assert body["status"] in {"healthy", "degraded", "unhealthy"}


def _database_unavailable():
    raise SQLAlchemyError("offline")


def _object_storage_unavailable():
    raise RuntimeError("offline")


def _cache_unavailable():
    raise RuntimeError("offline")