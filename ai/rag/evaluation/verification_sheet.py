"""A sheet for the person who verifies AI-drafted passage gold cases (annotation-guidelines §5.5).

    python -m ai.rag.evaluation.verification_sheet --out datasets/evaluation/passage_gold_v1_verification.csv

One row per draft: the question, the evidence it cites (document, page, text), and **competing pages**: other pages of the corpus that share
the question's distinctive terms. A question is only a fair test if the cited page is the one that answers it; the competing pages are
where an equally good answer would hide; `same_figures_on` lists other pages that contain a figure (number with unit) of the cited passage. Empty columns for the verifier: `answers_question`, `unique`, `question_clear`, `notes`.
The competing-page ranking is a lexical aid for a human, not a judgement.
"""
from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import IO, Sequence

from ai.rag.evaluation.passage_gold import PassageCase, load_passage_gold
from ai.rag.retrieval.evidence_window import best_window, question_terms

COLUMNS = ["gold_id", "split", "answerable", "unanswerable_kind", "question", "evidence", "same_figures_on", "competing_pages",
           "answers_question", "unique", "question_clear", "notes"]
_WORD = re.compile(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*")
SNIPPET_CHARS = 160


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def competing_pages(case: PassageCase, pages: Mapping[tuple[str, int], str], *, limit: int = 3) -> list[tuple[str, int, str]]:
    """(document, page, best-window snippet) of the pages, other than the cited ones, that match most of the question's terms."""
    terms = question_terms(case.question)
    if not terms or not pages:
        return []
    page_tokens = {key: _tokens(text) for key, text in pages.items()}
    frequency = Counter(term for tokens in page_tokens.values() for term in terms if term in tokens)
    idf = {term: math.log(1 + len(pages) / (1 + frequency[term])) for term in terms}
    cited = {(e.document_id, e.page) for e in case.evidence}
    scored = sorted(((sum(idf[t] for t in terms if t in tokens), key) for key, tokens in page_tokens.items() if key not in cited),
                    key=lambda item: (-item[0], item[1]))
    return [(doc, page, " ".join(best_window(pages[(doc, page)], case.question)[:SNIPPET_CHARS].split()))
            for score, (doc, page) in scored[:limit] if score > 0]


def same_figures_on(case: PassageCase, pages: Mapping[tuple[str, int], str]) -> list[tuple[str, int, str]]:
    """Other pages that contain a figure (number with unit) found in the cited passage: where the same answer may also be written."""
    from ai.rag.nlp.quantities import MeasurementExtractor
    from ai.rag.nlp.records import ChunkInput

    found = []
    for ev in case.evidence:
        figures = {r.text for r in MeasurementExtractor().extract(ChunkInput("g", ev.document_id, "v1", ev.page, ev.text))}
        for (doc, page), text in sorted(pages.items()):
            if (doc, page) != (ev.document_id, ev.page):
                shared = sorted(f for f in figures if f in text)
                if shared:
                    found.append((doc, page, ", ".join(shared)))
    return found


def sheet_rows(cases: Sequence[PassageCase], pages: Mapping[tuple[str, int], str]) -> list[dict]:
    rows = []
    for case in cases:
        rows.append({
            "gold_id": case.gold_id, "split": case.split, "answerable": "yes" if case.answerable else "no",
            "unanswerable_kind": case.unanswerable_kind or "", "question": case.question,
            "evidence": " | ".join(f"{e.document_id} p{e.page}: {' '.join(e.text.split())}" for e in case.evidence),
            "same_figures_on": " | ".join(f"{d} p{p}: {figures}" for d, p, figures in same_figures_on(case, pages)),
            "competing_pages": " | ".join(f"{d} p{p}: {snippet}" for d, p, snippet in competing_pages(case, pages)),
            "answers_question": "", "unique": "", "question_clear": "", "notes": "",
        })
    return rows


def write_csv(rows: Sequence[dict], handle: IO[str]) -> None:
    writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)


def main(argv: list[str]) -> int:
    from ai.rag.evaluation.propose_candidates import indexed_pages

    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--drafts", type=Path, default=root / "datasets" / "evaluation" / "passage_gold_v1_drafts.jsonl")
    parser.add_argument("--pdf-dir", type=Path, default=root / "docs" / "research")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    pages = {(f"FF-NTRS-{path.stem}", page["page"]): page["verbatim"]
             for path in sorted(args.pdf_dir.glob("*.pdf")) for page in indexed_pages(path)}
    rows = sheet_rows(load_passage_gold(args.drafts), pages)
    with (args.out.open("w", encoding="utf-8", newline="") if args.out else sys.stdout) as handle:
        write_csv(rows, handle)
    print(f"{len(rows)} drafts, {len(pages)} pages", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
