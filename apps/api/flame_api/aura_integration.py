import json
import logging
import re
import time
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from flame_api.config import Settings

logger = logging.getLogger("flame_api")


def _log_validation_failure(exc: HTTPError) -> None:
    """Log which request fields AURA rejected (type, location, message only; never the payload)."""
    try:
        raw = exc.read(8192)
        detail = json.loads(raw).get("detail")
        rows = [(str(r.get("type")), "/".join(map(str, r.get("loc", []))), str(r.get("msg"))) for r in detail]
    except (ValueError, AttributeError, TypeError):
        logger.warning("aura_request_rejected body=%r", raw[:300] if "raw" in locals() else None)
        return
    logger.warning("aura_request_rejected fields=%s", rows[:5])

AURA_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["statements"],
    "additionalProperties": False,
    "properties": {
        "statements": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "type": "object",
                "required": ["text", "claim_class", "evidence_ids"],
                "additionalProperties": False,
                "properties": {
                    "text": {"type": "string"},
                    "claim_class": {
                        "type": "string",
                        "enum": ["inferred", "hypothesized", "unsupported"],
                    },
                    "evidence_ids": {
                        "type": "array",
                        "maxItems": 16,
                        "items": {"type": "string"},
                    },
                },
            },
        },
    },
}
_UNSUPPORTED_OUTCOME = re.compile(
    r"\b(outcome|extinction|extinguished|ignition|ignited|burn time|sustained combustion)\b",
    re.IGNORECASE,
)


class AuraIntegrationError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _base_url(settings: Settings) -> str:
    return settings.aura_base_url.rstrip("/")


def check_aura_ready(settings: Settings, *, timeout_s: float = 2.0) -> tuple[str, float]:
    started = time.perf_counter()
    request = Request(f"{_base_url(settings)}/health/ready", method="GET")
    try:
        with urlopen(request, timeout=timeout_s) as response:
            status = "up" if 200 <= response.status < 300 else "down"
    except HTTPError:
        status = "down"
    except (TimeoutError, URLError, OSError):
        status = "down"
    return status, round((time.perf_counter() - started) * 1000, 1)


