"""Embedder / reranker comparison harness: ranking, metrics and paired differences, with fake models (no downloads)."""
import numpy as np

from ai.rag.evaluation.compare_models import Config, evaluate_config, run_comparison

PAGES = [
    {"doc": "D1", "page": 1, "text": "oxygen index of acrylic sheets"},
    {"doc": "D1", "page": 2, "text": "unrelated shipping logistics"},
    {"doc": "D2", "page": 1, "text": "flame spread over paper in microgravity"},
    {"doc": "D3", "page": 1, "text": "cabin pressure and decompression sickness"},
]
QUESTIONS = [
    {"id": "Q1", "q": "flame spread microgravity", "rel": {"D2"}},
    {"id": "Q2", "q": "decompression sickness cabin", "rel": {"D3"}},
    {"id": "Q3", "q": "oxygen index acrylic", "rel": {"D1"}},
]
VOCAB = sorted({w for p in PAGES for w in p["text"].split()} | {w for q in QUESTIONS for w in q["q"].split()})


def bag_embedder(texts, query):
    return np.array([[1.0 if w in t.split() else 0.0 for w in VOCAB] for t in texts])


def random_embedder(texts, query):
    rng = np.random.default_rng(0)
    return rng.normal(size=(len(texts), 8))


def keyword_reranker(query, texts):
    return [float(len(set(query.split()) & set(t.split()))) for t in texts]


def test_a_good_embedder_ranks_the_relevant_document_first():
    result = evaluate_config(Config("bag", bag_embedder, None), PAGES, QUESTIONS)
    assert [q["rr@10"] for q in result["per_question"]] == [1.0, 1.0, 1.0]
    assert result["mean"]["hit@1"] == 1.0


def test_the_reranker_reorders_the_candidate_window():
    result = evaluate_config(Config("rand+kw", random_embedder, keyword_reranker), PAGES, QUESTIONS, rerank_depth=4)
    assert result["mean"]["rr@10"] == 1.0                          # all four pages are reranked by keyword overlap


def test_documents_are_ranked_by_their_best_page_without_duplicates():
    result = evaluate_config(Config("bag", bag_embedder, None), PAGES, QUESTIONS)
    assert all(len(q["ranked_docs"]) == len(set(q["ranked_docs"])) for q in result["per_question"])


def test_comparison_reports_paired_differences_against_the_baseline():
    report = run_comparison([Config("rand", random_embedder, None), Config("bag", bag_embedder, None)], PAGES, QUESTIONS, baseline="rand")
    assert report["baseline"] == "rand" and report["n_questions"] == 3
    row = next(r for r in report["configs"] if r["label"] == "bag")
    assert row["vs_baseline"]["delta_rr@10"] >= 0 and len(row["vs_baseline"]["ci95"]) == 2
    assert next(r for r in report["configs"] if r["label"] == "rand")["vs_baseline"] is None
    assert "indicative" in report["caveat"].lower()
