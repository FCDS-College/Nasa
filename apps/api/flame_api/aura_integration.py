"""Compatibility layer for code written before the model router (M1).

The AURA HTTP client is ``ai/providers/cloud/aura.py``; prompts, schemas and validation are in
``flame_api/generation.py``. These helpers keep the old call signatures by routing through an
AURA-only router, for callers (and tests) that mean "ask AURA specifically".
"""
from __future__ import annotations

from typing import Any

from ai.providers.cloud.aura import AuraProvider
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
from ai.routing import ExecutionMode, NoCompatibleProvider, ProviderRegistry, Router
from flame_api import generation
from flame_api.config import Settings

AURA_RESPONSE_SCHEMA = generation.INTERPRETATION_SCHEMA
AURA_CHAT_SCHEMA = generation.CHAT_SCHEMA


class AuraIntegrationError(ProviderError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(ProviderErrorCode.UNAVAILABLE, message, provider="aura", status_code=status_code)


def _provider(settings: Settings) -> AuraProvider:
    if settings.aura_service_token is None:
        raise AuraIntegrationError("AURA service credentials are not configured.")
    return AuraProvider(base_url=settings.aura_base_url, service_token=settings.aura_service_token.get_secret_value(),
                        timeout_s=settings.aura_timeout_s, require_local=settings.aura_require_local)


def _aura_only(settings: Settings) -> Router:
    registry = ProviderRegistry()
    registry.register(_provider(settings))
    return Router(registry, mode=ExecutionMode.CLOUD_PREFERRED)


def check_aura_ready(settings: Settings, *, timeout_s: float = 2.0) -> tuple[str, float]:
    status = AuraProvider(base_url=settings.aura_base_url, service_token="", timeout_s=timeout_s,
                          require_local=settings.aura_require_local).health(timeout_s)
    return ("up" if status.state == "up" else "down"), status.latency_ms or 0.0


def _unwrap(exc: NoCompatibleProvider) -> AuraIntegrationError:
    last = exc.last_error
    return AuraIntegrationError(last.message if last else str(exc), status_code=last.status_code if last else None)


def interpret_analysis(settings: Settings, **kwargs: Any) -> dict[str, Any]:
    try:
        return generation.interpret_analysis(_aura_only(settings), **kwargs)
    except NoCompatibleProvider as exc:
        raise _unwrap(exc) from exc


def answer_question(settings: Settings, **kwargs: Any) -> dict[str, Any]:
    try:
        return generation.answer_question(_aura_only(settings), **kwargs)
    except NoCompatibleProvider as exc:
        raise _unwrap(exc) from exc
