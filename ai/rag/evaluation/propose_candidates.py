"""A worklist for annotators: passages worth writing a question about. It proposes; it never produces gold.

    python -m ai.rag.evaluation.propose_candidates --pdf-dir docs/research --out worklist.jsonl --per-document 5
    python -m ai.rag.evaluation.propose_candidates --show docs/research/20080034883.pdf --page 3 [--verbatim]

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

from ai.rag.ingestion.normalize import normalize_document
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


def _fitz():
    try:
        import fitz   # PyMuPDF: the same extractor production ingest uses, so offsets match the stored page text
    except ImportError:
        raise SystemExit("PyMuPDF is required to read PDFs: pip install 'pymupdf>=1.24,<2' (the `ingestion` extra of apps/api)") from None
    return fitz


def indexed_pages(pdf_path: Path) -> list[dict]:
    """The pages production ingest would keep, as `{"page", "verbatim", "indexed"}`.

    `verbatim` is the page text exactly as extracted: it is the evidence excerpt a citation points at, and the text that
    passage-level gold spans refer to. `indexed` is what search and the NLP extractors see (ligatures folded, hyphen splits
    rejoined, running headers and page numbers removed, stacked words joined). Annotate NLP spans on `indexed`.
    """
    pages = []
    for number, page in enumerate(_fitz().open(pdf_path), start=1):
        text = page.get_text("text").replace("\x00", "").strip()
        if len(text) >= 12 and not _looks_garbled(text):
            pages.append((number, text))
    return [{"page": number, "verbatim": text, "indexed": indexed}
            for (number, text), indexed in zip(pages, normalize_document([text for _, text in pages]))]


def propose(pdf_dir: Path, *, per_document: int | None = None) -> Iterator[dict]:
    fitz = _fitz()
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
    parser.add_argument("--out", type=Path)
    parser.add_argument("--per-document", type=int, default=None, help="at most this many proposals per PDF")
    parser.add_argument("--show", type=Path, help="print the text of one page of this PDF instead of writing a worklist")
    parser.add_argument("--page", type=int, help="with --show: the page number")
    parser.add_argument("--verbatim", action="store_true", help="with --show: the text as extracted instead of the indexed text")
    args = parser.parse_args()
    if args.show:
        page = next((p for p in indexed_pages(args.show) if p["page"] == args.page), None)
        if page is None:
            raise SystemExit(f"page {args.page} of {args.show} is not indexed (blank, garbled or out of range)")
        print(page["verbatim" if args.verbatim else "indexed"])
        return 0
    if args.out is None:
        parser.error("--out is required unless --show is used")
    rows = list(propose(args.pdf_dir, per_document=args.per_document))
    args.out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""), encoding="utf-8")
    print(f"{len(rows)} proposals from {len({r['document_id'] for r in rows})} documents -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
