"""Retrieval benchmark of Flame's live /api/search against a corpus-grounded gold set.

    FLAME_API_ORIGIN=http://localhost:8000 FLAME_READ_API_TOKEN=... \
        python -m ai.rag.evaluation.flame_retrieval_benchmark --label hybrid --out report.json

Gold set: datasets/evaluation/retrieval_gold_v1.jsonl. Each question is paraphrased (it avoids the
labelled document's key phrase) and lists the corpus documents (source IDs) that answer it; every label
carries a phrase that `--check-labels` verifies against the ingested text. Labels are document-level, so
the ranking is scored by the first appearance of each document in the top-k chunk hits.

Metrics: hit@1, hit@3, hit@5 (a relevant document appears in the top k documents), MRR@10 and
recall@5 (share of a question's relevant documents found in the top 5), each with a 95% bootstrap interval. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from ai.rag.evaluation.stats import bootstrap_ci

ROOT = Path(__file__).resolve().parents[3]
GOLD = ROOT / "datasets" / "evaluation" / "retrieval_gold_v1.jsonl"


def load_gold(path: Path = GOLD) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def ranked_documents(origin: str, token: str | None, question: str, k: int = 30) -> tuple[list[str], str, float]:
    url = f"{origin}/api/search?" + urllib.parse.urlencode({"q": question, "type": "document", "page_size": k, "domain": "all"})
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read())
    latency = time.perf_counter() - started
    docs: list[str] = []
    for hit in body["results"]:
        sid = (hit.get("source") or {}).get("source_id")
        if sid and sid not in docs:
            docs.append(sid)
    return docs, body["retrieval"]["mode"], latency


def score(gold: list[dict], runs: dict[str, list[str]]) -> dict:
    per_question = []
    for g in gold:
        docs = runs[g["id"]]
        relevant = set(g["relevant"])
        first = next((i + 1 for i, d in enumerate(docs[:10]) if d in relevant), None)
        per_question.append({
            "id": g["id"], "top5": docs[:5], "first_relevant_rank": first,
            "hit@1": int(first == 1), "hit@3": int(first is not None and first <= 3), "hit@5": int(first is not None and first <= 5),
            "rr@10": 0.0 if first is None else 1.0 / first,
            "recall@5": len(relevant & set(docs[:5])) / len(relevant),
        })
    def mean(key):
        return round(statistics.fmean(q[key] for q in per_question), 4)
    # 95% bootstrap intervals over questions. With a few dozen questions they are wide: report them with every number, and
    # compare two runs with `python -m ai.rag.evaluation.stats` (paired), not by eye.
    ci95 = {name: [round(x, 4) for x in bootstrap_ci([q[key] for q in per_question])]
            for name, key in (("hit@1", "hit@1"), ("hit@3", "hit@3"), ("hit@5", "hit@5"), ("mrr@10", "rr@10"), ("recall@5", "recall@5"))}
    return {"questions": len(gold), "hit@1": mean("hit@1"), "hit@3": mean("hit@3"), "hit@5": mean("hit@5"),
            "mrr@10": mean("rr@10"), "recall@5": mean("recall@5"), "ci95": ci95, "per_question": per_question}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--label", required=True, help="name of this configuration, e.g. hybrid or lexical")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    origin = os.environ.get("FLAME_API_ORIGIN", "http://localhost:8000").rstrip("/")
    token = os.environ.get("FLAME_READ_API_TOKEN")
    gold = load_gold()
    runs, modes, latencies = {}, set(), []
    for g in gold:
        docs, mode, latency = ranked_documents(origin, token, g["question"])
        runs[g["id"]] = docs
        modes.add(mode)
        latencies.append(latency)
    result = score(gold, runs)
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = None
    report = {
        "label": args.label, "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "git_commit": commit,
        "gold_set": str(GOLD.relative_to(ROOT)), "retrieval_modes_reported": sorted(modes),
        "latency_s": {"p50": round(statistics.median(latencies), 3), "max": round(max(latencies), 3)},
        **result,
    }
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("label", "retrieval_modes_reported", "hit@1", "hit@3", "hit@5", "mrr@10", "recall@5", "ci95", "latency_s")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
