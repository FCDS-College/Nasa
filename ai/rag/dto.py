from typing import Any

from pydantic import BaseModel, Field


class Locator(BaseModel):
    page: int | None = None
    section: str | None = None
    row: int | None = None


class RetrievalRequest(BaseModel):
    query: str
    top_k: int = Field(
        default=5,
        ge=1
    )
    filters: dict[str, Any] = Field(
        default_factory=dict
    )


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_version: str
    text: str
    score: float
    locator: Locator | None = None
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class EvidenceBundle(BaseModel):
    query: str

    evidence: list[RetrievedChunk] = Field(
        default_factory=list
    )

    context: str = ""

    citations: list[dict[str, Any]] = Field(
        default_factory=list
    )

    results: list[dict[str, Any]] = Field(
        default_factory=list
    )

    status: str = "ok"

    def is_sufficient(self):
        """
        Return True when the evidence bundle
        contains at least one retrieved chunk.
        """

        return (
            self.status == "ok"
            and len(self.evidence) > 0
        )

    @property
    def sources(self):
        """
        Backward-compatible access to evidence.
        """

        return [
            chunk.model_dump()
            for chunk in self.evidence
        ]

    def __getitem__(self, key):
        """
        Allow dictionary-style access while
        migrating the pipeline to DTOs.
        """

        if key == "query":
            return self.query

        if key == "status":
            return self.status

        if key == "context":
            return self.context

        if key == "sources":
            return self.sources

        if key == "results":
            return self.results

        if key == "citations":
            return self.citations

        raise KeyError(key)

    def __contains__(self, key):
        """
        Support expressions such as:

            "context" in result

        for backward compatibility with
        the previous dictionary response.
        """

        return key in {
            "query",
            "status",
            "context",
            "sources",
            "results",
            "citations"
        }
