# ADR-006: One retrieval stack

- **Status:** Accepted (2026-11-07). Owner of the decision: Eman (E1), with the Lead. Accepted on the Lead's instruction; Eman's approval is recorded in ADR index 1.2.0. Partly implemented: see ADR index 1.3.0.
- **Date:** 2026-10-12

## Context
There are two retrieval implementations:
- the API's own lexical + pgvector search in `apps/api/flame_api/main.py` and `vector_index.py`;
- Eman's `ai/rag` package (hybrid search, reranker, context builder, citation manager), which is not wired into the API.

The lexical and semantic results are appended, not rank-fused, and semantic search runs only on page 1 (Phase 2 Plan §2.1 row 1, item M2).

## Decision (proposed)
`ai/rag` becomes the retrieval stack and the API calls it:
- Reciprocal Rank Fusion of lexical and semantic results on every page and filter;
- the cross-encoder reranker reached through the router's `rerank` task (`ai/providers/local/cross_encoder.py`, registered when `FLAME_RERANKER_ENABLED=true`);
- query rewrite stored next to the original query.

The API's current search stays until `ai/rag` passes the M11 benchmark at least as well, then it is retired.

## Consequences
- Embeddings for `ai/rag` must come from the router's `embed.*` tasks, so offline behaviour and model identity stay consistent with the published index (ADR-002).
- This ADR stays "Proposed" until Eman accepts it; M2 is not delivered by PR #14.

## Links
Phase 2 Plan M2; `docs/ai/retrieval-evaluation.md`; [ADR-003](ADR-003-provider-neutral-model-router.md).
