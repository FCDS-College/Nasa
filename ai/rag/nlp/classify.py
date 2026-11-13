"""Rule-based document classification and first-page metadata. Cue order is the tie-break (documented in the tests)."""
from __future__ import annotations

import re

from ai.rag.nlp.identifiers import IdentifierExtractor
from ai.rag.nlp.records import ChunkInput, NlpRecord, span_record

_CUES = (
    ("technical_report", re.compile(r"NASA[/ ](?:TM|TP|CR|TN|SP)-|Technical (?:Memorandum|Paper|Publication)|Contractor Report")),
    ("conference_paper", re.compile(r"Proceedings|Workshop|Symposium|Conference")),
    ("journal_article", re.compile(r"Journal of|doi:?\s*10\.", re.IGNORECASE)),
    ("dataset_documentation", re.compile(r"Investigation Identifier|Study Identifier")),
)
_YEAR = re.compile(r"\b(19[5-9]\d|20[0-3]\d)\b")
_ABSTRACT = re.compile(r"(?ims)^[ \t]*Abstract[ \t]*[:.\-]?[ \t]*\n?(?P<body>.+?)(?=\n[ \t]*\n|\Z)")


class DocumentClassifier:
    name = "doctype-rules"
    version = "1.0.0"
    method = "rule"

    def extract(self, chunk: ChunkInput) -> list[NlpRecord]:
        if chunk.page != 1:
            return []
        hits = [(label, m) for label, pattern in _CUES if (m := pattern.search(chunk.text))]
        if not hits:
            return []
        label, match = hits[0]
        return [span_record(self, chunk, "document_class", match.start(), match.end(), normalized=label,
                            confidence=1.0 if len(hits) == 1 else 0.5, payload={"labels_matched": [h[0] for h in hits]})]


class MetadataExtractor:
    name = "metadata-rules"
    version = "1.0.0"
    method = "rule"

    def extract(self, chunk: ChunkInput) -> list[NlpRecord]:
        if chunk.page != 1:
            return []
        records = []
        report = next((r for r in IdentifierExtractor().extract(chunk) if r.payload.get("kind") == "nasa_report"), None)
        if report is not None:
            records.append(span_record(self, chunk, "metadata_field", report.char_start, report.char_end,
                                       normalized=report.normalized, payload={"field": "report_number"}))
        if (year := _YEAR.search(chunk.text)):
            records.append(span_record(self, chunk, "metadata_field", year.start(), year.end(), normalized=year.group(0),
                                       confidence=0.5, payload={"field": "year", "basis": "first year-like token on page 1"}))
        if (abstract := _ABSTRACT.search(chunk.text)):
            records.append(span_record(self, chunk, "metadata_field", abstract.start("body"), abstract.end("body"),
                                       normalized=None, payload={"field": "abstract"}))
        return records
