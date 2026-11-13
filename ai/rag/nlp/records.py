"""Source-linked NLP records (D1, docs/ai/nlp-pipeline.md §4). Pure Python: no storage or model imports."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, Field, model_validator

REVIEW_STATUSES = ("machine_extracted", "human_verified", "rejected", "superseded")


@dataclass(frozen=True, slots=True)
class ChunkInput:
    """One retrievable chunk. Every record's offsets are relative to `text`."""

    chunk_id: str
    document_id: str
    document_version: str
    page: int | None
    text: str


class NlpRecord(BaseModel):
    """A candidate extraction. `record_type` is the spec's `type` (renamed: D-9)."""

    record_type: str
    text: str
    normalized: str | None = None
    document_id: str
    document_version: str
    page: int | None = None
    char_start: int
    char_end: int
    chunk_id: str
    extractor: str
    extractor_version: str
    method: Literal["rule", "model", "llm"]
    confidence: float
    review_status: str = "machine_extracted"
    payload: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> NlpRecord:
        if not self.chunk_id or not self.document_id:
            raise ValueError("a record needs the chunk and document it came from")
        if self.char_start < 0 or self.char_end <= self.char_start:
            raise ValueError("a record needs a non-empty source span")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        if self.review_status not in REVIEW_STATUSES:
            raise ValueError(f"review_status must be one of {REVIEW_STATUSES}")
        return self

    @property
    def record_id(self) -> str:
        """Stable per (extractor, version, chunk, type, span); a new extractor version is a new record."""
        key = "|".join((self.extractor, self.extractor_version, self.chunk_id, self.record_type,
                        str(self.char_start), str(self.char_end)))
        return "nr_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


class Extractor(Protocol):
    name: str
    version: str
    method: str

    def extract(self, chunk: ChunkInput) -> list[NlpRecord]: ...


def span_record(extractor: Extractor, chunk: ChunkInput, record_type: str, start: int, end: int, *,
                normalized: str | None = None, confidence: float = 1.0, payload: dict | None = None) -> NlpRecord:
    return NlpRecord(
        record_type=record_type, text=chunk.text[start:end], normalized=normalized, document_id=chunk.document_id,
        document_version=chunk.document_version, page=chunk.page, char_start=start, char_end=end, chunk_id=chunk.chunk_id,
        extractor=extractor.name, extractor_version=extractor.version, method=extractor.method, confidence=confidence,
        payload=payload or {},
    )


def run_extractors(chunk: ChunkInput, extractors: list[Extractor]) -> tuple[list[NlpRecord], dict[str, int]]:
    """Run every extractor; keep only records whose span really is in this chunk, and count the rest."""
    kept: list[NlpRecord] = []
    dropped: dict[str, int] = {}
    for extractor in extractors:
        for record in extractor.extract(chunk):
            if record.chunk_id != chunk.chunk_id or chunk.text[record.char_start:record.char_end] != record.text:
                dropped[extractor.name] = dropped.get(extractor.name, 0) + 1
                continue
            kept.append(record)
    return kept, dropped
