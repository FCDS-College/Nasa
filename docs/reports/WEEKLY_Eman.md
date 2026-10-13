# Weekly notes: Eman

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Eman | In review | 0.1.0 | 2026-10-12 | M2, M3, M4, M5, 2H Task 5 | `ai/`, `docs/ai/` |

(If this file already exists, keep the existing sections and append only the section below.)

## Week 1 (2026-10-10 to 2026-10-14)

### Done
- Code (branch `Eman`, no pull request opened yet):
  - `9319d65`: AI interfaces, prompt registry, grounded composer, CAG, session MAG, RRF fusion, cross-encoder reranker, query rewrite (rebased on the team's repo restructure).
  - `0fc94c3`: `FlameRAGService` wiring, merged `ai/README.md`, tests moved to `tests/unit/`.
  - `d7bf6b2`: cache metrics now record time saved (`compute_ms`).
  - `34c9849`: no-network end-to-end test.
- Documents: E1-1 `retrieval-pipeline.md` (`f0aa3a2`), E1-2 `prompts.md` and E1-3 `grounded-generation.md` (`c919766`), E1-4 `cag-policy.md` and E1-5 `mag-policy.md`, E1-11 `offline-rag.md` (this commit).
- Tests: `python -m pytest -q tests/unit` -> **81 passed** on Eman's machine at `0fc94c3`.

### In progress
- E1-6 `multimodal-interpretation.md` (needs `cv/contracts/analysis_result.json`).
- Fixes of `context-builder.md`, `citation-provenance.md`, `document-context-schema.md` against `ai/rag/context/` and `ai/rag/citations/`.
- Docstrings for public functions in `ai/rag/**`.

### Blockers and decisions needed
- The Lead must accept or change the retrieval consolidation ADR in `retrieval-pipeline.md` (adapter location, vector column migration, `/api/chat` built on `FlameRAGService`).
- Connecting `/api/search` and `/api/chat` to `FlameRAGService` is owned by the Lead.
- The real NASA corpus ingestion and Ziad's gold set are needed before any Recall@k or MRR number can be reported (E1-10).
- Anas (E2) must confirm the knowledge-version publication event that should call the cache invalidation methods (E1-4).

### Documents changed this week
`docs/ai/retrieval-pipeline.md`, `prompts.md`, `grounded-generation.md`, `cag-policy.md`, `mag-policy.md`, `offline-rag.md`, `ai/README.md`.

