"""Score the verified passage gold set through the live /api/search, compare two runs, calibrate an abstention threshold.

    FLAME_API_ORIGIN=http://localhost:8000 FLAME_READ_API_TOKEN=... python -m ai.rag.evaluation.run_passage_gold run --label baseline --out baseline.json
    (restart the API with FLAME_LEXICAL_MODE=or_idf, or FLAME_DENSE_GRANULARITY=window, run again with another label)
    python -m ai.rag.evaluation.run_passage_gold compare baseline.json or_idf.json
    python -m ai.rag.evaluation.run_passage_gold run --mode chat --label chat --out chat.json && python -m ai.rag.evaluation.run_passage_gold calibrate chat.json

It reads `datasets/evaluation/passage_gold_v1.jsonl` and uses **only verified cases** (`verified_cases`: verified by someone other than the author).
It refuses to report below 20 verified answerable cases (and calibration below 8 verified unanswerable ones): fewer would be mostly noise.
Retrieval is page-level: the right document on the wrong page is a miss. Every number carries a 95 % bootstrap interval; a difference between
two runs is paired over the same questions and is "shown" only if its interval excludes 0. Stdlib HTTP, like `flame_retrieval_benchmark`.

`--mode document` (default) searches documents only, as the benchmark does. `--mode chat` sends exactly what `/api/chat` sends first
(`q`, `page_size=5`), so the top score is the one an abstention gate on the chat path would see. That score is the fused rank score of
`/api/search` (agreement of the lexical and dense legs), not a relevance probability and not the reranker's score.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path

from ai.rag.evaluation.passage_gold import MIN_VERIFIED_FOR_REPORT, PassageCase, load_passage_gold, retrieval_report, validate, verified_cases
from ai.rag.evaluation.stats import compare_reports

ROOT = Path(__file__).resolve().parents[3]
GOLD = ROOT / "datasets" / "evaluation" / "passage_gold_v1.jsonl"
MIN_UNANSWERABLE_FOR_CALIBRATION = 8
RANK_DEPTH = 10
Fetch = Callable[[str], dict]


def rankings_from_body(body: dict) -> list[tuple[str, int]]:
    """(source_id, page) of the hits, best first; a repeated page counts once and a hit without a page is dropped."""
    seen: list[tuple[str, int]] = []
    for hit in body.get("results", []):
        source_id = (hit.get("source") or {}).get("source_id")
        page = (hit.get("locator") or {}).get("page")
        if source_id and isinstance(page, int) and (source_id, page) not in seen:
            seen.append((source_id, page))
    return seen


def _top_score(body: dict) -> float:
    scores = [hit["score"] for hit in body.get("results", []) if isinstance(hit.get("score"), (int, float))]
    return float(max(scores)) if scores else 0.0


def run(cases: Sequence[PassageCase], fetch: Fetch, *, label: str) -> dict:
    scored = verified_cases(list(cases))
    answerable = [c for c in scored if c.answerable]
    unanswerable = [c for c in scored if not c.answerable]
    if len(answerable) < MIN_VERIFIED_FOR_REPORT:
        raise ValueError(f"need at least {MIN_VERIFIED_FOR_REPORT} verified answerable cases, have {len(answerable)}")
    problems = validate(list(cases))
    if problems:      # e.g. too few unanswerable cases after a staged adoption: the set must be complete before it is scored
        raise ValueError("the gold file breaks its own rules, so it is not scored: " + "; ".join(problems[:4]))
    rankings: dict[str, list[tuple[str, int]]] = {}
    per_question, modes, reranking = [], set(), set()
    for case in [*answerable, *unanswerable]:
        body = fetch(case.question)
        ranked = rankings_from_body(body)
        modes.add((body.get("retrieval") or {}).get("mode"))
        reranking.add(((body.get("retrieval") or {}).get("reranking") or {}).get("status"))
        entry = {"id": case.gold_id, "answerable": case.answerable, "split": case.split, "top_score": _top_score(body),
                 "n_results": len(body.get("results", []))}
        if case.answerable:
            rankings[case.gold_id] = ranked
            wanted = {(e.document_id, e.page) for e in case.evidence}
            first = next((i for i, hit in enumerate(ranked[:RANK_DEPTH], start=1) if hit in wanted), None)
            entry.update({"first_relevant_rank": first, "hit@1": float(first == 1), "hit@5": float(first is not None and first <= 5),
                          "rr@10": 0.0 if first is None else 1.0 / first})
        per_question.append(entry)
    return {"label": label, "gold_set": "passage_gold_v1.jsonl", "n_answerable": len(answerable), "n_unanswerable": len(unanswerable),
            "retrieval_modes_reported": sorted(m for m in modes if m), "reranking_statuses": sorted(s for s in reranking if s),
            "retrieval": retrieval_report(answerable, rankings), "per_question": per_question}


def compare_runs(report_a: dict, report_b: dict, *, metric: str = "rr@10", seed: int = 0) -> dict:
    """Paired difference b - a over the answerable questions both runs scored. `difference_shown` is True only if the 95 % interval excludes 0."""
    def answerable_only(report: dict) -> dict:
        return {"label": report.get("label"), "per_question": [q for q in report["per_question"] if q.get("answerable")]}

    result = compare_reports(answerable_only(report_a), answerable_only(report_b), metric=metric, seed=seed)
    low, high = result["ci95"]
    return {**result, "difference_shown": bool(low > 0 or high < 0)}


def auc(answerable: Sequence[float], unanswerable: Sequence[float]) -> float:
    """Chance that a random answerable question has a higher top score than a random unanswerable one (ties count half)."""
    wins = sum((a > u) + 0.5 * (a == u) for a in answerable for u in unanswerable)
    return wins / (len(answerable) * len(unanswerable))


def calibrate(report: dict, *, seed: int = 0, iters: int = 2000) -> dict:
    """How well the top search score separates answerable from unanswerable questions, and the threshold that balances the two errors.

    The rule evaluated is "abstain when the top score is below the threshold". Nothing is configured by this function.
    """
    positive = [q["top_score"] for q in report["per_question"] if q["answerable"]]
    negative = [q["top_score"] for q in report["per_question"] if not q["answerable"]]
    if len(positive) < MIN_VERIFIED_FOR_REPORT or len(negative) < MIN_UNANSWERABLE_FOR_CALIBRATION:
        raise ValueError(f"calibration needs at least {MIN_VERIFIED_FOR_REPORT} verified answerable and {MIN_UNANSWERABLE_FOR_CALIBRATION} "
                         f"verified unanswerable cases, have {len(positive)} and {len(negative)}")
    best = max(sorted(set(positive + negative)),
               key=lambda t: (0.5 * (sum(s >= t for s in positive) / len(positive) + sum(s < t for s in negative) / len(negative)), -t))
    rng = random.Random(seed)
    resampled = sorted(auc([rng.choice(positive) for _ in positive], [rng.choice(negative) for _ in negative]) for _ in range(iters))
    return {
        "label": report.get("label"), "n_answerable": len(positive), "n_unanswerable": len(negative),
        "auc": {"value": auc(positive, negative), "ci95": [resampled[int(0.025 * iters)], resampled[int(0.975 * iters) - 1]]},
        "candidate_threshold": best,
        "answerable_abstained": sum(s < best for s in positive) / len(positive),
        "unanswerable_abstained": sum(s < best for s in negative) / len(negative),
        "note": "A candidate only: it balances the two error rates on this sample. Read the interval and the two rates, decide what an "
                "unwarranted refusal costs against an unsupported answer, and set it yourself; this command changes no setting.",
    }


def _http_fetch(origin: str, token: str | None, mode: str) -> Fetch:
    def fetch(question: str) -> dict:
        params = {"q": question, "page_size": 5} if mode == "chat" else {"q": question, "type": "document", "page_size": 30, "domain": "all"}
        request = urllib.request.Request(f"{origin}/api/search?" + urllib.parse.urlencode(params),
                                         headers={"Authorization": f"Bearer {token}"} if token else {})
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read())

    return fetch


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    runner = commands.add_parser("run", help="search every verified question and score it")
    runner.add_argument("--label", required=True)
    runner.add_argument("--out", type=Path, required=True)
    runner.add_argument("--gold", type=Path, default=GOLD)
    runner.add_argument("--mode", choices=("document", "chat"), default="document")
    commands.add_parser("compare", help="paired difference between two run reports").add_argument("reports", nargs=2, type=Path)
    commands.add_parser("calibrate", help="separation of answerable from unanswerable by the top score").add_argument("report", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            origin = os.environ.get("FLAME_API_ORIGIN", "http://localhost:8000").rstrip("/")
            report = run(load_passage_gold(args.gold), _http_fetch(origin, os.environ.get("FLAME_READ_API_TOKEN"), args.mode), label=args.label)
            args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"label": report["label"], "n_answerable": report["n_answerable"], **report["retrieval"]}))
        elif args.command == "compare":
            a, b = (json.loads(path.read_text(encoding="utf-8")) for path in args.reports)
            print(json.dumps(compare_runs(a, b), indent=2))
        else:
            print(json.dumps(calibrate(json.loads(args.report.read_text(encoding="utf-8"))), indent=2))
    except ValueError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
