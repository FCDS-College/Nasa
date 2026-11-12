# Retrieval evaluation: the ai/rag search stack and the reranker (2026-11-12)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas), built with Claude Code | Current (gold set still needs human review: Ziad, Eman) | 1.0.0 | 2026-11-12 | ADR-006, M11 | `ai/rag/retrieval/search_stack.py`, `apps/api/flame_api/main.py` (`search`), `ai/rag/evaluation/flame_retrieval_benchmark.py` |

ADR-006 says the API's own search "stays until `ai/rag` passes the M11 benchmark at least as well, then it is retired". This report is that comparison. It also measures the cross-encoder reranker, which had never run on a real model in this repository before.

## Method

The corpus, gold set, scoring and benchmark command are those of [retrieval-2026-11-07.md](retrieval-2026-11-07.md):
- **corpus:** 315 chunks, embeddings `bge-small-en-v1.5`;
- **gold set:** 26 paraphrased questions in `datasets/evaluation/retrieval_gold_v1.jsonl`;
- **scoring:** document-level hit@k, MRR@10 and recall@5 over the top 30 hits, `domain=all`, `type=document`.

All three configurations ran at the same time against the same PostgreSQL database (migrated to `0009`) and embedding cache. Each was a separate `uvicorn` on one 4-core x86_64 machine with no GPU.

| Label | Code | Reranker |
|---|---|---|
| `old` | `main` at `78dbdbb`, run from a git worktree: the API's inline ranking | none |
| `stack` | the ADR-006 commit: candidates from SQL, order from `ai/rag/retrieval/search_stack.py` | off (`FLAME_RERANKER_ENABLED=false`, the default) |
| `stack-rerank` | the same code | on: `cross-encoder/ms-marco-MiniLM-L-6-v2` through the router's `rerank` task, depth 20 |

```text
FLAME_API_ORIGIN=http://127.0.0.1:8101 python -m ai.rag.evaluation.flame_retrieval_benchmark --label old          --out …/retrieval-old-2026-11-12.json
FLAME_API_ORIGIN=http://127.0.0.1:8102 python -m ai.rag.evaluation.flame_retrieval_benchmark --label stack        --out …/retrieval-stack-2026-11-12.json
FLAME_API_ORIGIN=http://127.0.0.1:8103 python -m ai.rag.evaluation.flame_retrieval_benchmark --label stack-rerank --out …/retrieval-stack-rerank-2026-11-12.json
```

The benchmark writes the `git_commit` of the checkout it runs from (`b6e83c6`), not that of the server. The JSON files were therefore corrected by hand to name the code under test (`git_commit`, `code_under_test`).

## Results

| Configuration | hit@1 | hit@3 | hit@5 | MRR@10 | recall@5 | p50 latency | max latency |
|---|---|---|---|---|---|---|---|
| `old` (API inline ranking) | 0.81 | 0.88 | 0.96 | 0.86 | 0.83 | 34 ms | 70 ms |
| **`stack`** (ai/rag, default) | **0.81** | **0.88** | **0.96** | **0.86** | **0.83** | 37 ms | 76 ms |
| `stack-rerank` | **0.88** | **0.92** | 0.96 | **0.91** | **0.86** | 546 ms | 687 ms |

- **The ADR-006 gate is met.** For all 26 questions, the `stack` top-5 document list is identical to `old`'s. The new code reorganises the ranking without changing it, and costs about 3 ms per search.
- **The reranker helps on this gold set, with one regression.** It changes the first relevant rank of 5 questions:

  | Question | Fused rank | Reranked rank |
  |---|---|---|
  | RG-07 | 4 | **1** |
  | RG-11 | 4 | **1** |
  | RG-24 | 2 | **1** |
  | RG-13 | 3 | **2** |
  | RG-19 | 1 | 4 |

  RG-22 (BASS-II hypothesis) is still missed by all three configurations.
- **The reranker costs about 0.5 s per search on CPU**, roughly 15× the unreranked latency. `/api/chat` runs up to six searches per question (the full question plus up to five key terms), so reranking adds about 3 s to an uncached chat answer.

## Decision taken from this report

- `/api/search` and `/api/chat` now run on the `ai/rag` stack; the API's inline ranking is removed (ADR-006).
- **Reranking stays off by default.** The gain (+0.08 hit@1, +0.05 MRR@10) comes from 26 AI-authored questions that no human has reviewed: one question moves hit@1 by 0.04. The cost is a second model on every search, a 0.5 s latency floor, and a model that must be cached for offline use. Enable it with `FLAME_RERANKER_ENABLED=true` where that latency is acceptable. Whether to make it the default is the Lead's call once the gold set is reviewed.

## Known limitations

- 26 questions; one question moves hit@1 by 0.04. The gold set is AI-authored and not yet human-reviewed.
- Labels are document-level, so the reranker's passage-level choices are scored only through each document's first appearance.
- Latency was measured with three API instances sharing four cores, and the cross-encoder ran on CPU. A GPU, or a dedicated host, would change the cost.
- Answer quality (faithfulness, citation precision) is still not measured: no language model was available here.

## Changelog
- 1.0.0 (2026-11-12): first run: the ADR-006 gate (old vs stack) and the reranker.
