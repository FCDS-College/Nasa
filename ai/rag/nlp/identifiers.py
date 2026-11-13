"""Rule-based identifier extraction. Confidence is 1.0 for an exact pattern match; there is no other outcome."""
from __future__ import annotations

import re

from ai.rag.nlp.records import ChunkInput, NlpRecord, span_record

# Order matters: an earlier pattern claims its span, so the generic experiment pattern never re-reads `TM-2008`.
_PATTERNS = (
    ("publication", "doi", re.compile(r"\b10\.\d{4,9}/[^\s\"<>]*[^\s\"<>.,;)]")),
    ("publication", "nasa_report", re.compile(r"\bNASA[/ ](?:TM|TP|CR|TN|SP)-(?:\d{4}-)?\d{4,9}\b")),
    ("publication", "ntrs", re.compile(r"\b(?:FF-)?NTRS[- :]*\d{11}\b")),
    ("dataset", "psi", re.compile(r"\b(?:FF-)?PSI-\d{1,4}\b")),
    # An experiment ID must follow a context word. A context-free `XX-0042` pattern measured on the committed NTRS PDFs
    # (284 pages) fired mostly on NASA-STD-6001, shuttle missions (STS-94), aircraft (KC-135) and conference IDs (IAC-12).
    ("experiment", "test_id", re.compile(
        r"\b(?i:run|test|experiment|sample|specimen)s?[ \t]+#?(?P<id>[A-Z][A-Z0-9]{1,9}-\d{2,5}[A-Z]?)\b")),
)


def _normalise(kind: str, text: str) -> str:
    if kind == "nasa_report":
        return re.sub(r"^NASA[/ ]", "NASA/", text)
    if kind == "ntrs":
        return "FF-NTRS-" + re.search(r"\d{11}", text).group(0)
    if kind == "psi":
        return re.sub(r"^FF-", "", text)
    if kind == "doi":
        return text.lower()
    return text


class IdentifierExtractor:
    name = "identifier-rules"
    version = "1.1.0"
    method = "rule"

    def extract(self, chunk: ChunkInput) -> list[NlpRecord]:
        taken: list[tuple[int, int]] = []
        records: list[NlpRecord] = []
        for record_type, kind, pattern in _PATTERNS:
            for match in pattern.finditer(chunk.text):
                start, end = match.span("id") if "id" in pattern.groupindex else match.span()
                if any(start < t_end and t_start < end for t_start, t_end in taken):
                    continue
                taken.append((start, end))
                records.append(span_record(self, chunk, record_type, start, end,
                                           normalized=_normalise(kind, chunk.text[start:end]), payload={"kind": kind}))
        return sorted(records, key=lambda r: r.char_start)
