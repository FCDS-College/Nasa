"""A worklist for annotators: passages worth writing a question about. It proposes; it never produces gold.

    python -m ai.rag.evaluation.propose_candidates --pdf-dir docs/research --out worklist.jsonl --per-document 5

For each page of each PDF, sentences that contain a measurement (a number with a unit: the facts a value-lookup or
condition question is about) are proposed with their exact character span in the page text the pipeline sees
(PyMuPDF `get_text("text")`, stripped, as `flame_api.ingest` stores it). An annotator reads the passage, writes a question
that it answers without quoting it, and records the case in `passage_gold_v1.jsonl` as a `draft`; a second person verifies it.
Unanswerable questions cannot be proposed this way: they must be written by a person (annotation-guidelines §5).

Needs PyMuPDF (the `ingestion` extra). No model is used.
"""
from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterator
from pathlib import Path

from ai.rag.nlp.quantities import MeasurementExtractor
from ai.rag.nlp.records import ChunkInput

ROOT = Path(__file__).resolve().parents[3]
_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n[ \t]*\n")
_FUNCTION_WORDS = frozenset({"the", "of", "and", "in", "to", "a", "is", "for", "with", "on", "at", "by", "was", "that", "are", "from", "as", "be",
                             "this", "were"})


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """Non-overlapping (start, end) spans of the sentences of `text`, trimmed of surrounding whitespace."""
    spans: list[tuple[int, int]] = []

    def add(start: int, end: int) -> None:
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if end > start:
            spans.append((start, end))

    start = 0
    for match in _BOUNDARY.finditer(text):
        add(start, match.start())
        start = match.end()
    add(start, len(text))
    return spans


def candidate_passages(page_text: str) -> list[dict]:
    """Sentences containing at least one measurement, with offsets into `page_text`."""
    extractor = MeasurementExtractor()
    rows = []
    for start, end in sentence_spans(page_text):
        sentence = page_text[start:end]
        found = extractor.extract(ChunkInput("candidate", "candidate", "v1", None, sentence))
        if found:
            rows.append({"char_start": start, "char_end": end, "text": sentence, "measurements": [r.text for r in found], "status": "proposal"})
    return rows


def _looks_garbled(text: str) -> bool:
    """A broken PDF font map extracts as non-language (same idea as `flame_api.ingest.text_layer_is_garbled`)."""
    tokens = re.findall(r"[A-Za-z]+", text.lower())
    return len(tokens) >= 40 and sum(t in _FUNCTION_WORDS for t in tokens) / len(tokens) < 0.03


def propose(pdf_dir: Path, *, per_document: int | None = None) -> Iterator[dict]:
    try:
        import fitz   # PyMuPDF: the same extractor production ingest uses, so offsets match the stored page text
    except ImportError:
        raise SystemExit("PyMuPDF is required to read PDFs: pip install 'pymupdf>=1.24,<2' (the `ingestion` extra of apps/api)") from None
    for path in sorted(Path(pdf_dir).glob("*.pdf")):
        document_id = f"FF-NTRS-{path.stem}"
        emitted = 0
        for number, page in enumerate(fitz.open(path), start=1):
            text = page.get_text("text").replace("\x00", "").strip()
            if len(text) < 12 or _looks_garbled(text):
                continue
            for row in candidate_passages(text):
                if per_document is not None and emitted >= per_document:
                    break
                emitted += 1
                yield {"document_id": document_id, "page": number, **row}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pdf-dir", type=Path, default=ROOT / "docs" / "research")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--per-document", type=int, default=None, help="at most this many proposals per PDF")
    args = parser.parse_args()
    rows = list(propose(args.pdf_dir, per_document=args.per_document))
    args.out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""), encoding="utf-8")
    print(f"{len(rows)} proposals from {len({r['document_id'] for r in rows})} documents -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
