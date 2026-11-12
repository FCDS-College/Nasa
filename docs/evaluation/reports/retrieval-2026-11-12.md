# Retrieval evaluation: the ai/rag search stack and the reranker (2026-11-12)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas), built with Claude Code | Current (gold set still needs human review: Ziad, Eman) | 1.1.0 | 2026-11-12 | ADR-006, M11 | `ai/rag/retrieval/search_stack.py`, `apps/api/flame_api/main.py` (`search`), `ai/rag/evaluation/flame_retrieval_benchmark.py` |

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

## Decision taken from this report (superseded the same day: see the follow-up below)

- `/api/search` and `/api/chat` now run on the `ai/rag` stack; the API's inline ranking is removed (ADR-006).
- **Reranking stays off by default.** The gain (+0.08 hit@1, +0.05 MRR@10) comes from 26 AI-authored questions that no human has reviewed: one question moves hit@1 by 0.04. The cost is a second model on every search, a 0.5 s latency floor, and a model that must be cached for offline use. Enable it with `FLAME_RERANKER_ENABLED=true` where that latency is acceptable. Whether to make it the default is the Lead's call once the gold set is reviewed.

## Follow-up: reranking on by default (same day, after PR #29)

The Lead asked for reranking to be on by default. **The API image did not contain sentence-transformers**: it is only in `ai/requirements.txt`, which the Dockerfile does not install. So the default would have been `unavailable` in every deployment.

The provider now runs fastembed's ONNX export, `Xenova/ms-marco-MiniLM-L-6-v2`:
- fastembed is already in the image for embeddings, and it needs no PyTorch;
- on the same pairs it returns the same scores as `cross-encoder/ms-marco-MiniLM-L-6-v2`, to three decimals.

The benchmark was re-run on the same database, with one API instance per configuration:

| Configuration | hit@1 | hit@3 | hit@5 | MRR@10 | recall@5 | p50 latency |
|---|---|---|---|---|---|---|
| fused (reranker off) | 0.81 | 0.88 | 0.96 | 0.86 | 0.83 | 41 ms |
| fastembed, depth 20, passages ≤ 2000 chars | 0.88 | 0.92 | 0.96 | 0.91 | 0.88 | 704 ms |
| **fastembed, depth 10, passages ≤ 2000 chars (the default)** | **0.88** | **0.92** | 0.96 | **0.91** | **0.88** | 692 ms |
| fastembed, depth 10, passages ≤ 1000 chars (not adopted) | 0.88 | 0.92 | 0.96 | 0.91 | 0.84 | 388 ms |

- **Depth 10 scores exactly as depth 20** on this gold set, for half the model work, so the default depth is now 10 (`FLAME_RERANK_DEPTH`). In isolation the model scores 10 real 2000-character chunks in 676 ms and 20 in 1,309 ms. Inside the server the measured latency barely changed between the two, so latency there is not only the model.
- **Capping passages at 1,000 characters halves the latency but costs recall@5 (0.88 → 0.84).** The 2,000-character cap is kept.
- **Per question,** against the fused order:
  - better first relevant rank: RG-07 (4→1), RG-11 (4→1), RG-24 (2→1), RG-13 (3→2);
  - better recall@5: RG-01 and RG-20 (0.5→1.0), RG-07 (0.25→0.5);
  - worse: RG-19 (1→4).
- **Cost.** About 0.7 s per search on this shared 4-core machine. `/api/chat` searches up to six times per uncached question, so it can add several seconds.
- **First use.** The model (about 90 MB) is downloaded into `FLAME_EMBEDDING_CACHE_DIR` on the first search, which took about 7 s here. An offline deployment must prepare it first (`python -m ai.providers.local.cross_encoder prepare --cache-dir <dir>`); otherwise search falls back to the fused order with `reranking.status = "unavailable"`, and chat answers are not cached.
- Set `FLAME_RERANKER_ENABLED=false` where that latency or download is unacceptable.

## Known limitations

- 26 questions; one question moves hit@1 by 0.04. The gold set is AI-authored and not yet human-reviewed.
- Labels are document-level, so the reranker's passage-level choices are scored only through each document's first appearance.
- Latency was measured with three API instances sharing four cores, and the cross-encoder ran on CPU. A GPU, or a dedicated host, would change the cost.
- Answer quality (faithfulness, citation precision) is still not measured: no language model was available here.

## Changelog
- 1.0.0 (2026-11-12): first run: the ADR-006 gate (old vs stack) and the reranker.
- 1.1.0 (2026-11-12): follow-up: the reranker moves to fastembed ONNX and is on by default with depth 10; depth and passage-length variants measured.
