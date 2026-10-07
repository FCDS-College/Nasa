from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FLAME_", env_file=".env", extra="ignore")

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
    aura_enabled: bool = False
    llm_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
