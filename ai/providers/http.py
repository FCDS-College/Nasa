"""Stdlib JSON-over-HTTP for adapters, with every failure mapped to a ProviderError.

Adapters call ``request_json`` instead of ``urlopen`` directly so timeouts, size caps and error
normalization are the same everywhere. Tests replace ``urlopen`` in this module.
"""
from __future__ import annotations

import json
import logging
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ai.providers.contracts.errors import ProviderError, ProviderErrorCode

logger = logging.getLogger("flame_api")

DEFAULT_MAX_BYTES = 64 * 1024
_OOM_MARKERS = ("out of memory", "requires more system memory", "insufficient memory", "cuda error: out of memory")


def _rejected_fields(raw: bytes) -> list[tuple[str, str, str]]:
    """(type, location, message) of a FastAPI-style 422, never the payload itself."""
    try:
        detail = json.loads(raw).get("detail")
        return [(str(r.get("type")), "/".join(map(str, r.get("loc", []))), str(r.get("msg"))) for r in detail][:5]
    except (ValueError, AttributeError, TypeError):
        return []


def _map_http_error(exc: HTTPError, provider: str) -> ProviderError:
    try:
        raw = exc.read(8192) or b""
    except OSError:
        raw = b""
    lowered = raw.decode("utf-8", "replace").lower()
    code = exc.code
    if code == 422:
        logger.warning("provider_request_rejected provider=%s fields=%s", provider, _rejected_fields(raw))
    if any(marker in lowered for marker in _OOM_MARKERS) or code in {413, 429, 507}:
        mapped = ProviderErrorCode.RESOURCE_EXHAUSTED
    elif code == 404 and "model" in lowered and ("not found" in lowered or "does not exist" in lowered):
        mapped = ProviderErrorCode.MODEL_MISSING
    elif code in {401, 403}:
        mapped = ProviderErrorCode.NOT_CONFIGURED
    elif code >= 500:
        mapped = ProviderErrorCode.UNAVAILABLE
    else:
        mapped = ProviderErrorCode.INVALID_REQUEST
    return ProviderError(mapped, f"{provider} returned HTTP {code}.", provider=provider, status_code=code)


def request_json(
    method: str,
    url: str,
    *,
    provider: str,
    timeout_s: float,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Any:
    data = None
    all_headers = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        data = json.dumps(body, separators=(",", ":"), allow_nan=False).encode("utf-8")
        all_headers["Content-Type"] = "application/json"
    request = Request(url, data=data, method=method, headers=all_headers)
    try:
        with urlopen(request, timeout=timeout_s) as response:
            status = getattr(response, "status", 200)
            if status < 200 or status >= 300:
                raise ProviderError(ProviderErrorCode.UNAVAILABLE, f"{provider} returned HTTP {status}.",
                                    provider=provider, status_code=status)
            payload = response.read(max_bytes + 1)
    except ProviderError:
        raise
    except HTTPError as exc:
        raise _map_http_error(exc, provider) from exc
    except URLError as exc:
        # URLError is raised while connecting: the request never reached the provider.
        reason = exc.reason
        code = ProviderErrorCode.TIMEOUT if isinstance(reason, (TimeoutError, socket.timeout)) else ProviderErrorCode.UNAVAILABLE
        raise ProviderError(code, f"{provider} could not be reached.", provider=provider, request_sent=False) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise ProviderError(ProviderErrorCode.TIMEOUT, f"{provider} did not answer in time.", provider=provider) from exc
    except OSError as exc:
        raise ProviderError(ProviderErrorCode.UNAVAILABLE, f"{provider} connection failed.", provider=provider) from exc

    if len(payload) > max_bytes:
        raise ProviderError(ProviderErrorCode.INVALID_OUTPUT, f"{provider} response exceeded the size limit.", provider=provider)
    try:
        return json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderError(ProviderErrorCode.INVALID_OUTPUT, f"{provider} returned invalid JSON.", provider=provider) from exc


def probe(url: str, *, provider: str, timeout_s: float, headers: dict[str, str] | None = None) -> Any:
    """GET for a health check. Same mapping; callers turn the ProviderError into a HealthStatus."""
    return request_json("GET", url, provider=provider, timeout_s=timeout_s, headers=headers, max_bytes=256 * 1024)


def parse_json_object(text: str, *, provider: str) -> dict[str, Any]:
    """Models sometimes wrap JSON in prose or code fences; take the outermost object or fail."""
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        candidate = candidate[candidate.find("{"):] if "{" in candidate else candidate
    start, end = candidate.find("{"), candidate.rfind("}")
    if start < 0 or end <= start:
        raise ProviderError(ProviderErrorCode.INVALID_OUTPUT, f"{provider} did not return a JSON object.", provider=provider)
    try:
        value = json.loads(candidate[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ProviderError(ProviderErrorCode.INVALID_OUTPUT, f"{provider} returned malformed JSON.", provider=provider) from exc
    if not isinstance(value, dict):
        raise ProviderError(ProviderErrorCode.INVALID_OUTPUT, f"{provider} returned a non-object.", provider=provider)
    return value
