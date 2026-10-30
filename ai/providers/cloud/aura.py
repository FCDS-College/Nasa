"""AURA as one optional, external provider (ADR-004).

Flame calls AURA's ``POST /api/v3/chat`` with a narrow service key. Flame does its own retrieval,
so AURA's tools, knowledge and memory are off. Evidence travels in ``context`` (AURA's DATA
channel), never in ``message``. AURA validates the reply against ``response_schema``; Flame
validates it again (``flame_api/generation.py``).
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from ai.providers.contracts.base import Capability, HealthStatus, Locality, ProviderInfo
from ai.providers.contracts.chat import ChatRequest, ChatResponse
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
from ai.providers.contracts.structured import StructuredRequest, StructuredResponse
from ai.providers.http import probe, request_json

MAX_CONTEXT_ENTRIES = 16
MAX_CONTEXT_TEXT = 2000  # AURA rejects a longer `context[].text` with 422 (ContextEntry)


class AuraProvider:
    def __init__(self, *, base_url: str, service_token: str, timeout_s: float = 120.0, require_local: bool = True) -> None:
        self._base = base_url.rstrip("/")
        self._token = service_token
        self._timeout_s = timeout_s
        self._require_local = require_local
        self.info = ProviderInfo(
            name="aura", runtime="aura", locality=Locality.EXTERNAL,
            capabilities=frozenset({Capability.CHAT, Capability.STRUCTURED}), model=None, version=None,
        )

    def health(self, timeout_s: float) -> HealthStatus:
        started = time.perf_counter()
        try:
            probe(f"{self._base}/health/ready", provider="aura", timeout_s=timeout_s)
        except ProviderError as exc:
            return HealthStatus("down", round((time.perf_counter() - started) * 1000, 1), exc.code.value)
        return HealthStatus("up", round((time.perf_counter() - started) * 1000, 1))

    def _body(self, request: ChatRequest, schema: dict[str, Any] | None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "message": "\n\n".join(m.content for m in request.messages if m.content),
            "agent": "orchestrator",
            "plan": False,
            "use_knowledge": False,
            "use_memory": False,
            "use_tools": False,
            "require_local": bool(request.options.get("require_local", self._require_local)),
            "max_output_tokens": request.max_output_tokens,
            "temperature": request.temperature,
            "context": [{"id": p.id, "text": p.text[:MAX_CONTEXT_TEXT], "source": p.source}
                        for p in request.context[:MAX_CONTEXT_ENTRIES]],
        }
        if schema is not None:
            body["response_schema"] = schema
        return body

    def _post(self, request: ChatRequest, schema: dict[str, Any] | None) -> dict[str, Any]:
        key = request.idempotency_key
        body = self._body(request, schema)
        headers = {"Authorization": f"Bearer {self._token}"}
        if key:
            # AURA replays any stored <500 answer for 24h and rejects the same key with a different body
            # (422 idempotency_key_reused). Binding the key to the body keeps exact retries deduplicated
            # while a re-run with new evidence or instructions is a new request.
            digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
            headers.update({"Idempotency-Key": f"{key}:{digest}", "X-Correlation-Id": key})
        decoded = request_json(
            "POST", f"{self._base}/api/v3/chat", provider="aura",
            timeout_s=request.timeout_s or self._timeout_s, body=body, headers=headers,
        )
        if not isinstance(decoded, dict):
            raise ProviderError(ProviderErrorCode.INVALID_OUTPUT, "aura returned a non-object.", provider="aura")
        return decoded

    @staticmethod
    def _model(decoded: dict[str, Any]) -> str:
        return decoded["model"] if isinstance(decoded.get("model"), str) else "unknown"

    def chat(self, request: ChatRequest) -> ChatResponse:
        decoded = self._post(request, None)
        if not isinstance(decoded.get("message"), str):
            raise ProviderError(ProviderErrorCode.INVALID_OUTPUT, "aura returned no message.", provider="aura")
        return ChatResponse(text=decoded["message"], model=self._model(decoded), provider="aura",
                            cached=bool(decoded.get("cached")), usage=decoded.get("usage") or {})

    def generate_structured(self, request: StructuredRequest) -> StructuredResponse:
        decoded = self._post(request.chat, request.schema)
        if not isinstance(decoded.get("data"), dict):
            raise ProviderError(ProviderErrorCode.INVALID_OUTPUT, "aura response did not contain structured data.", provider="aura")
        # AURA routes to its own model pool; report which upstream it used, keyed as aura/<provider>.
        upstream = decoded.get("provider") if isinstance(decoded.get("provider"), str) else None
        return StructuredResponse(data=decoded["data"], model=self._model(decoded),
                                  provider=f"aura/{upstream}" if upstream else "aura",
                                  cached=bool(decoded.get("cached")), usage=decoded.get("usage") or {})