def _post_chat(settings: Settings, request_body: dict[str, Any], *, idempotency_key: str) -> dict[str, Any]:
    body = json.dumps(request_body, separators=(",", ":"), allow_nan=False).encode("utf-8")
    request = Request(
        f"{_base_url(settings)}/api/v3/chat",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.aura_service_token.get_secret_value()}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
            "X-Correlation-Id": idempotency_key,
        },
    )
    try:
        with urlopen(request, timeout=settings.aura_timeout_s) as response:
            if response.status < 200 or response.status >= 300:
                raise AuraIntegrationError(
                    "AURA returned an unsuccessful response.", status_code=response.status
                )
            response_body = response.read(64 * 1024 + 1)
    except HTTPError as exc:
        if exc.code == 422:
            _log_validation_failure(exc)
        raise AuraIntegrationError(
            "AURA returned an unsuccessful response.", status_code=exc.code
        ) from exc
    except (TimeoutError, URLError, OSError) as exc:
        raise AuraIntegrationError("AURA could not be reached.") from exc

    if len(response_body) > 64 * 1024:
        raise AuraIntegrationError("AURA response exceeded the configured size limit.")
    try:
        decoded = json.loads(response_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuraIntegrationError("AURA returned invalid JSON.") from exc
    if not isinstance(decoded, dict) or not isinstance(decoded.get("data"), dict):
        raise AuraIntegrationError("AURA response did not contain structured data.")
    return decoded


def interpret_analysis(
    settings: Settings,
    *,
    analysis_id: str,
    context: list[dict[str, str]],
    allowed_evidence_ids: set[str],
) -> dict[str, Any]:
    if settings.aura_service_token is None:
        raise AuraIntegrationError("AURA service credentials are not configured.")

    request_body = {
        "message": (
            "Carefully interpret the supplied Flame image measurements. Return only cautious "
            "scientific statements supported by the provided context. Do not infer temperature, "
            "causality, or investigation-wide outcomes. Cite only supplied Flame evidence IDs; "
            "use hypothesized or unsupported when evidence is insufficient."
        ),
        "agent": "orchestrator",
        "plan": False,
        "use_knowledge": False,
        "use_memory": False,
        "use_tools": False,
        "require_local": settings.aura_require_local,
        "max_output_tokens": 400,
        "temperature": 0.0,
        "context": context[:16],
        "response_schema": AURA_RESPONSE_SCHEMA,
    }
    decoded = _post_chat(settings, request_body, idempotency_key=analysis_id)

    raw_statements = decoded["data"].get("statements")
    if not isinstance(raw_statements, list) or len(raw_statements) > 8:
        raise AuraIntegrationError("AURA returned an invalid statement list.")

    statements: list[dict[str, Any]] = []
    rejected = 0
    for item in raw_statements:
        if not isinstance(item, dict):
            rejected += 1
            continue
        text = item.get("text")
        claim_class = item.get("claim_class")
        evidence_ids = item.get("evidence_ids")
        if (
            not isinstance(text, str)
            or not text.strip()
            or len(text) > 1000
            or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", text)
            or re.search(r"\btemperature\b", text, re.IGNORECASE)
            or _UNSUPPORTED_OUTCOME.search(text)
            or not isinstance(claim_class, str)
            or claim_class not in {"inferred", "hypothesized", "unsupported"}
            or not isinstance(evidence_ids, list)
            or any(not isinstance(value, str) for value in evidence_ids)
            or any(value not in allowed_evidence_ids for value in evidence_ids)
            or (claim_class == "unsupported" and evidence_ids)
            or (claim_class == "inferred" and not evidence_ids)
        ):
            rejected += 1
            continue
        statements.append(
            {
                "text": text.strip(),
                "claim_class": claim_class,
                "evidence_ids": list(dict.fromkeys(evidence_ids)),
            }
        )

    return {
        "statements": statements,
        "rejected_statement_count": rejected,
        "model": decoded.get("model") if isinstance(decoded.get("model"), str) else None,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


AURA_CHAT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["answer", "evidence_ids"],
    "additionalProperties": False,
    "properties": {
        "answer": {"type": "string"},
        "evidence_ids": {"type": "array", "maxItems": 8, "items": {"type": "string"}},
    },
}
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def answer_question(
    settings: Settings,
    *,
    request_id: str,
    question: str,
    passages: list[dict[str, str]],
) -> dict[str, Any]:
    """Ask AURA to answer from Flame passages only, and keep only citations Flame supplied.

    The passages travel in ``context`` (AURA's DATA channel), never in ``message``, so document
    text cannot act as instructions. Tools stay off: Flame did the retrieval itself.
    """
    if settings.aura_service_token is None:
        raise AuraIntegrationError("AURA service credentials are not configured.")

    request_body = {
        "message": (
            "Answer the question below about NASA combustion research using ONLY the supplied Flame "
            "evidence. If the evidence does not answer it, say so plainly instead of guessing. "
            "Put the evidence_id of every passage you relied on in evidence_ids, copied exactly.\n\n"
            f"Question: {question}"
        ),
        "agent": "orchestrator",
        "plan": False,
        "use_knowledge": False,
        "use_memory": False,
        "use_tools": False,
        "require_local": settings.aura_require_local,
        "max_output_tokens": 500,
        "temperature": 0.0,
        "context": passages[:16],
        "response_schema": AURA_CHAT_SCHEMA,
    }
    decoded = _post_chat(settings, request_body, idempotency_key=request_id)

    data = decoded["data"]
    answer = data.get("answer")
    cited = data.get("evidence_ids")
    if (
        not isinstance(answer, str)
        or not answer.strip()
        or len(answer) > 4000
        or _CONTROL_CHARS.search(answer)
        or not isinstance(cited, list)
        or any(not isinstance(value, str) for value in cited)
    ):
        raise AuraIntegrationError("AURA returned an invalid answer.")

    allowed = {entry["id"] for entry in passages}
    valid = [value for value in dict.fromkeys(cited) if value in allowed]
    return {
        "answer": answer.strip(),
        "evidence_ids": valid,
        "dropped_citations": len(set(cited)) - len(valid),
        "provider": decoded.get("provider") if isinstance(decoded.get("provider"), str) else "aura",
        "model": decoded.get("model") if isinstance(decoded.get("model"), str) else "unknown",
        "cached": bool(decoded.get("cached")),
    }