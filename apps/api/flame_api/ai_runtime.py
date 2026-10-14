"""The one place where Flame's settings meet concrete AI providers (2H Task 2).

Everything else in ``flame_api`` asks this module for the router and talks to provider-neutral
contracts. Changing which model answers is a configuration change here, not a code change elsewhere.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import UTC, datetime

from ai.routing import CircuitBreaker, ExecutionMode, HealthMonitor, ProviderRegistry, Router
from flame_api.config import Settings, get_settings

logger = logging.getLogger("flame_api")

MODE_ACTION = "ai.mode.changed"

_lock = threading.Lock()
_router: Router | None = None
_router_settings: Settings | None = None   # strong ref: an id() could be reused after GC
_mode_override: ExecutionMode | None = None
_override_checked_at: float = 0.0
_OVERRIDE_TTL_S = 10.0


def _secret(value) -> str | None:
    return value.get_secret_value() if value is not None else None


def build_router(settings: Settings) -> Router:
    from ai.providers.cloud.aura import AuraProvider
    from ai.providers.cloud.hf_space_cv import HfSpaceCvProvider
    from ai.providers.local.fastembed_embeddings import FastEmbedProvider
    from ai.providers.local.flame_cv import FlameCvProvider
    from ai.providers.local.flame_cv_video import FlameCvVideoProvider
    from ai.providers.local.llamacpp import LlamaCppProvider
    from ai.providers.local.ollama import OllamaProvider
    from ai.providers.local.vllm import VllmProvider

    registry = ProviderRegistry()
    router = Router(
        registry,
        mode=ExecutionMode(settings.ai_execution_mode),
        breaker=CircuitBreaker(threshold=settings.provider_failure_threshold, cooldown_s=settings.provider_cooldown_s),
        monitor=HealthMonitor(probe_timeout_s=settings.provider_probe_timeout_s, ttl_s=settings.provider_health_ttl_s),
        mode_source=current_mode_override,
    )

    def models_offline() -> bool:
        # Local model runtimes must never download weights while the effective mode is offline_only,
        # including after a runtime mode switch; downloads belong to the explicit `prepare` command.
        return settings.embedding_offline or router.mode is ExecutionMode.OFFLINE_ONLY

    # Priority breaks ties inside one locality: GPU vLLM before CPU Ollama before llama.cpp.
    if settings.vllm_base_url:
        registry.register(VllmProvider(base_url=settings.vllm_base_url, model=settings.vllm_model,
                                       timeout_s=settings.llm_timeout_s, api_key=_secret(settings.vllm_api_key)), priority=10)
    if settings.ollama_base_url:
        registry.register(OllamaProvider(base_url=settings.ollama_base_url, model=settings.ollama_model,
                                         timeout_s=settings.llm_timeout_s, keep_alive=settings.ollama_keep_alive), priority=20)
    if settings.llamacpp_base_url:
        registry.register(LlamaCppProvider(base_url=settings.llamacpp_base_url, model=settings.llamacpp_model,
                                           timeout_s=settings.llm_timeout_s), priority=30)
    if settings.aura_enabled and settings.aura_service_token is not None:
        registry.register(AuraProvider(base_url=settings.aura_base_url, service_token=_secret(settings.aura_service_token),
                                       timeout_s=settings.aura_timeout_s, require_local=settings.aura_require_local), priority=50)
    registry.register(FastEmbedProvider(cache_dir=settings.embedding_cache_dir, offline=models_offline), priority=10)
    if settings.reranker_enabled:
        from ai.providers.local.cross_encoder import CrossEncoderReranker

        registry.register(CrossEncoderReranker(offline=models_offline), priority=10)
    # FLAME_CV_PROVIDER picks the preferred vision provider; the other one stays as the fallback.
    registry.register(FlameCvProvider(), priority=10 if settings.cv_provider == "local" else 20)
    registry.register(FlameCvVideoProvider(), priority=10)  # local only: video never leaves the machine
    if settings.cv_hf_space_url:
        registry.register(HfSpaceCvProvider(base_url=settings.cv_hf_space_url, token=_secret(settings.cv_hf_token),
                                            timeout_s=settings.cv_timeout_s, max_upload_bytes=settings.max_upload_bytes),
                          priority=10 if settings.cv_provider == "hf_space" else 20)
    return router


def get_router(settings: Settings | None = None) -> Router:
    """The process-wide router, rebuilt when a different Settings object is in force (tests swap it)."""
    global _router, _router_settings
    settings = settings or get_settings()
    with _lock:
        if _router is None or _router_settings is not settings:
            _router = build_router(settings)
            _router_settings = settings
        return _router


def reset() -> None:
    global _router, _router_settings, _mode_override, _override_checked_at
    with _lock:
        _router = None
        _router_settings = None
        _mode_override = None
        _override_checked_at = 0.0


def _latest_audited_mode() -> ExecutionMode | None:
    """The mode from the newest audit_event, so every process (API replicas, RQ worker) agrees."""
    from sqlalchemy import select

    from flame_api.database import SessionLocal
    from flame_api.models import AuditEvent

    with SessionLocal() as session:
        row = session.execute(
            select(AuditEvent.after).where(AuditEvent.action == MODE_ACTION).order_by(AuditEvent.occurred_at.desc()).limit(1)
        ).scalar_one_or_none()
    if isinstance(row, dict) and row.get("mode") in {m.value for m in ExecutionMode}:
        return ExecutionMode(row["mode"])
    return None


def current_mode_override() -> ExecutionMode | None:
    global _mode_override, _override_checked_at
    now = time.monotonic()
    if now - _override_checked_at >= _OVERRIDE_TTL_S:
        _override_checked_at = now
        try:
            persisted = _latest_audited_mode()
        except Exception:  # no database (tests, first boot): keep what this process knows
            persisted = None
        if persisted is not None:
            _mode_override = persisted
    return _mode_override


def set_mode(session, mode: ExecutionMode, *, router: Router, actor: str, request_id: str | None) -> dict:
    """Switch the execution mode for this process now and, via the audit row, for every process."""
    global _mode_override, _override_checked_at
    from flame_api.ids import new_ulid
    from flame_api.models import AuditEvent

    before = router.mode
    session.add(AuditEvent(
        event_id=new_ulid(), occurred_at=datetime.now(UTC), actor=actor, action=MODE_ACTION,
        target_type="ai_execution_mode", target_id=None, before={"mode": before.value},
        after={"mode": mode.value}, request_id=request_id,
    ))
    session.commit()
    with _lock:
        _mode_override = mode
        _override_checked_at = time.monotonic()
    logger.warning("ai_mode_changed from=%s to=%s actor=%s request_id=%s", before.value, mode.value, actor, request_id)
    return {"previous_mode": before.value, "mode": mode.value}

