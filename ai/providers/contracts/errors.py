"""Normalized provider errors. Every adapter maps its own failures onto these codes."""
from __future__ import annotations

from enum import Enum


class ProviderErrorCode(str, Enum):
    NOT_CONFIGURED = "not_configured"          # provider has no endpoint/credentials
    UNAVAILABLE = "unavailable"                # unreachable, 5xx, connection refused
    TIMEOUT = "timeout"                        # no answer inside the configured timeout
    MODEL_MISSING = "model_missing"            # runtime is up but the model is not installed / corrupt
    RESOURCE_EXHAUSTED = "resource_exhausted"  # out of memory, context too long, rate/budget limit
    INVALID_REQUEST = "invalid_request"        # the provider rejected what we sent (4xx)
    INVALID_OUTPUT = "invalid_output"          # the provider answered, but not in the required shape
    EGRESS_BLOCKED = "egress_blocked"          # refused by the execution mode before any socket opened
    UNSUPPORTED = "unsupported"                # capability not offered by this provider


# Failures where trying a different provider can help. INVALID_REQUEST is ours to fix, not theirs.
_FALLBACK_CODES = frozenset({
    ProviderErrorCode.UNAVAILABLE, ProviderErrorCode.TIMEOUT, ProviderErrorCode.MODEL_MISSING,
    ProviderErrorCode.RESOURCE_EXHAUSTED, ProviderErrorCode.INVALID_OUTPUT, ProviderErrorCode.NOT_CONFIGURED,
    ProviderErrorCode.EGRESS_BLOCKED, ProviderErrorCode.UNSUPPORTED,
})


class ProviderError(Exception):
    """A provider failure with a stable code. ``message`` never carries credentials or payloads.

    ``request_sent`` is False when the failure happened before the request reached the provider
    (connection refused, DNS failure, egress blocked). Only then is a non-idempotent call safe to
    send somewhere else.

    ``upstream_code`` is the provider's own error slug when its body carried one (AURA's
    ``error``, e.g. ``capability_unavailable``): for logs and operators only, never for routing.
    """

    def __init__(
        self,
        code: ProviderErrorCode,
        message: str,
        *,
        provider: str | None = None,
        status_code: int | None = None,
        request_sent: bool = True,
        upstream_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = ProviderErrorCode(code)
        self.message = message
        self.provider = provider
        self.status_code = status_code
        self.request_sent = request_sent
        self.upstream_code = upstream_code

    @property
    def fallback_eligible(self) -> bool:
        return self.code in _FALLBACK_CODES

    @property
    def retryable(self) -> bool:
        return self.code in {ProviderErrorCode.UNAVAILABLE, ProviderErrorCode.TIMEOUT, ProviderErrorCode.RESOURCE_EXHAUSTED}

    def to_dict(self) -> dict:
        return {"provider": self.provider, "code": self.code.value, "status_code": self.status_code}

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"ProviderError({self.code.value!r}, provider={self.provider!r}, status={self.status_code!r})"
