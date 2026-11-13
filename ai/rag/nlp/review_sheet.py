"""A review sheet for the D1 seed vocabularies (`ai/rag/nlp/vocab/*.json`).

    python -m ai.rag.nlp.review_sheet docs/research --out docs/data/vocabulary-review-2026-11-13.csv

One row per vocabulary entry: what it matches in the committed NTRS PDFs (hit count, documents, the surface forms actually matched) and
a few matches in context, with empty `decision`, `correction` and `notes` columns for the domain expert. The seeds are unreviewed until
someone fills those columns in; the sheet only makes that review fast. Entries the corpus never mentions are flagged, not dropped: a
term can be right and still absent from 24 reports.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path
from typing import IO, Sequence

from ai.rag.nlp.records import ChunkInput
from ai.rag.nlp.vocab import VocabularyExtractor, load_vocabulary, vocabulary_version

COLUMNS = ["type", "canonical", "hits", "documents", "surface_forms", "contexts", "flag", "decision", "correction", "notes"]
CONTEXT_CHARS = 60


def _context(text: str, start: int, end: int) -> str:
    left, right = text[max(0, start - CONTEXT_CHARS):start], text[end:end + CONTEXT_CHARS]
    return " ".join(f"{left}[{text[start:end]}]{right}".split())


def review_rows(vocabulary: dict, pages: Sequence[dict], *, contexts: int = 3) -> list[dict]:
    extractor = VocabularyExtractor(vocabulary, version=vocabulary_version(vocabulary))
    forms: dict[tuple[str, str], Counter] = {}
    docs: dict[tuple[str, str], set] = {}
    shown: dict[tuple[str, str], list[str]] = {}
    for page in pages:
        chunk = ChunkInput(f"{page['doc']}:{page['page']}", page["doc"], "v1", page["page"], page["text"])
        for record in extractor.extract(chunk):
            key = (record.record_type, record.normalized)
            forms.setdefault(key, Counter())[record.text] += 1
            docs.setdefault(key, set()).add(page["doc"])
            if len(shown.setdefault(key, [])) < contexts:
                shown[key].append(f"{page['doc']} p{page['page']}: {_context(page['text'], record.char_start, record.char_end)}")
    rows = []
    for record_type, entries in sorted(vocabulary.items()):
        for canonical in sorted(entries):
            key = (record_type, canonical)
            counter = forms.get(key, Counter())
            hits = sum(counter.values())
            rows.append({
                "type": record_type, "canonical": canonical, "hits": hits, "documents": len(docs.get(key, ())),
                "surface_forms": "; ".join(f"{form} x{n}" for form, n in sorted(counter.items(), key=lambda item: (-item[1], item[0]))),
                "contexts": " | ".join(shown.get(key, [])), "flag": "" if hits else "no hits in this corpus",
                "decision": "", "correction": "", "notes": "",
            })
    return rows


def write_csv(rows: Sequence[dict], handle: IO[str]) -> None:
    writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)


def main(argv: list[str]) -> int:
    from ai.rag.evaluation.propose_candidates import indexed_pages

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pdf_dir", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    pages = [{"doc": f"FF-NTRS-{path.stem}", "page": page["page"], "text": page["indexed"]}
             for path in sorted(args.pdf_dir.glob("*.pdf")) for page in indexed_pages(path)]
    rows = review_rows(load_vocabulary(), pages)
    with (args.out.open("w", encoding="utf-8", newline="") if args.out else sys.stdout) as handle:
        write_csv(rows, handle)
    print(f"{len(rows)} entries, {sum(1 for r in rows if r['hits'] == 0)} with no hits, {len(pages)} pages", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
