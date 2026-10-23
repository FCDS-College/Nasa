# Context builder

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Eman | Draft | 0.2.0 | 2026-10-14 | M2 (audit fix) | `ai/rag/context/context_builder.py`, `ai/rag/citations/citation_manager.py` |

Checked against the code at commit `5888580` (branch `Eman`). The earlier version of this file described intended behaviour; this version describes what the code does and marks every divergence. **Planned** = not in code.

## 1. Purpose

The context builder turns ranked evidence into a bounded, ordered context string that keeps the identity of every chunk.

## 2. Input

| Design said | Code does |
|---|---|
| User query + reranked chunks + citation metadata + token budget | `ContextBuilder.build(results)` takes **only** the ranked results (best first): a list of `{"chunk": {...}}` dicts. It does not receive the query or citation metadata. |
| Configurable token budget | The budget is set in the constructor and counted in **characters**: `max_chunks=5`, `max_characters=4000`. No tokens are counted. |

## 3. Processing, as implemented

| Design step | Status | What the code does |
|---|---|---|
| Relevance filtering | Not in the builder | Done earlier: vector minimum score (0.7) in `VectorSearchService` and the evidence check in `RAGRetrievalPipeline.retrieve`. |
| Deduplication | Partly | Skips a chunk whose `chunk_id` was already selected. Near-duplicate or overlapping text (chunks overlap by design) is **not** detected. |
| Evidence selection | Rank only | Takes chunks in the order given. No source-quality score and no diversity rule. |
| Ordering | Preserved | Keeps the reranker's order; it does not reorder. |
| Budget check | Implemented, in characters | Stops at `max_chunks`, or when adding the next chunk would exceed `max_characters`. It stops at the first chunk that does not fit (`break`); it does not look for a smaller chunk that would still fit. |
| Compression | **Planned** | Not implemented. Chunks are included whole and unmodified. |

## 4. Scientific uncertainty

Because chunks are never shortened or rewritten, words such as "may", "approximately" or "inconclusive" stay in the context exactly as in the source. The rule that any future compression must keep uncertainty, numbers, conditions and citations stays valid but only matters once compression exists (**Planned**).

## 5. Source preservation

Each selected source keeps `chunk_id`, `document_id`, `document_version`, `text`, `metadata` and, when present, `locator` (taken from `chunk["locator"]` or `chunk["metadata"]["locator"]`). The context string is `"[<chunk_id>]\n<text>"` parts joined by a blank line.

Important: the string in `EvidenceBundle.context` is **not** what the language model sees. `GroundedAnswerComposer` renders its own `<evidence>` blocks from `bundle.evidence` (see `prompts.md`). The context string is kept for display and backward compatibility.

## 6. Output

`ContextBuilder.build` returns `{"context": str, "sources": list}`. `CitationManager.attach_citations` then adds `citations`, giving `{"context", "sources", "citations"}`. The fields `items` and `token_count` from the earlier design **do not exist**.

## 7. Evidence

| Claim | Code | Test command | Result |
|---|---|---|---|
| Builder and citations behave as described | `ai/rag/context/context_builder.py`, `ai/rag/citations/citation_manager.py` | `python -m pytest -q tests/unit/test_context_builder.py tests/unit/test_citation_manager.py` | Part of Eman's full run `python -m pytest -q tests/unit` at commit `34c9849`: **83 passed** (2026-10-13). |

## 8. Known limitations

- The budget is in characters, so it does not match any model's token limit (per-model budgets are **Planned**, Sub-phase 2H).
- Stopping at the first chunk that does not fit can leave the budget unused.
- `HybridSearchService` returns up to `top_k` chunks even when their score is 0, so a zero-score chunk can reach the context when fewer than `top_k` chunks are relevant (reported to the owner; not changed in this documentation task).
- No near-duplicate removal; overlapping chunks can repeat the same sentence.

## 9. Changelog

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-10-14 | Rewritten to match the code at `5888580`; divergences from the earlier design listed. |
| 0.1.0 | Day 1 | Initial design text (not verified against code). |

## 10. ملخص بالعربي

الـ builder بياخد النتايج المترتبة بس (مش الـ query ولا token budget)، والـ budget بالـ characters (5 chunks و4000 حرف). بيمنع تكرار نفس الـ chunk_id بس، ومفيش compression. والنص اللي بيروح للـ LLM بيتبني في الـ composer مش من الـ context string.
