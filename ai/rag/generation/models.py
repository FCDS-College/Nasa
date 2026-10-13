from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

CLAIM_LABELS = ("observed", "measured", "estimated", "inferred", "hypothesized")

STATUS_ANSWERED = "answered"
STATUS_PARTIAL = "partially_supported"
STATUS_INSUFFICIENT = "insufficient_evidence"
STATUS_CONFLICTING = "conflicting_evidence"


class Claim(BaseModel):
    """One validated statement: text, label (one of CLAIM_LABELS), evidence_ids (retrieved chunk ids) and citation_ids (C1, C2, ...)."""
    text: str
    label: str
    evidence_ids: list[str]
    citation_ids: list[str] = Field(default_factory=list)


class GroundedAnswer(BaseModel):
    """Final answer object.

    status is one of answered, partially_supported, insufficient_evidence, conflicting_evidence. Holds the rebuilt answer text, claims, citations, warnings, dropped citation ids, abstention reason, memory ids used and the prompt/model versions."""

    question: str
    status: str
    answer: str = ""
    claims: list[Claim] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    dropped_citation_ids: list[str] = Field(default_factory=list)
    abstention_reason: str | None = None
    memory_used: list[str] = Field(default_factory=list)
    versions: dict[str, str] = Field(default_factory=dict)

    @property
    def abstained(self) -> bool:
        """True when status is insufficient_evidence or conflicting_evidence."""
        return self.status in (STATUS_INSUFFICIENT, STATUS_CONFLICTING)
