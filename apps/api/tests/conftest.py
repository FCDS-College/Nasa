import os

os.environ["FLAME_API_AUTH_ENABLED"] = "true"
os.environ["FLAME_READ_API_TOKEN"] = "test-read-token-0123456789abcdef0123456789"
os.environ["FLAME_WRITE_API_TOKEN"] = "test-write-token-0123456789abcdef0123456789"
os.environ["FLAME_AURA_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from jsonschema.validators import RefResolver
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from flame_api.database import get_session
from flame_api.main import app
from flame_api.models import Base

CONTRACT_PATH = __import__("pathlib").Path(__file__).resolve().parents[3] / "docs" / "api" / "openapi.json"


def assert_contract_component(instance, component_name):
    import json

    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(
        contract["components"]["schemas"][component_name],
        resolver=RefResolver.from_schema(contract),
    )
    errors = list(validator.iter_errors(instance))
    assert not errors, "\n".join(f"{list(error.absolute_path)}: {error.message}" for error in errors)


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