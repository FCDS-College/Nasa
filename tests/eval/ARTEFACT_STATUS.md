# What the files in `tests/eval/` measure

Written 2026-11-13 after an audit (`.internal/research/2026-11-13-nlp-audit.md`, finding E-1). Each row says whether the artefact
measures the deployed system. Nothing here has been run against a real language model or against the served API.

| Artefact | What it is | Measures Flame? |
|---|---|---|
| `metrics.py` | Recall@k, MRR, nDCG@k, citation precision/recall/F1. Recall, MRR and nDCG are `None` (undefined) when no evidence is expected. | No: a library of formulas. Unit-tested in `test_evaluation_validity.py`. |
| `mock_rag.py`, `rag_connector.py` (`mock` mode) | Two hard-coded answers, chosen by whether the query contains "combustion" or a few Arabic words. | **No.** It scores the harness. |
| `rag_connector.py` (`api` mode) | Raises `NotImplementedError`. It used to POST JSON to `/api/search`, which is `GET ?q=`, and returned the error text as the "answer". | No. For the live API use `ai/rag/evaluation/flame_retrieval_benchmark.py`. |
| `../../run_evaluation.py`, `../../evaluation_report.json` | Runs the gold file through the connector. The report names the evaluated system (`mock`), averages only answerable cases, and lists its caveats. | **No** (mock). Not run in CI. |
| `../../datasets/evaluation/rag_gold.jsonl` | 38 cases (31 answerable, 7 not). Its evidence IDs (`DOC-001-P15`, ...) are not documents of the indexed corpus. | Cannot be answered from the index. |
| `master_pipeline.py` | Guardrails: substring and regex rules (citation, PII, cross-modal, self-correction) and `LLMJudge`. The judge parses the verdict JSON when a Gemini key is set, otherwise it checks a keyword list. | Heuristics, not a validated judge. |
| `evaluator.py` | Averages the `metrics.*` columns of a file and compares them with thresholds. On a file without those columns (such as the gold file) it reports `NOT EVALUATED`. | Only as good as the scores in the file. |
| `test_cases.jsonl` | 33 records with scores (`metrics`) typed in by hand; one `domain` is `movie_fire_ship`. Queries repeat. | **No**: not the output of any system. |
| `*.ipynb` (15 notebooks) | Keyword and regex guardrail classes, and averages over the typed scores in `test_cases.jsonl`. None of them references a RAG system, a connector or an API (checked by search). One (`rag_evaluator`) hard-codes a score of 3.8. | **No.** Demonstrations. |
| `test_provenance.py` | Schema, coverage and leakage checks on `rag_gold.jsonl`. Page-level leakage cannot fail. Document-level leakage is a strict expected failure: the splits share documents. | Data checks only. |
| `test_api_contracts.py` | Four tests, all skipped. | No. |
| `ranking.py` | Hard gates plus a weighted composite (`0.40 * recall + 0.40 * faithfulness + 0.20 * speed`). Not a Pareto frontier; no BM25. | No: inputs are typed in tests. |
| `evaluation_report.json` (in this directory) | A report of 2026-10-05 over 6 test cases from the legacy notebooks (typed scores). Not the same file as the one at the repository root. | No. |

## Tools for a trustworthy set (no data yet)
| Tool | Purpose |
|---|---|
| `ai/rag/evaluation/stats.py` | Bootstrap intervals; paired comparison of two benchmark runs (`python -m ai.rag.evaluation.stats A.json B.json`). |
| `ai/rag/evaluation/passage_gold.py`, `datasets/evaluation/passage_gold_v1.*` | Passage-level gold schema, validator (document-disjoint splits, unanswerable share, verifier other than the author) and scoring. The gold file is empty. |
| `ai/rag/evaluation/propose_candidates.py` | A worklist of sentences with measurements for annotators to write questions about. Proposals are not gold. |

## Where real measurements are
`ai/rag/evaluation/flame_retrieval_benchmark.py` runs the live `/api/search` against `datasets/evaluation/retrieval_gold_v1.jsonl`
(26 AI-authored questions, document-level labels, all answerable). It now writes a 95% interval with each number; `docs/evaluation/reports/retrieval-significance-2026-11-13.md` compares the committed runs. It is the only measurement of the
served retrieval stack. No measurement of generated-answer quality, citation correctness or abstention exists yet.
