"""Compare embedders and rerankers on the committed PDFs (audit roadmap item 13). Indicative only.

    python -m ai.rag.evaluation.compare_models docs/research \\
        --embedders BAAI/bge-small-en-v1.5 BAAI/bge-base-en-v1.5 \\
        --rerankers none Xenova/ms-marco-MiniLM-L-6-v2 BAAI/bge-reranker-base --cache-dir <dir> --out report.json

Corpus: the pages production would index (`indexed_pages`), the dense side reading each page's first 2,000 characters as production
does. Gold: `datasets/evaluation/retrieval_gold_v1.jsonl`, document-level, restricted to documents that have indexable text here.
Ranking: dense top pages, the top `rerank_depth` reordered by the cross-encoder, documents ranked by their best page.

Caveat (also printed in the report): 26 or fewer document-level questions on 24 documents. Differences are reported with paired
95 % bootstrap intervals; an interval containing 0 means "not distinguishable", not "equal". This does not measure passage-level
retrieval, multilingual queries, speed in production, or the model licence/size trade-off.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

from ai.rag.evaluation.stats import bootstrap_ci, paired_bootstrap_ci

CAVEAT = ("Indicative only: a few dozen document-level questions on 24 committed reports. Intervals that contain 0 mean the "
          "difference is not distinguishable from noise with this sample, not that the models are equal.")
RERANK_DEPTH = 10
DENSE_CHARS = 2000      # what the production embedder reads of a page
Embedder = Callable[[Sequence[str], bool], np.ndarray]          # (texts, is_query) -> vectors
Reranker = Callable[[str, Sequence[str]], Sequence[float]]


@dataclass(frozen=True)
class Config:
    label: str
    embedder: Embedder
    reranker: Reranker | None = None


def _rank_documents(page_order: Sequence[int], pages: Sequence[dict]) -> list[str]:
    seen: list[str] = []
    for index in page_order:
        if pages[index]["doc"] not in seen:
            seen.append(pages[index]["doc"])
    return seen


def evaluate_config(config: Config, pages: Sequence[dict], questions: Sequence[dict], *, rerank_depth: int = RERANK_DEPTH) -> dict:
    page_vectors = np.asarray(config.embedder([p["text"][:DENSE_CHARS] for p in pages], False), dtype=float)
    page_norms = np.linalg.norm(page_vectors, axis=1) + 1e-12
    per_question = []
    for question in questions:
        query_vector = np.asarray(config.embedder([question["q"]], True), dtype=float)[0]
        sims = page_vectors @ query_vector / (page_norms * (np.linalg.norm(query_vector) + 1e-12))
        order = [int(i) for i in np.argsort(-sims, kind="stable")]
        if config.reranker is not None:
            window = order[:rerank_depth]
            scores = list(config.reranker(question["q"], [pages[i]["text"][:DENSE_CHARS] for i in window]))
            window = [i for _, i in sorted(zip((-s for s in scores), window), key=lambda pair: pair[0])]
            order = window + order[rerank_depth:]
        ranked = _rank_documents(order, pages)[:10]
        rr = next((1 / rank for rank, doc in enumerate(ranked, start=1) if doc in question["rel"]), 0.0)
        per_question.append({"id": question["id"], "rr@10": rr, "hit@1": float(rr == 1.0),
                             "hit@3": float(any(d in question["rel"] for d in ranked[:3])), "ranked_docs": ranked})
    for model in (config.embedder, config.reranker):
        getattr(model, "close", lambda: None)()
    mean = {metric: sum(q[metric] for q in per_question) / len(per_question) for metric in ("rr@10", "hit@1", "hit@3")}
    low, high = bootstrap_ci([q["rr@10"] for q in per_question])
    return {"label": config.label, "mean": mean, "rr@10_ci95": [low, high], "per_question": per_question}


def run_comparison(configs: Sequence[Config], pages: Sequence[dict], questions: Sequence[dict], *, baseline: str | None = None,
                   rerank_depth: int = RERANK_DEPTH) -> dict:
    results = []
    for config in configs:
        started = time.perf_counter()
        result = evaluate_config(config, pages, questions, rerank_depth=rerank_depth)
        result["seconds"] = round(time.perf_counter() - started, 1)
        results.append(result)
    baseline = baseline or results[0]["label"]
    base = next(r for r in results if r["label"] == baseline)
    base_rr = [q["rr@10"] for q in base["per_question"]]
    rows = []
    for result in results:
        rr = [q["rr@10"] for q in result["per_question"]]
        compared = None
        if result is not base:
            low, high = paired_bootstrap_ci(base_rr, rr)
            compared = {"delta_rr@10": sum(y - x for x, y in zip(base_rr, rr)) / len(rr), "ci95": [low, high],
                        "improved": sum(y > x for x, y in zip(base_rr, rr)), "worse": sum(y < x for x, y in zip(base_rr, rr))}
        rows.append({"label": result["label"], "mean": result["mean"], "rr@10_ci95": result["rr@10_ci95"], "seconds": result["seconds"],
                     "vs_baseline": compared})
    return {"baseline": baseline, "n_questions": len(questions), "n_pages": len(pages), "rerank_depth": rerank_depth,
            "configs": rows, "caveat": CAVEAT}


# --- real models (fastembed) ---------------------------------------------------------------------------------------------
# Models are loaded on first use and released when a config has been evaluated: the larger ones are hundreds of MB to 1 GB each,
# and loading every model up front exhausted memory on a small machine.

class _FastembedEmbedder:
    def __init__(self, name: str, cache_dir: str | None) -> None:
        self.name, self.cache_dir, self._model = name, cache_dir, None
        self._memo: dict[tuple, np.ndarray] = {}        # the same pages and questions are embedded once per model, not per reranker

    def __call__(self, texts: Sequence[str], query: bool) -> np.ndarray:
        key = (query, tuple(texts))
        if key not in self._memo:
            if self._model is None:
                from fastembed import TextEmbedding

                self._model = TextEmbedding(model_name=self.name, cache_dir=self.cache_dir)
            from ai.providers.local.fastembed_embeddings import QUERY_PREFIX

            self._memo[key] = np.array(list(self._model.embed([(QUERY_PREFIX + t if query else t) for t in texts])))
        return self._memo[key]

    def close(self) -> None:
        self._model = None


class _FastembedReranker:
    def __init__(self, name: str, cache_dir: str | None) -> None:
        self.name, self.cache_dir, self._model = name, cache_dir, None

    def __call__(self, query: str, texts: Sequence[str]) -> list[float]:
        if self._model is None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder

            self._model = TextCrossEncoder(model_name=self.name, cache_dir=self.cache_dir)
        return list(self._model.rerank(query, list(texts)))

    def close(self) -> None:
        self._model = None


def load_corpus(pdf_dir: Path, gold_path: Path) -> tuple[list[dict], list[dict]]:
    from ai.rag.evaluation.propose_candidates import indexed_pages

    pages = [{"doc": f"FF-NTRS-{path.stem}", "page": page["page"], "text": page["indexed"]}
             for path in sorted(Path(pdf_dir).glob("*.pdf")) for page in indexed_pages(path)]
    have = {p["doc"] for p in pages}
    questions = []
    for line in Path(gold_path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            relevant = {d for d in row["relevant"] if d in have}
            if relevant:
                questions.append({"id": row["id"], "q": row["question"], "rel": relevant})
    return pages, questions


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pdf_dir", type=Path)
    parser.add_argument("--gold", type=Path, default=Path("datasets/evaluation/retrieval_gold_v1.jsonl"))
    parser.add_argument("--embedders", nargs="+", default=["BAAI/bge-small-en-v1.5"])
    parser.add_argument("--rerankers", nargs="+", default=["none"])
    parser.add_argument("--cache-dir")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    pages, questions = load_corpus(args.pdf_dir, args.gold)
    configs = []
    for embedder_name in args.embedders:
        embedder = _FastembedEmbedder(embedder_name, args.cache_dir)
        for reranker_name in args.rerankers:
            reranker = None if reranker_name == "none" else _FastembedReranker(reranker_name, args.cache_dir)
            configs.append(Config(f"{embedder_name.split('/')[-1]}+{reranker_name.split('/')[-1]}", embedder, reranker))
    report = run_comparison(configs, pages, questions)
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
