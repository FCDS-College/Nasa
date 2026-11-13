"""Confidence intervals for evaluation metrics. Stdlib only.

With a few dozen questions a difference of a few points is noise: the 26-question retrieval gold cannot show an effect of
0.05 (audit finding E-2). Every reported mean should travel with an interval, and every claimed improvement with a paired one.

    python -m ai.rag.evaluation.stats docs/evaluation/reports/retrieval-stack-2026-11-12.json \
        docs/evaluation/reports/retrieval-stack-rerank-2026-11-12.json
"""
from __future__ import annotations

import argparse
import json
import random
from collections.abc import Iterable, Sequence
from pathlib import Path

_TIE = 1e-12


def bootstrap_ci(values: Iterable[float], *, iters: int = 4000, seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:
    """Percentile bootstrap interval of the mean. Resamples observations (questions), with a fixed seed so it is reproducible."""
    data = list(values)
    if not data:
        raise ValueError("no observations: an interval needs at least one question")
    n = len(data)
    rng = random.Random(seed)
    means = sorted(sum(data[rng.randrange(n)] for _ in range(n)) / n for _ in range(iters))
    return means[int(alpha / 2 * iters)], means[min(iters - 1, int((1 - alpha / 2) * iters))]


def paired_bootstrap_ci(a: Sequence[float], b: Sequence[float], **kwargs) -> tuple[float, float]:
    """Interval of mean(b - a) over the same questions. If it contains 0, the difference is not distinguishable from noise."""
    if len(a) != len(b):
        raise ValueError("paired samples must have the same length")
    return bootstrap_ci([y - x for x, y in zip(a, b)], **kwargs)


def compare_reports(report_a: dict, report_b: dict, *, metric: str = "rr@10", seed: int = 0) -> dict:
    """Paired comparison of two benchmark reports (as written by `flame_retrieval_benchmark`) on the questions they share."""
    a = {q["id"]: q[metric] for q in report_a["per_question"]}
    b = {q["id"]: q[metric] for q in report_b["per_question"]}
    common = sorted(set(a) & set(b))
    if not common:
        raise ValueError("the two reports have no question in common")
    xs, ys = [a[i] for i in common], [b[i] for i in common]
    deltas = [y - x for x, y in zip(xs, ys)]
    return {
        "a": report_a.get("label"), "b": report_b.get("label"), "metric": metric, "n": len(common),
        "mean_a": sum(xs) / len(xs), "mean_b": sum(ys) / len(ys), "delta": sum(deltas) / len(deltas),
        "ci95": list(paired_bootstrap_ci(xs, ys, seed=seed)),
        "improved": sum(d > _TIE for d in deltas), "worse": sum(d < -_TIE for d in deltas), "tied": sum(abs(d) <= _TIE for d in deltas),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Paired comparison of two retrieval benchmark reports.")
    parser.add_argument("report_a", type=Path)
    parser.add_argument("report_b", type=Path)
    parser.add_argument("--metric", default=None, help="per-question key (default: hit@1 and rr@10)")
    args = parser.parse_args()
    a, b = (json.loads(p.read_text(encoding="utf-8")) for p in (args.report_a, args.report_b))
    for metric in ([args.metric] if args.metric else ["hit@1", "rr@10"]):
        r = compare_reports(a, b, metric=metric)
        lo, hi = r["ci95"]
        verdict = "distinguishable from noise" if lo > 0 or hi < 0 else "NOT distinguishable from noise"
        print(f"{r['metric']:7s} {r['a']} -> {r['b']}: {r['mean_a']:.3f} -> {r['mean_b']:.3f}  delta {r['delta']:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]"
              f"  (n={r['n']}: {r['improved']} better, {r['worse']} worse, {r['tied']} tied)  {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
