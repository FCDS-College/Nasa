"""The PII-masking exam: how often does the masker hide private data, and how often does it damage harmless text?

    python -m ai.rag.evaluation.run_pii_exam --out docs/evaluation/reports/latest/pii-exam.json
    python -m ai.rag.evaluation.run_pii_exam --check          # validate the exam file only

Every case of `datasets/evaluation/pii_gold_v1.jsonl` lists the `pii` strings that must disappear from the masked text and the
`keep` strings that must survive it (report numbers, identifiers, measurements). Per string:

* a PII string that is still in the output is a **miss** (private data leaked);
* a PII string that is gone is a **hit**;
* a `keep` string that is gone is a **false positive** (the masker damaged harmless text).

precision = hits / (hits + false positives); miss rate = misses / PII strings. Intervals are percentile bootstraps over cases
(fixed seed). "Gone" is a string test: a mask that hides only part of a phone number still counts as a hit, which flatters the result.

The default detector is the only masker in the repository, `tests.eval.master_pipeline.PIIMaskingGuardrail`; `--detector module:Class`
scores another one (it needs `mask_sensitive_data(text) -> {"masked_output": ...}`). The exam was drafted by an AI and is unverified
(annotation-guidelines §5.5): the report says so, and the gate will not call its rows verified.
"""
from __future__ import annotations

import argparse
import importlib
import json
import random
import subprocess
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "datasets" / "evaluation" / "pii_gold_v1.jsonl"
DEFAULT_DETECTOR = "tests.eval.master_pipeline:PIIMaskingGuardrail"


def load(path: Path = DATA) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate(cases: Sequence[dict]) -> list[str]:
    """Problems with the exam file itself (empty list when sound)."""
    problems, seen = [], set()
    for case in cases:
        cid = case.get("id", "?")
        if cid in seen:
            problems.append(f"{cid}: duplicate id")
        seen.add(cid)
        for key in ("id", "lang", "kind", "text", "pii", "keep", "provenance"):
            if key not in case:
                problems.append(f"{cid}: missing `{key}`")
        for string in [*case.get("pii", []), *case.get("keep", [])]:
            if string not in case.get("text", ""):
                problems.append(f"{cid}: `{string}` is not in the text")
        if set(case.get("pii", [])) & set(case.get("keep", [])):
            problems.append(f"{cid}: a string is both PII and keep")
        if case.get("lang") not in ("en", "ar"):
            problems.append(f"{cid}: lang must be en or ar")
    if not any(c.get("pii") for c in cases):
        problems.append("no case has PII")
    if not any(c.get("keep") for c in cases):
        problems.append("no case has a keep string")
    return problems


def score_case(case: dict, masked: str) -> dict:
    misses = [s for s in case["pii"] if s in masked]
    destroyed = [s for s in case["keep"] if s not in masked]
    return {"id": case["id"], "kind": case["kind"], "lang": case["lang"], "n_pii": len(case["pii"]), "misses": misses,
            "n_keep": len(case["keep"]), "destroyed": destroyed}


def _ratios(rows: Sequence[dict]) -> dict:
    pii = sum(r["n_pii"] for r in rows)
    missed = sum(len(r["misses"]) for r in rows)
    hits = pii - missed
    destroyed = sum(len(r["destroyed"]) for r in rows)
    return {"n_pii": pii, "hits": hits, "misses": missed, "n_keep": sum(r["n_keep"] for r in rows), "false_positives": destroyed,
            "precision": hits / (hits + destroyed) if hits + destroyed else None,
            "recall": hits / pii if pii else None, "miss_rate": missed / pii if pii else None}


def _interval(rows: Sequence[dict], key: str, *, iters: int = 2000, seed: int = 0) -> list[float | None]:
    rng = random.Random(seed)
    draws = sorted(v for v in (_ratios([rows[rng.randrange(len(rows))] for _ in rows])[key] for _ in range(iters)) if v is not None)
    if not draws:
        return [None, None]
    return [round(draws[int(0.025 * len(draws))], 4), round(draws[min(len(draws) - 1, int(0.975 * len(draws)))], 4)]


def run(cases: Sequence[dict], mask: Callable[[str], str], *, detector: str = DEFAULT_DETECTOR) -> dict:
    rows = [score_case(case, mask(case["text"])) for case in cases]
    total = _ratios(rows)
    by = {}
    for field in ("kind", "lang"):
        for value in sorted({r[field] for r in rows}):
            part = _ratios([r for r in rows if r[field] == value])
            by[f"{field}={value}"] = {k: (None if v is None else round(v, 4)) for k, v in part.items()}
    verified = sum(bool((c.get("provenance") or {}).get("verified")) for c in cases)
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or None
    except OSError:
        commit = None
    return {
        "exam": "pii_gold_v1", "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "git_commit": commit, "detector": detector,
        "n_cases": len(cases), "verified": verified,
        **{k: (None if v is None else round(v, 4)) for k, v in total.items()},
        "precisionCI95": _interval(rows, "precision"), "recallCI95": _interval(rows, "recall"), "missRateCI95": _interval(rows, "miss_rate"),
        "by": by,
        "failures": [{"id": r["id"], "kind": r["kind"], "leaked": r["misses"], "damaged": r["destroyed"]} for r in rows if r["misses"] or r["destroyed"]],
        "note": "Drafted by an AI and unverified. String test: a partly hidden phone number counts as hidden. Names are not treated as PII.",
    }


def load_detector(spec: str) -> Callable[[str], str]:
    module_name, _, class_name = spec.partition(":")
    instance = getattr(importlib.import_module(module_name), class_name)()
    return lambda text: instance.mask_sensitive_data(text)["masked_output"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--detector", default=DEFAULT_DETECTOR, help="module:Class with mask_sensitive_data(text)")
    parser.add_argument("--check", action="store_true", help="validate the exam file and stop")
    args = parser.parse_args(argv)
    cases = load(args.data)
    problems = validate(cases)
    if problems:
        print("the exam file breaks its own rules:\n  " + "\n  ".join(problems[:10]))
        return 1
    if args.check:
        print(f"{len(cases)} cases, valid")
        return 0
    report = run(cases, load_detector(args.detector), detector=args.detector)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PII exam: {report['n_cases']} cases, precision {report['precision']} {report['precisionCI95']}, "
          f"miss rate {report['miss_rate']} {report['missRateCI95']} ({report['misses']} of {report['n_pii']} PII strings leaked, "
          f"{report['false_positives']} of {report['n_keep']} harmless strings damaged). Labels verified: {report['verified']}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
