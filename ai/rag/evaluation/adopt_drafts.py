"""Move AI-drafted passage gold cases into the gold set, but only the ones a named person accepts (annotation-guidelines §5.5).

    python -m ai.rag.evaluation.adopt_drafts --verifier "Their Name" --accept PG-001 PG-002 ...

A case becomes `verified` only through this command, by a verifier who is not its author and not an AI. The resulting file must still
pass `validate` (exact evidence text, document-disjoint splits, at least 25 % unanswerable); on any problem nothing is written, so accept
a mix of answerable and unanswerable cases together. Running it again never duplicates a case or changes an earlier verifier.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

from ai.rag.evaluation.passage_gold import PassageCase, load_passage_gold, validate

_AI_NAME = re.compile(r"claude|gpt|openai|anthropic|\bllm\b|\bai\b|assistant|\bbot\b", re.IGNORECASE)


def _to_json(case: PassageCase) -> str:
    return json.dumps({
        "gold_id": case.gold_id, "split": case.split, "question": case.question, "answerable": case.answerable,
        "evidence": [{"document_id": e.document_id, "page": e.page, "char_start": e.char_start, "char_end": e.char_end, "text": e.text}
                     for e in case.evidence],
        "question_type": case.question_type, "unanswerable_kind": case.unanswerable_kind, "author": case.author,
        "verified_by": list(case.verified_by), "status": case.status}, ensure_ascii=False)


def adopt(drafts: Path, target: Path, *, verifier: str, accept: list[str], page_texts: Mapping[tuple[str, int], str] | None = None,
          min_unanswerable_share: float = 0.25) -> dict:
    verifier = verifier.strip()
    if not verifier:
        raise ValueError("name the person who verified these cases")
    if _AI_NAME.search(verifier):
        raise ValueError(f"{verifier!r} looks like an AI: a verifier must be a person")
    by_id = {c.gold_id: c for c in load_passage_gold(drafts)}
    unknown = [i for i in accept if i not in by_id]
    if unknown:
        raise ValueError(f"no such draft: {', '.join(unknown)}")
    for gold_id in accept:
        if by_id[gold_id].author.strip().lower() == verifier.lower():
            raise ValueError(f"{gold_id}: the verifier cannot be the author ({verifier!r})")
    existing = load_passage_gold(target) if target.exists() else []
    have = {c.gold_id for c in existing}
    new = [replace(by_id[i], status="verified", verified_by=(verifier,)) for i in dict.fromkeys(accept) if i not in have]
    combined = [*existing, *new]
    problems = validate(combined, page_texts=page_texts, min_unanswerable_share=min_unanswerable_share) if combined else []
    if problems:
        raise ValueError("the resulting gold set would break the rules, nothing was written: " + "; ".join(problems))
    if new:
        target.write_text("\n".join(_to_json(c) for c in combined) + "\n", encoding="utf-8")
    return {"adopted": [c.gold_id for c in new], "already_adopted": [i for i in dict.fromkeys(accept) if i in have],
            "total_in_gold": len(combined)}


def main(argv: list[str]) -> int:
    from ai.rag.evaluation.propose_candidates import indexed_pages

    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verifier", required=True)
    parser.add_argument("--accept", nargs="+", required=True)
    parser.add_argument("--drafts", type=Path, default=root / "datasets" / "evaluation" / "passage_gold_v1_drafts.jsonl")
    parser.add_argument("--target", type=Path, default=root / "datasets" / "evaluation" / "passage_gold_v1.jsonl")
    parser.add_argument("--pdf-dir", type=Path, default=root / "docs" / "research")
    args = parser.parse_args(argv)
    pages = {(f"FF-NTRS-{path.stem}", page["page"]): page["verbatim"]
             for path in sorted(args.pdf_dir.glob("*.pdf")) for page in indexed_pages(path)}
    try:
        print(json.dumps(adopt(args.drafts, args.target, verifier=args.verifier, accept=args.accept, page_texts=pages)))
    except ValueError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
