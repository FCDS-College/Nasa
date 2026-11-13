| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | Generated; human review pending | 0.1.0 | 2026-11-13 | E2, M2, ADR-006 | `ai/rag/evaluation/compare_models.py`, `tests/unit/test_compare_models.py`, `model-comparison-2026-11-13.json` |

# Embedder and reranker comparison (audit roadmap item 13)

**Question.** Would a larger embedder (`BAAI/bge-base-en-v1.5`) or a larger reranker (`BAAI/bge-reranker-base`) retrieve better than the served pair, `bge-small-en-v1.5` and `ms-marco-MiniLM-L-6-v2`?

**Answer, with this evidence: no difference can be shown, and none of the larger models is worth its cost on this data.** The evidence is small (26 document-level questions); read the intervals, not the point estimates.

## Method

`python -m ai.rag.evaluation.compare_models docs/research --embedders BAAI/bge-small-en-v1.5 BAAI/bge-base-en-v1.5 --rerankers Xenova/ms-marco-MiniLM-L-6-v2 none BAAI/bge-reranker-base --cache-dir <dir> --out model-comparison-2026-11-13.json` (fastembed ONNX, CPU, 2026-11-13).

- Corpus: the 240 indexable pages of the 24 committed NTRS PDFs, as production would index them (`indexed_pages`: normalised text); the dense side reads the first 2,000 characters of a page, as production does.
- Gold: the 26 questions of `datasets/evaluation/retrieval_gold_v1.jsonl` whose relevant document has indexable text here (all 26). Document-level relevance.
- Ranking: dense nearest pages, the top 10 reordered by the cross-encoder, documents ranked by their best page, `rr@10` and `hit@k` per question. No lexical leg and no RRF: this isolates the two models, so absolute numbers are not the served stack's.
- Intervals: percentile bootstrap over questions; differences are paired against the served pair (4,000 resamples, seed 0).

## Result

| Embedder + reranker | rr@10 | 95 % CI | hit@1 | hit@3 | Δ rr@10 vs served | Δ 95 % CI | better / worse questions |
|---|---|---|---|---|---|---|---|
| bge-small + MiniLM-L-6 (**served**) | 0.897 | 0.78–1.00 | 0.885 | 0.923 | | | |
| bge-small, no reranker | 0.843 | 0.70–0.96 | 0.808 | 0.885 | −0.054 | −0.163 to +0.026 | 1 / 3 |
| bge-small + bge-reranker-base | 0.840 | 0.71–0.96 | 0.769 | 0.923 | −0.058 | −0.115 to 0.000 | 0 / 3 |
| bge-base + MiniLM-L-6 | 0.904 | 0.79–1.00 | 0.885 | 0.923 | +0.006 | 0.000 to +0.019 | 1 / 0 |
| bge-base, no reranker | 0.849 | 0.72–0.96 | 0.808 | 0.885 | −0.048 | −0.135 to +0.013 | 1 / 2 |
| bge-base + bge-reranker-base | 0.885 | 0.77–0.98 | 0.846 | 0.923 | −0.013 | −0.058 to +0.019 | 1 / 1 |

- **bge-base over bge-small:** +0.006 rr@10 with the same reranker, one question changed. That is nothing. It costs twice the vector size (768 against 384 dimensions) and the migration `chunk_embedding vector(384)`, a re-index and a manifest change.
- **bge-reranker-base over MiniLM:** not better in either pairing (−0.058 and −0.019 against the matching MiniLM rows) and about 13× the download (1.04 GB against 0.08 GB, fastembed's listing).
- **Reranker on or off** (served embedder): −0.054 without it, interval −0.163 to +0.026, which contains 0: consistent with the earlier finding that the reranker's gain is not significant at this sample size (`retrieval-significance-2026-11-13.md`).

## Recommendation

Keep `bge-small-en-v1.5` and `ms-marco-MiniLM-L-6-v2`. Revisit only with the passage-level gold set (≥ 20 verified questions, `docs/evaluation/annotation-guidelines.md`), where a larger embedder could matter more than at document level, and with Arabic queries if those are in scope: neither bge model above is multilingual.

## Known limitations

- 26 AI-authored, document-level, all-answerable questions; the intervals describe sampling noise over these questions, not over user questions. A real gain of a few points would not be detectable here.
- Document-level relevance cannot show whether the right *passage* ranks higher, which is where a stronger model is most likely to help.
- The ranking is dense (plus rerank) only; the served stack also fuses a lexical leg.
- No timing or memory comparison is claimed: the harness's per-config seconds include model load and, for the first config of an embedder, page embedding.
- One run, one machine; model files as downloaded by fastembed on 2026-11-13.

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-11-13 | First version. |
