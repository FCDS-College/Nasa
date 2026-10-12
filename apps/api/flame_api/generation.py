"""Grounded generation over Flame evidence, through the model router (M1, M3 boundary).

Flame owns the prompt, the response schema and the validation; the router decides which model
writes the text. Validation runs inside the routed call, so a provider that returns unusable
output counts as a failure and the next permitted provider gets the question instead.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from ai.providers.contracts.chat import ChatMessage, ChatRequest, Passage
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
from ai.providers.contracts.structured import StructuredRequest
from ai.routing import Router

INTERPRETATION_SCHEMA: dict[str, Any] = {
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


CHAT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["answer", "evidence_ids"],
    "additionalProperties": False,
    "properties": {
        "answer": {"type": "string"},
        "evidence_ids": {"type": "array", "maxItems": 8, "items": {"type": "string"}},
    },
}
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")



INTERPRETATION_INSTRUCTIONS = (
    "Carefully interpret the supplied Flame image measurements. Return only cautious "
    "scientific statements supported by the provided context. Do not infer temperature, "
    "causality, or investigation-wide outcomes. Cite only supplied Flame evidence IDs; "
    "use hypothesized or unsupported when evidence is insufficient."
)
CHAT_INSTRUCTIONS = (
    "Answer the question below about NASA combustion research using ONLY the supplied Flame "
    "evidence. If the evidence does not answer it, say so plainly instead of guessing. "
    "Put the evidence_id of every passage you relied on in evidence_ids, copied exactly."
)


def _invalid(provider: str, message: str) -> ProviderError:
    return ProviderError(ProviderErrorCode.INVALID_OUTPUT, message, provider=provider)


def _passages(entries: list[dict[str, str]]) -> tuple[Passage, ...]:
    return tuple(Passage(id=e["id"], text=e["text"], source=e.get("source", "")) for e in entries[:16])


def _validate_statements(data: dict[str, Any], allowed_evidence_ids: set[str], provider: str) -> tuple[list[dict], int]:
    raw_statements = data.get("statements")
    if not isinstance(raw_statements, list) or len(raw_statements) > 8:
        raise _invalid(provider, "The model returned an invalid statement list.")
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
        statements.append({"text": text.strip(), "claim_class": claim_class, "evidence_ids": list(dict.fromkeys(evidence_ids))})
    return statements, rejected


def interpret_analysis(
    router: Router,
    *,
    analysis_id: str,
    context: list[dict[str, str]],
    allowed_evidence_ids: set[str],
    require_local: bool | None = None,
) -> dict[str, Any]:
    options = {} if require_local is None else {"require_local": require_local}
    request = StructuredRequest(
        chat=ChatRequest(
            messages=(ChatMessage("system", INTERPRETATION_INSTRUCTIONS),),
            context=_passages(context), max_output_tokens=400, temperature=0.0,
            idempotency_key=analysis_id, options=options,
        ),
        schema=INTERPRETATION_SCHEMA,
    )

    def call(provider):
        response = provider.generate_structured(request)
        statements, rejected = _validate_statements(response.data, allowed_evidence_ids, provider.info.name)
        return response, statements, rejected

    routed = router.route("analysis.interpret", call)
    response, statements, rejected = routed.value
    return {
        "statements": statements,
        "rejected_statement_count": rejected,
        "provider": routed.metadata.provider,
        "model": response.model if response.model != "unknown" else None,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "execution": routed.metadata.to_dict(),
    }


def answer_question(
    router: Router,
    *,
    request_id: str,
    question: str,
    passages: list[dict[str, str]],
    require_local: bool | None = None,
) -> dict[str, Any]:
    """Answer from Flame passages only, and keep only citations Flame supplied.

    The passages travel as context (a DATA channel), never inside the question message, so
    document text cannot act as instructions.
    """
    options = {} if require_local is None else {"require_local": require_local}
    request = StructuredRequest(
        chat=ChatRequest(
            messages=(ChatMessage("system", CHAT_INSTRUCTIONS), ChatMessage("user", f"Question: {question}")),
            context=_passages(passages), max_output_tokens=500, temperature=0.0,
            idempotency_key=request_id, options=options,
        ),
        schema=CHAT_SCHEMA,
    )

    def call(provider):
        response = provider.generate_structured(request)
        answer = response.data.get("answer")
        cited = response.data.get("evidence_ids")
        if (
            not isinstance(answer, str)
            or not answer.strip()
            or len(answer) > 4000
            or _CONTROL_CHARS.search(answer)
            or not isinstance(cited, list)
            or any(not isinstance(value, str) for value in cited)
        ):
            raise _invalid(provider.info.name, "The model returned an invalid answer.")
        return response, answer, cited

    routed = router.route("chat.answer", call)
    response, answer, cited = routed.value
    allowed = {entry["id"] for entry in passages}
    valid = [value for value in dict.fromkeys(cited) if value in allowed]
    return {
        "answer": answer.strip(),
        "evidence_ids": valid,
        "dropped_citations": len(set(cited)) - len(valid),
        "provider": response.provider,
        "model": response.model,
        "cached": response.cached,
        "execution": routed.metadata.to_dict(),
    }
