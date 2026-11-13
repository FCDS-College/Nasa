"""Ollama (local LLM runtime). Uses the native ``/api/chat`` with ``format`` set to the JSON schema."""
from __future__ import annotations

import time
from typing import Any

from ai.providers.contracts.base import Capability, HealthStatus, Locality, ProviderInfo
from ai.providers.contracts.chat import ChatMessage, ChatRequest, ChatResponse, render_context
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
from ai.providers.contracts.structured import StructuredRequest, StructuredResponse
from ai.providers.http import parse_json_object, probe, request_json


def messages_with_context(request: ChatRequest) -> list[dict[str, str]]:
    """Instructions (system) first, then the fenced evidence as a *user* message, then the rest.

    Retrieved text never gets system privileges: a document that tries to give orders is data in a user turn,
    escaped and fenced by ``render_context``. The evidence turn also guarantees the conversation ends with a
    user message when a request carries only system instructions and context.
    """
    system = [m for m in request.messages if m.role == "system"]
    rest = [m for m in request.messages if m.role != "system"]
    ordered: list[ChatMessage] = [*system, ChatMessage("user", render_context(request.context)), *rest]
    return [{"role": m.role, "content": m.content} for m in ordered]


class OllamaProvider:
    def __init__(self, *, base_url: str, model: str, timeout_s: float = 180.0, keep_alive: str = "30m",
                 context_window: int | None = None, name: str = "ollama") -> None:
        self._base = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s
        self._keep_alive = keep_alive
        self.info = ProviderInfo(
            name=name, runtime="ollama", locality=Locality.LOCAL,
            capabilities=frozenset({Capability.CHAT, Capability.STRUCTURED}), model=model,
            context_window=context_window,
        )

    def health(self, timeout_s: float) -> HealthStatus:
        started = time.perf_counter()
        try:
            tags = probe(f"{self._base}/api/tags", provider=self.info.name, timeout_s=timeout_s)
        except ProviderError as exc:
            return HealthStatus("down", round((time.perf_counter() - started) * 1000, 1), exc.code.value)
        latency = round((time.perf_counter() - started) * 1000, 1)
        names = {m.get("name") for m in (tags.get("models") or []) if isinstance(m, dict)} if isinstance(tags, dict) else set()
        wanted = {self._model, f"{self._model}:latest"}
        if not names & wanted:
            return HealthStatus("down", latency, ProviderErrorCode.MODEL_MISSING.value, model_present=False)
        return HealthStatus("up", latency, model_present=True)

    def _call(self, request: ChatRequest, fmt: Any) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self._model,
            "messages": messages_with_context(request),
            "stream": False,
            "keep_alive": self._keep_alive,
            "options": {"temperature": request.temperature, "num_predict": request.max_output_tokens},
        }
        if fmt is not None:
            body["format"] = fmt
        decoded = request_json("POST", f"{self._base}/api/chat", provider=self.info.name,
                               timeout_s=request.timeout_s or self._timeout_s, body=body, max_bytes=1024 * 1024)
        message = decoded.get("message") if isinstance(decoded, dict) else None
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ProviderError(ProviderErrorCode.INVALID_OUTPUT, "ollama returned no message.", provider=self.info.name)
        return decoded

    @staticmethod
    def _usage(decoded: dict[str, Any]) -> dict[str, Any]:
        return {"prompt_tokens": decoded.get("prompt_eval_count"), "completion_tokens": decoded.get("eval_count")}

    def chat(self, request: ChatRequest) -> ChatResponse:
        decoded = self._call(request, None)
        return ChatResponse(text=decoded["message"]["content"], model=self._model, provider=self.info.name,
                            usage=self._usage(decoded))

    def generate_structured(self, request: StructuredRequest) -> StructuredResponse:
        decoded = self._call(request.chat, request.schema)
        data = parse_json_object(decoded["message"]["content"], provider=self.info.name)
        return StructuredResponse(data=data, model=self._model, provider=self.info.name, usage=self._usage(decoded))
