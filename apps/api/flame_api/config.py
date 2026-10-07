from functools import lru_cache
from hmac import compare_digest
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FLAME_", env_file=".env", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value.removeprefix("postgresql://")
        return value

    environment: str = "development"
    api_version: str = "0.1.0"
    build_id: str | None = None
    git_sha: str | None = None
    database_url: str = "postgresql+psycopg://flame:flame@localhost:5432/flame"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_access_key: str = "flame-local"
    s3_secret_key: SecretStr = SecretStr("change-me-local-only")
    s3_bucket: str = "flame-artifacts"
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    max_image_pixels: int = Field(default=50_000_000, gt=0)
    api_auth_enabled: bool = True
    read_api_token: SecretStr | None = None
    write_api_token: SecretStr | None = None
    aura_enabled: bool = False
    aura_base_url: str = "https://aura-ai-production-03a4.up.railway.app"
    aura_service_token: SecretStr | None = None
    aura_timeout_s: float = Field(default=120.0, gt=0, le=120)
    llm_enabled: bool = False

    @model_validator(mode="after")
    def require_distinct_api_tokens(self):
        if self.api_auth_enabled:
            if self.read_api_token is None or self.write_api_token is None:
                raise ValueError("FLAME_READ_API_TOKEN and FLAME_WRITE_API_TOKEN are required when API authentication is enabled.")
            read_token = self.read_api_token.get_secret_value()
            write_token = self.write_api_token.get_secret_value()
            if len(read_token) < 32 or len(write_token) < 32:
                raise ValueError("Flame API tokens must contain at least 32 characters.")
            if compare_digest(read_token.encode(), write_token.encode()):
                raise ValueError("FLAME_READ_API_TOKEN and FLAME_WRITE_API_TOKEN must be different.")

        aura_url = urlsplit(self.aura_base_url)
        if (
            aura_url.scheme != "https"
            or not aura_url.netloc
            or aura_url.path not in {"", "/"}
            or aura_url.username is not None
            or aura_url.password is not None
            or aura_url.query
            or aura_url.fragment
        ):
            raise ValueError("FLAME_AURA_BASE_URL must be an HTTPS origin without embedded credentials.")
        if self.aura_enabled and self.aura_service_token is None:
            raise ValueError("FLAME_AURA_SERVICE_TOKEN is required when AURA interpretation is enabled.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
