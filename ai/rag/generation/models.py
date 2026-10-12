from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

CLAIM_LABELS = ("observed", "measured", "estimated", "inferred", "hypothesized")

STATUS_ANSWERED = "answered"
STATUS_PARTIAL = "partially_supported"
STATUS_INSUFFICIENT = "insufficient_evidence"
STATUS_CONFLICTING = "conflicting_evidence"


class Claim(BaseModel):
    text: str
    label: str
    evidence_ids: list[str]
    citation_ids: list[str] = Field(default_factory=list)


class GroundedAnswer(BaseModel):
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
        return self.status in (STATUS_INSUFFICIENT, STATUS_CONFLICTING)
