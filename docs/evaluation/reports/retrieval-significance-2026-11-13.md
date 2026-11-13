| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | Generated; human review pending | 0.1.0 | 2026-11-13 | E2, M2 | `ai/rag/evaluation/stats.py`, `ai/rag/evaluation/flame_retrieval_benchmark.py` |

# Retrieval benchmark: are the differences real?

The committed benchmark runs (`retrieval-*.json`, 26 questions each) report point estimates only. This report adds a **paired bootstrap interval** over the
questions the two runs share (4,000 resamples, fixed seed 0). If the interval contains 0 the difference is not distinguishable from noise with this many
questions. Nothing was re-run against the API: the inputs are the committed per-question results.

### reranker on (`cross-encoder/ms-marco-MiniLM-L-6-v2`, depth 20, CPU) versus off (`stack`, `FLAME_RERANKER_ENABLED=false`)

```text
$ python -m ai.rag.evaluation.stats docs/evaluation/reports/retrieval-stack-2026-11-12.json docs/evaluation/reports/retrieval-stack-rerank-2026-11-12.json
hit@1   stack -> stack-rerank: 0.808 -> 0.885  delta +0.077  95% CI [-0.077, +0.231]  (n=26: 3 better, 1 worse, 22 tied)  NOT distinguishable from noise
rr@10   stack -> stack-rerank: 0.859 -> 0.913  delta +0.054  95% CI [-0.045, +0.160]  (n=26: 4 better, 1 worse, 21 tied)  NOT distinguishable from noise
```

### reranker on at the shipped default (fastembed reranker, depth 10, 2000 characters) versus off

```text
$ python -m ai.rag.evaluation.stats docs/evaluation/reports/retrieval-stack-2026-11-12.json docs/evaluation/reports/retrieval-rerank-fastembed-depth10-2026-11-12.json
hit@1   stack -> rerank-fastembed-depth10: 0.808 -> 0.885  delta +0.077  95% CI [-0.077, +0.231]  (n=26: 3 better, 1 worse, 22 tied)  NOT distinguishable from noise
rr@10   stack -> rerank-fastembed-depth10: 0.859 -> 0.913  delta +0.054  95% CI [-0.045, +0.160]  (n=26: 4 better, 1 worse, 21 tied)  NOT distinguishable from noise
```

### hybrid (lexical + dense) versus lexical only

```text
$ python -m ai.rag.evaluation.stats docs/evaluation/reports/retrieval-lexical-2026-11-07.json docs/evaluation/reports/retrieval-hybrid-2026-11-07.json
hit@1   lexical -> hybrid: 0.308 -> 0.808  delta +0.500  95% CI [+0.308, +0.692]  (n=26: 13 better, 0 worse, 13 tied)  distinguishable from noise
rr@10   lexical -> hybrid: 0.308 -> 0.859  delta +0.551  95% CI [+0.365, +0.734]  (n=26: 17 better, 0 worse, 9 tied)  distinguishable from noise
```

## Reading the results

- **Hybrid versus lexical is a real effect**: +0.50 hit@1, with an interval that excludes 0 and no question where lexical wins. The benchmark detects an effect this large.
- **The reranker's improvement is not shown.** Three questions improve and one gets worse on hit@1, and the interval is about ±0.15 around +0.08. That is what 26 questions
  can resolve. "Reranker on by default" is therefore a design decision with no statistical support from this benchmark, in either direction.
- The same limits apply to the earlier settings comparisons (rerank depth 20 versus 10, passage cap 2000 versus 1000): they were chosen on these 26 questions.

## Known limitations

- 26 AI-authored, document-level, all-answerable questions (`retrieval-2026-11-07.md`); the intervals describe sampling noise over these questions, not over the questions users will ask.
- The bootstrap resamples questions only; run-to-run variation of the system is not measured.
- No intervals exist for the older runs that were not committed with per-question rows.
- Result of an independent check on the committed PDFs (not the API) agrees: dense, BM25 and hybrid are indistinguishable there too (`.internal/research/2026-11-13-nlp-audit.md`, E-2).

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-11-13 | First version: paired intervals over the committed runs. |
