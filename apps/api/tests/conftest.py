import os

os.environ["FLAME_API_AUTH_ENABLED"] = "true"
os.environ["FLAME_READ_API_TOKEN"] = "test-read-token-0123456789abcdef0123456789"
os.environ["FLAME_WRITE_API_TOKEN"] = "test-write-token-0123456789abcdef0123456789"
os.environ["FLAME_AURA_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from flame_api.database import get_session
from flame_api.main import app
from flame_api.models import Base

from api_contract import CONTRACT_PATH, assert_contract_component  # noqa: F401  (re-export)


@pytest.fixture(autouse=True)
def fresh_ai_runtime(monkeypatch):
    """Router, circuit state and any runtime mode override are per test.

    The persisted mode is read through the real FLAME_DATABASE_URL, not the test's SQLite session, so a
    developer's running Postgres (with an `ai.mode.changed` audit row) would otherwise leak into tests.
    """
    from flame_api import ai_runtime, answer_cache

    monkeypatch.setattr(ai_runtime, "_latest_audited_mode", lambda: None)
    ai_runtime.reset()
    answer_cache.reset()
    yield
    ai_runtime.reset()
    answer_cache.reset()


@pytest.fixture(autouse=True)
def fresh_rate_limits():
    """Rate-limit buckets live in an in-process fake, never in a real Redis, and are per test."""
    from flame_api import clients, main, rate_limit

    rate_limit.set_backend(rate_limit.MemoryBackend())
    clients.reset()
    main._chat_calls.clear()
    yield
    rate_limit.set_backend(None)
    clients.reset()
    main._chat_calls.clear()


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield sessions
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(session_factory):

    def override_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {os.environ['FLAME_READ_API_TOKEN']}"
        yield test_client
    app.dependency_overrides.clear()