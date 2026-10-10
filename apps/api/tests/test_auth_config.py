import pytest
from pydantic import SecretStr, ValidationError

from flame_api.config import Settings


def test_enabled_auth_requires_distinct_long_tokens(monkeypatch):
    monkeypatch.delenv("FLAME_READ_API_TOKEN")
    monkeypatch.delenv("FLAME_WRITE_API_TOKEN")
    with pytest.raises(ValidationError):
        Settings(api_auth_enabled=True)

    token = SecretStr("a" * 40)
    with pytest.raises(ValidationError):
        Settings(api_auth_enabled=True, read_api_token=token, write_api_token=token)

    with pytest.raises(ValidationError):
        Settings(api_auth_enabled=True, read_api_token="short", write_api_token="another-short")


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
