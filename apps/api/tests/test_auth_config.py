import pytest
from pydantic import SecretStr, ValidationError

from flame_api.config import Settings


def test_enabled_auth_requires_distinct_long_tokens(monkeypatch):
    monkeypatch.delenv("FLAME_READ_API_TOKEN")
    monkeypatch.delenv("FLAME_WRITE_API_TOKEN")
    token = SecretStr("a" * 40)
    with pytest.raises(ValidationError):
        Settings(api_auth_enabled=True, read_api_token=token, write_api_token=token)

    with pytest.raises(ValidationError):
        Settings(api_auth_enabled=True, read_api_token="short", write_api_token="another-short")

    with pytest.raises(ValidationError):
        Settings(api_auth_enabled=True, read_api_token="short")


def test_legacy_tokens_are_optional_once_client_keys_exist(monkeypatch):
    """P2-1: a deployment may run on client keys alone; either deprecated token may be left unset."""
    monkeypatch.delenv("FLAME_READ_API_TOKEN")
    monkeypatch.delenv("FLAME_WRITE_API_TOKEN")

    assert Settings(api_auth_enabled=True).read_api_token is None
    assert Settings(api_auth_enabled=True, read_api_token="r" * 40).write_api_token is None


def test_auth_can_be_disabled_for_non_http_worker():
    settings = Settings(api_auth_enabled=False)

    assert settings.api_auth_enabled is False


def test_railway_postgres_url_uses_installed_psycopg_driver():
    settings = Settings(
        api_auth_enabled=False,
        database_url="postgresql://user:pass@db.internal:5432/flame",
    )

    assert settings.database_url == "postgresql+psycopg://user:pass@db.internal:5432/flame"


def test_aura_base_url_requires_https():
    with pytest.raises(ValidationError):
        Settings(api_auth_enabled=False, aura_base_url="http://aura.example")


def test_hf_cv_provider_requires_secure_space_origin():
    with pytest.raises(ValidationError):
        Settings(api_auth_enabled=False, cv_provider="hf_space")
    with pytest.raises(ValidationError):
        Settings(api_auth_enabled=False, cv_hf_space_url="http://cv.example")
    with pytest.raises(ValidationError):
        Settings(api_auth_enabled=False, cv_hf_space_url="https://user:pass@cv.example")

    settings = Settings(
        api_auth_enabled=False,
        cv_provider="hf_space",
        cv_hf_space_url="https://flame-cv.hf.space",
    )

    assert settings.cv_provider == "hf_space"
    assert settings.cv_hf_space_url == "https://flame-cv.hf.space"

    local_settings = Settings(
        api_auth_enabled=False,
        cv_hf_space_url="",
        cv_hf_token="",
    )
    assert local_settings.cv_hf_space_url is None
    assert local_settings.cv_hf_token is None


PRODUCTION_SAFE = {
    "api_auth_enabled": False,
    "environment": "production",
    "database_url": "postgresql+psycopg://flame:a-real-password-0123@db.internal:5432/flame",
    "s3_access_key": "prod-access-key",
    "s3_secret_key": "prod-secret-0123456789abcdef",
}


def test_production_accepts_real_secrets():
    settings = Settings(**PRODUCTION_SAFE)

    assert settings.environment == "production"


@pytest.mark.parametrize(
    ("field", "value", "setting"),
    [
        ("s3_secret_key", "change-me-local-only", "FLAME_S3_SECRET_KEY"),
        ("s3_secret_key", "flame-local-only-change-me", "FLAME_S3_SECRET_KEY"),
        ("s3_secret_key", "change-me-later-0123456789", "FLAME_S3_SECRET_KEY"),
        ("s3_access_key", "flame-local", "FLAME_S3_ACCESS_KEY"),
        ("database_url", "postgresql+psycopg://flame:flame@localhost:5432/flame", "FLAME_DATABASE_URL"),
        ("database_url", "postgresql://flame:flame-local-only@postgres:5432/flame", "FLAME_DATABASE_URL"),
    ],
)
def test_production_refuses_local_defaults_without_echoing_them(field, value, setting):
    """P2-6: the error names the setting and never contains the value."""
    with pytest.raises(ValidationError) as raised:
        Settings(**{**PRODUCTION_SAFE, field: value})

    message = str(raised.value)
    assert setting in message
    assert value not in message
    assert "input_value" not in message


def test_production_refuses_the_built_in_defaults():
    with pytest.raises(ValidationError, match="FLAME_S3_SECRET_KEY"):
        Settings(api_auth_enabled=False, environment="Production")


def test_local_defaults_are_fine_outside_production():
    settings = Settings(api_auth_enabled=False, environment="development")

    assert settings.s3_access_key == "flame-local"
