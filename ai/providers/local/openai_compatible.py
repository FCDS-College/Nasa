"""Any server speaking the OpenAI chat-completions dialect on our own network (vLLM, llama.cpp)."""
from __future__ import annotations

import time
from typing import Any

from ai.providers.contracts.base import Capability, HealthStatus, Locality, ProviderInfo
from ai.providers.contracts.chat import ChatRequest, ChatResponse
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
from ai.providers.contracts.structured import StructuredRequest, StructuredResponse
from ai.providers.http import parse_json_object, probe, request_json
from ai.providers.local.ollama import messages_with_context


class OpenAICompatibleProvider:
    runtime = "openai_compatible"

    def __init__(self, *, base_url: str, model: str, name: str, timeout_s: float = 180.0,
                 api_key: str | None = None, context_window: int | None = None) -> None:
        self._base = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.info = ProviderInfo(
            name=name, runtime=self.runtime, locality=Locality.LOCAL,
            capabilities=frozenset({Capability.CHAT, Capability.STRUCTURED}), model=model,
            context_window=context_window,
        )

    def health(self, timeout_s: float) -> HealthStatus:
        started = time.perf_counter()
        try:
            listing = probe(f"{self._base}/v1/models", provider=self.info.name, timeout_s=timeout_s, headers=self._headers)
        except ProviderError as exc:
            return HealthStatus("down", round((time.perf_counter() - started) * 1000, 1), exc.code.value)
        latency = round((time.perf_counter() - started) * 1000, 1)
        ids = {m.get("id") for m in (listing.get("data") or []) if isinstance(m, dict)} if isinstance(listing, dict) else set()
        if self._model not in ids:
            return HealthStatus("down", latency, ProviderErrorCode.MODEL_MISSING.value, model_present=False)
        return HealthStatus("up", latency, model_present=True)

    def _call(self, request: ChatRequest, schema: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
        body: dict[str, Any] = {
            "model": self._model,
            "messages": messages_with_context(request),
            "max_tokens": request.max_output_tokens,
            "temperature": request.temperature,
            "stream": False,
        }
        if schema is not None:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "flame_response", "schema": schema}}
        decoded = request_json("POST", f"{self._base}/v1/chat/completions", provider=self.info.name,
                               timeout_s=request.timeout_s or self._timeout_s, body=body, headers=self._headers,
                               max_bytes=1024 * 1024)
        try:
            content = decoded["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(ProviderErrorCode.INVALID_OUTPUT, "no completion returned.", provider=self.info.name) from exc
        if not isinstance(content, str):
            raise ProviderError(ProviderErrorCode.INVALID_OUTPUT, "completion is not text.", provider=self.info.name)
        usage = decoded.get("usage") if isinstance(decoded.get("usage"), dict) else {}
        return content, usage

    def chat(self, request: ChatRequest) -> ChatResponse:
        content, usage = self._call(request, None)
        return ChatResponse(text=content, model=self._model, provider=self.info.name, usage=usage)

    def generate_structured(self, request: StructuredRequest) -> StructuredResponse:
        content, usage = self._call(request.chat, request.schema)
        return StructuredResponse(data=parse_json_object(content, provider=self.info.name), model=self._model,
                                  provider=self.info.name, usage=usage)
