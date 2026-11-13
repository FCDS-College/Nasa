"""Table and figure captions, references to them, and caption association inside one document."""
from __future__ import annotations

import re

from ai.rag.nlp.records import ChunkInput, NlpRecord, span_record

_CAPTION = re.compile(r"(?m)^[ \t]*(?P<cap>(?P<kind>Table|Figure|Fig\.)[ \t]+(?P<label>\d+[A-Za-z]?)[ \t]*[.:–-][^\n]*)")
_REFERENCE = re.compile(r"\b(?P<kind>Tables?|Figures?|Figs?\.)[ \t]+(?P<label>\d+[A-Za-z]?)")


def _kind(word: str) -> str:
    return "table" if word.lower().startswith("table") else "figure"


class FigureTableExtractor:
    name = "figure-table-rules"
    version = "1.0.0"
    method = "rule"

    def extract(self, chunk: ChunkInput) -> list[NlpRecord]:
        records, caption_spans = [], []
        for match in _CAPTION.finditer(chunk.text):
            kind = _kind(match["kind"])
            start, end = match.start("cap"), match.end("cap")
            caption_spans.append((start, end))
            records.append(span_record(self, chunk, f"{kind}_caption", start, end, normalized=f"{kind}:{match['label'].lower()}"))
        for match in _REFERENCE.finditer(chunk.text):
            if any(s <= match.start() < e for s, e in caption_spans):
                continue
            kind = _kind(match["kind"])
            records.append(span_record(self, chunk, f"{kind}_reference", match.start(), match.end(),
                                       normalized=f"{kind}:{match['label'].lower()}"))
        return sorted(records, key=lambda r: r.char_start)


def associate_captions(records: list[NlpRecord]) -> list[NlpRecord]:
    captions: dict[tuple[str, str], list[NlpRecord]] = {}
    for record in sorted(records, key=lambda r: (r.page or 0, r.char_start)):
        if record.record_type.endswith("_caption"):
            captions.setdefault((record.document_id, record.normalized), []).append(record)
    out = []
    for record in records:
        if record.record_type.endswith("_reference"):
            found = captions.get((record.document_id, record.normalized))
            if found:
                payload = {**record.payload, "caption_record_id": found[0].record_id,
                           "caption_chunk_id": found[0].chunk_id, "ambiguous": len(found) > 1}
                record = record.model_copy(update={"payload": payload})
        out.append(record)
    return out
