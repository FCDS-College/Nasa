| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.1.0 | 2026-10-12 | C2 | `docs/evaluation/reports/` |

# E5-8: LLM Comparison Report (Candidate Models)

## 1. Candidate Models Evaluated

* `gemini-1.5-pro` (Target Primary Model)
* `gemini-1.5-flash` (Target High-Throughput Model)
* `gpt-4o` (Cross-provider Scientific Baseline)

---

## 2. Evaluation Protocol & Router (M1)

All models are queried through the central model router using the frozen benchmark `datasets/evaluation/rag_gold.jsonl`. Blinded outputs will be evaluated by domain experts per `docs/evaluation/annotation-guidelines.md`.

*Initial Status: Scheduled for Phase 2 Week 5 upon model router deployment.*
