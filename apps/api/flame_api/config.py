from functools import lru_cache
from hmac import compare_digest
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator

from flame_api.contracts import API_VERSION
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # hide_input_in_errors: a validation error would otherwise echo the raw settings (secrets
    # included) into the start-up log.
    model_config = SettingsConfigDict(env_prefix="FLAME_", env_file=".env", extra="ignore", hide_input_in_errors=True)

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value.removeprefix("postgresql://")
        return value

    @field_validator(
        "cv_hf_space_url", "cv_hf_token", "ollama_base_url", "vllm_base_url", "vllm_api_key",
        "llamacpp_base_url", "embedding_cache_dir", mode="before",
    )
    @classmethod
    def normalize_empty_cv_settings(
        cls, value: str | SecretStr | None
    ) -> str | SecretStr | None:
        return None if value == "" else value

    environment: str = "development"
    api_version: str = API_VERSION   # the contract version (docs/api/openapi.json info.version)
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
    # Video analyses (analysis_type flame_video, ADR-005). The CV pipeline itself caps 500 MiB / 600 s.
    max_video_upload_bytes: int = Field(default=200 * 1024 * 1024, gt=0, le=500 * 1024 * 1024)
    max_video_frames: int = Field(default=600, ge=1, le=5000)
    video_job_timeout_s: int = Field(default=3600, ge=60, le=6 * 3600)
    # ADR-008: a video job stores its measured frames in PostgreSQL every this many sampled frames, and
    # checks for a cancel request at the same points. At most this many frames are re-done after a crash.
    video_checkpoint_every_frames: int = Field(default=10, ge=1, le=1000)
    api_auth_enabled: bool = True
    # Deprecated (P2-1): per-client keys from `python -m flame_api.clients` replace these. Each is
    # optional and keeps working as before while set (identity `legacy-read` / `legacy-write`).
    read_api_token: SecretStr | None = None
    write_api_token: SecretStr | None = None
    aura_enabled: bool = False
    aura_base_url: str = "https://aura-ai-production-03a4.up.railway.app"
    aura_service_token: SecretStr | None = None
    aura_timeout_s: float = Field(default=120.0, gt=0, le=120)
    # True refuses any AURA provider that is not on AURA's own host. A deployment whose only model
    # is a self-hosted GPU Space (a remote provider to AURA) must set this to false, or every
    # AURA call fails with 503 all_providers_failed.
    aura_require_local: bool = True
    # Per client identity, in Redis (FLAME_REDIS_URL). Chat stays the strictest: every call can reach
    # a model. If Redis is down, requests are let through and chat falls back to an in-process limit.
    rate_limit_enabled: bool = True
    read_rate_limit_per_minute: int = Field(default=600, ge=1, le=100_000)
    write_rate_limit_per_minute: int = Field(default=60, ge=1, le=100_000)
    chat_rate_limit_per_minute: int = Field(default=30, ge=1, le=600)
    # Deprecated: the `llm` health entry now reflects the model router. Kept so old .env files load.
    llm_enabled: bool = False
    # --- Sub-phase 2H / M1: model router. Names documented in docs/hybrid-ai/PHASE_2_HYBRID_AI_ARCHITECTURE.md.
    ai_execution_mode: Literal["cloud_preferred", "local_first", "offline_only"] = "local_first"
    ollama_base_url: str | None = None
    ollama_model: str = "qwen2.5:3b-instruct-q4_K_M"
    ollama_keep_alive: str = "30m"
    vllm_base_url: str | None = None
    vllm_model: str = "Qwen/Qwen2.5-7B-Instruct-AWQ"
    vllm_api_key: SecretStr | None = None
    llamacpp_base_url: str | None = None
    llamacpp_model: str = "local"
    # A local model on CPU runs ~5-10 tokens/s; 500 output tokens must finish inside this.
    llm_timeout_s: float = Field(default=180.0, gt=0, le=600)
    provider_failure_threshold: int = Field(default=3, ge=1, le=20)
    provider_cooldown_s: float = Field(default=30.0, ge=1, le=3600)
    provider_probe_timeout_s: float = Field(default=2.0, gt=0, le=5)
    provider_health_ttl_s: float = Field(default=15.0, ge=1, le=600)
    embedding_cache_dir: str | None = None
    embedding_offline: bool = False
    # ADR-006: the fastembed ONNX cross-encoder reorders the first `rerank_depth` search results. On by
    # default since 2026-11-12: hit@1 0.81 -> 0.88 and MRR@10 0.86 -> 0.91 on the 26-question gold set, at
    # about 0.7 s per search on a shared 4-core CPU (docs/evaluation/reports/retrieval-2026-11-12.md §5).
    # With no cached model in an offline deployment, search falls back to the fused order ("unavailable").
    reranker_enabled: bool = True
    # How many of the first fused /api/search results the cross-encoder reorders (page-independent).
    # 10 scored the same as 20 on the gold set, for half the model work.
    rerank_depth: int = Field(default=10, ge=2, le=100)
    # Roadmap item 8: figures and identifiers in a chat answer that appear in none of the cited passages.
    # "warn" adds the warning `answer_values_not_in_cited_evidence` (and keeps the answer out of the cache);
    # "strict" also withholds the answer text (`answer_withheld_unsupported_values`); "off" skips the check.
    # It is a traceability check, not entailment: see ai/rag/verification/support.py.
    answer_support_check: Literal["off", "warn", "strict"] = "warn"
    # Roadmap item 10. "and": every question term must match (plainto_tsquery, the served behaviour). "or_idf": any term
    # may match and a chunk scores the sum of its matched terms' idf (apps/api/flame_api/lexical.py). Default stays "and"
    # until the passage-level gold set (>= 20 verified questions) shows a difference; PostgreSQL only.
    lexical_mode: Literal["and", "or_idf"] = "and"
    # Roadmap item 11. "page": the dense leg embeds each page's first 2,000 characters (served behaviour). "window": it embeds
    # overlapping 1,200-character windows of the whole page and a page scores as its best window; needs
    # `python -m flame_api.vector_index build-windows`, falls back to "page" when there are no windows. Default "page" until the
    # passage-level gold set (>= 20 verified questions) shows a difference.
    dense_granularity: Literal["page", "window"] = "page"
    # Roadmap item 8 (abstention). None: no gate. A number: `/api/chat` answers "too weak" without calling a model when the best fused score of
    # the search for the whole question is below it. That score is the agreement of the lexical and dense legs (at most about 0.033), not a
    # relevance probability. Choose it with `ai.rag.evaluation.run_passage_gold run --mode chat` and `calibrate`, which need 20 verified
    # answerable and 8 verified unanswerable passage-gold cases; do not set it from a guess.
    chat_abstain_below: float | None = Field(default=None, ge=0, le=1)
    otel_enabled: bool = False
    otel_service_name: str = "flame-api"
    cv_provider: Literal["local", "hf_space"] = "local"
    cv_hf_space_url: str | None = None
    cv_hf_token: SecretStr | None = None
    cv_timeout_s: float = Field(default=300.0, gt=0, le=600)
    # Operator speech in flight video (docs/cv/audio-transcription.md). Off by default: it needs the
    # faster-whisper model cached (`python -m ai.providers.local.faster_whisper_transcription prepare`).
    # Transcription runs locally only; it never leaves the machine and a failure never fails the video job.
    transcription_enabled: bool = False
    transcription_model: str = "small"
    transcription_cache_dir: str | None = None

    @model_validator(mode="after")
    def require_distinct_api_tokens(self):
        if self.api_auth_enabled:
            # Neither legacy token is required any more: a deployment may run on client keys alone.
            tokens = {name: token.get_secret_value() for name, token in (
                ("FLAME_READ_API_TOKEN", self.read_api_token), ("FLAME_WRITE_API_TOKEN", self.write_api_token),
            ) if token is not None}
            if any(len(token) < 32 for token in tokens.values()):
                raise ValueError("Flame API tokens must contain at least 32 characters.")
            if len(tokens) == 2 and compare_digest(*(token.encode() for token in tokens.values())):
                raise ValueError("FLAME_READ_API_TOKEN and FLAME_WRITE_API_TOKEN must be different.")
        if self.environment.strip().lower() == "production":
            self._refuse_local_defaults()

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
        if self.cv_hf_space_url is not None:
            cv_url = urlsplit(self.cv_hf_space_url)
            if (
                cv_url.scheme != "https"
                or not cv_url.netloc
                or cv_url.path not in {"", "/"}
                or cv_url.username is not None
                or cv_url.password is not None
                or cv_url.query
                or cv_url.fragment
            ):
                raise ValueError("FLAME_CV_HF_SPACE_URL must be an HTTPS origin without embedded credentials.")
        for name in ("ollama_base_url", "vllm_base_url", "llamacpp_base_url"):
            value = getattr(self, name)
            if value is None:
                continue
            local_url = urlsplit(value)
            # Local runtimes live on the same (possibly disconnected) network, so plain HTTP is allowed.
            if (
                local_url.scheme not in {"http", "https"}
                or not local_url.netloc
                or local_url.path not in {"", "/"}
                or local_url.username is not None
                or local_url.password is not None
                or local_url.query
                or local_url.fragment
            ):
                raise ValueError(f"FLAME_{name.upper()} must be an http(s) origin without a path or credentials.")
        if self.cv_provider == "hf_space" and self.cv_hf_space_url is None:
            raise ValueError("FLAME_CV_HF_SPACE_URL is required when FLAME_CV_PROVIDER=hf_space.")
        return self

    def _refuse_local_defaults(self) -> None:
        """P2-6: the local-only values in this file and in Compose must never reach production.

        The error names the setting, never the value: settings errors end up in deploy logs.
        """
        secret = self.s3_secret_key.get_secret_value()
        if secret in _LOCAL_S3_SECRETS or "change-me" in secret.lower():
            raise ValueError("FLAME_S3_SECRET_KEY is a local development default; set a real secret in production.")
        if self.s3_access_key in _LOCAL_S3_ACCESS_KEYS:
            raise ValueError("FLAME_S3_ACCESS_KEY is a local development default; set a real access key in production.")
        try:
            password = urlsplit(self.database_url).password
        except ValueError:
            password = None
        if password is not None and (password in _LOCAL_DB_PASSWORDS or "change-me" in password.lower()):
            raise ValueError("FLAME_DATABASE_URL uses a local development database password; set a real one in production.")


# The defaults above plus the Compose fallbacks in infrastructure/compose.yaml.
_LOCAL_S3_SECRETS = frozenset({"change-me-local-only", "flame-local-only-change-me"})
_LOCAL_S3_ACCESS_KEYS = frozenset({"flame-local"})
_LOCAL_DB_PASSWORDS = frozenset({"flame", "flame-local-only"})


@lru_cache
def get_settings() -> Settings:
    return Settings()
