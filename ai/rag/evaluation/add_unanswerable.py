"""Add person-written unanswerable questions to the passage gold drafts (annotation-guidelines §5.3).

    python -m ai.rag.evaluation.add_unanswerable --author "Your Name" --file my_questions.txt [--check-only]

`my_questions.txt` has one question per line. A line starting with `OOD:` is an out-of-domain question (chocolate cake); any other line is
an in-domain question the reports should not answer, the kind that matters most. Each becomes a `draft` authored by you, in
`passage_gold_v1_drafts.jsonl`; **you cannot verify them yourself**: another person adopts them with `adopt_drafts`.

For every question the tool prints how many pages of the committed reports contain each of its distinctive words and the closest pages by
those words, so you can see whether the reports really leave it unanswered. It is a lexical aid: read the closest pages yourself.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

from ai.rag.evaluation.adopt_drafts import _AI_NAME, _to_json
from ai.rag.evaluation.passage_gold import PassageCase, load_passage_gold
from ai.rag.evaluation.verification_sheet import competing_pages
from ai.rag.retrieval.evidence_window import question_terms

KINDS = ("in_domain_not_in_corpus", "out_of_domain")
SPLITS = ("dev", "validation", "holdout")
MIN_QUESTION_CHARS = 10
_WORD = re.compile(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*")


def absence_report(question: str, pages: Mapping[tuple[str, int], str], *, limit: int = 3) -> dict:
    """How many pages contain each distinctive word of the question, which words occur nowhere, and the closest pages by those words."""
    terms = sorted(question_terms(question))
    tokens = {key: set(_WORD.findall(text.lower())) for key, text in pages.items()}
    counts = Counter({term: sum(term in page_tokens for page_tokens in tokens.values()) for term in terms})
    probe = PassageCase.from_dict({"gold_id": "PG-000", "split": "dev", "question": question, "answerable": False, "evidence": [],
                                   "question_type": "other", "unanswerable_kind": "in_domain_not_in_corpus", "author": "x",
                                   "verified_by": [], "status": "draft"})
    return {"term_pages": {term: counts[term] for term in terms}, "absent_terms": sorted(t for t in terms if counts[t] == 0),
            "closest_pages": competing_pages(probe, pages, limit=limit), "pages_searched": len(pages)}


def add_unanswerable(drafts: Path, *, author: str, questions: Sequence[str], kind_of: Mapping[str, str] | None = None,
                     default_kind: str = "in_domain_not_in_corpus") -> list[str]:
    author = author.strip()
    if not author:
        raise ValueError("name the person who wrote these questions")
    if _AI_NAME.search(author):
        raise ValueError(f"{author!r} looks like an AI: these questions must be written by a person")
    existing = load_passage_gold(drafts) if drafts.exists() else []
    seen = {c.question.strip().lower() for c in existing}
    cleaned: list[str] = []
    for question in (q.strip() for q in questions):
        if len(question) < MIN_QUESTION_CHARS:
            raise ValueError(f"question too short ({len(question)} characters, at least {MIN_QUESTION_CHARS}): {question!r}")
        if question.lower() in seen:
            raise ValueError(f"duplicate question: {question!r}")
        seen.add(question.lower())
        cleaned.append(question)
    kinds = dict(kind_of or {})
    bad = [k for k in [*kinds.values(), default_kind] if k not in KINDS]
    if bad:
        raise ValueError(f"unanswerable_kind must be one of {KINDS}, got {bad[0]!r}")
    number = max((int(c.gold_id.split("-")[1]) for c in existing), default=0)
    start = sum(not c.answerable for c in existing)
    lines, added = [], []
    for offset, question in enumerate(cleaned):
        number += 1
        gold_id = f"PG-{number:03d}"
        case = PassageCase.from_dict({"gold_id": gold_id, "split": SPLITS[(start + offset) % len(SPLITS)], "question": question,
                                      "answerable": False, "evidence": [], "question_type": "other",
                                      "unanswerable_kind": kinds.get(question, default_kind), "author": author, "verified_by": [],
                                      "status": "draft"})
        lines.append(_to_json(case))
        added.append(gold_id)
    if lines:
        with drafts.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    return added


def _load_pages(pdf_dir: Path) -> dict[tuple[str, int], str]:
    from ai.rag.evaluation.propose_candidates import indexed_pages

    return {(f"FF-NTRS-{path.stem}", page["page"]): page["verbatim"] for path in sorted(pdf_dir.glob("*.pdf")) for page in indexed_pages(path)}


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--author", required=True)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--drafts", type=Path, default=root / "datasets" / "evaluation" / "passage_gold_v1_drafts.jsonl")
    parser.add_argument("--pdf-dir", type=Path, default=root / "docs" / "research")
    parser.add_argument("--check-only", action="store_true", help="print the absence report and write nothing")
    args = parser.parse_args(argv)
    kind_of, questions = {}, []
    for line in args.file.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.strip().upper().startswith("OOD:"):
            question = line.split(":", 1)[1].strip()
            kind_of[question] = "out_of_domain"
        else:
            question = line.strip()
        questions.append(question)
    pages = _load_pages(args.pdf_dir)
    for question in questions:
        report = absence_report(question, pages)
        print(f"\n{question}")
        if question in kind_of:
            print("  (out of domain)")
            continue
        print("  pages containing each word: " + ", ".join(f"{t}={n}" for t, n in report["term_pages"].items()))
        print("  words in no page: " + (", ".join(report["absent_terms"]) or "none: read the closest pages carefully"))
        for doc, page, snippet in report["closest_pages"]:
            print(f"  closest: {doc} p{page}: {snippet[:140]}")
    if args.check_only:
        return 0
    try:
        print(json.dumps({"added": add_unanswerable(args.drafts, author=args.author, questions=questions, kind_of=kind_of)}))
    except ValueError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
