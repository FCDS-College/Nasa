# Update Report: Eman (Engineer 1, AI / RAG / Context Engineering)

**Reviewed:** `main` @ `f9ee52f` (all four engineer branches are already merged into it) · **Basis:** MVP plan §15 (Engineer 1), §16 daily table, §18 (RAG metrics), §22 (Definition of Done)
**Verification:** tests run in a clean Python venv (numpy, scikit-learn, pydantic, pypdf, pytest). `sentence-transformers` was not installed.

## Verdict: 5 / 10 against the MVP scope (retrieval core is solid; the answer path does not exist)

## Plan requirements vs. delivered

| Plan item (Engineer 1) | Day | Status | Evidence |
|---|---|---|---|
| RAG/MAG interfaces, prompt registry outline | 1 | Partial | Policy docs exist (`docs/ai/prompts.md`, `cag-policy.md`, `mag-policy.md`). **No prompt registry in code.** |
| Retrieval DTOs / key design | 2 | Done | `ai/rag/dto.py` (pydantic DTOs), `tests/unit/test_dto.py` |
| Chunk/context requirements | 3 | Done | `ingestion/chunker.py`, `context/context_builder.py`, `docs/ai/document-context-schema.md` |
| Hybrid retrieval / rerank prototype | 4 | Done | `retrieval/{vector,keyword,hybrid}_search.py`, `reranking/reranker.py`, `metadata_filter.py`, 33 unit tests pass |
| Grounded answer composer, citation validation, abstention | 5 | **Missing** | `citations/citation_manager.py` formats citations; no composer, no validator, no abstention logic anywhere in `ai/` |
| Context budget / caching hooks | 6 | Partial | Context builder exists; no cache keys or hooks in code |
| Query rewrite / hybrid tuning | 7 | **Missing** | No rewrite code |
| Image-context guardrails, interpretation template, analysis + evidence flow | 8-11 | **Missing** | Nothing in `ai/` touches CV output. The only interpretation path is the AURA call in `apps/api` (written by the Lead) |
| Response/retrieval cache, session MAG | 12 | **Missing** | Only policy docs; no Redis/cache/session code |
| Retrieval regression suite | 13 | Partial | `evaluation/evaluate_retrieval.py` runs on `build_test_chunks()` (synthetic text), not the real corpus; no gate/threshold |
| Answer/citation audit | 14 | Not possible | There is no answer to audit |

MVP Definition of Done items owned here: **cited RAG, CAG with version-aware invalidation, session MAG: none are demonstrable today.**

## What was good
- Clean package layout (`ai/rag/{ingestion,embeddings,retrieval,reranking,context,citations,evaluation}`) that matches §14.
- Real tests with a deterministic fake embedding service (`tests/conftest.py`), including failure-case and no-substring-matching tests.
- DTOs carry the fields the API contract needs.

## Defects found (and what was done)
| # | Finding | Action |
|---|---|---|
| 1 | `ai/rag/ingestion/pdf_loader.py` imported `src.ingestion.document` (pre-restructure path). The module could not be imported, so the PDF ingestion path was dead. | **Fixed** → `ai.rag.ingestion.document` |
| 2 | `tests/unit/test_reranker.py` and `test_keyword_search.py` imported `src.*`; both failed. | **Fixed** |
| 3 | `test_ingestion.py` read `data/raw/20000034017.pdf` (folder no longer exists). | **Fixed** → `docs/research/20000034017.pdf` |
| 4 | No dependency manifest: a fresh venv cannot import `ai.rag` (`sklearn`, `pydantic`, `pypdf`, `sentence-transformers`). | **Added** `ai/requirements.txt` |
| 5 | `tests/test_dto.py` sat outside `tests/unit/`. | **Moved** |
| 6 | `test_embeddings.py::test_embedding` downloads a real model; fails offline / in CI without the model. | Not changed. Mark as an opt-in test or mock it. |
| 7 | `datasets/evaluation/rag_gold.jsonl` (6 cases) is about a **ship fire** (`scene-12`, `engine_room_blueprint.pdf`), not microgravity combustion, so it cannot measure retrieval over the NASA corpus. | Not changed. Needs a rewrite with real `ev_` IDs (see Next steps). |

**Test result after fixes:** 60 passed, 1 deselected (`test_embedding`, needs the model) across `tests/unit`, `tests/cv`, `tests/eval/test_provenance.py`; 33 of those are the RAG unit tests.

## Next steps (priority order)
1. Build the answer composer with citation validation and abstention (Day 5). This is the largest gap and blocks the "RAG answers cite resolvable evidence" Definition-of-Done item.
2. Replace the gold set with real questions whose `expected_evidence_ids` resolve to ingested PSI/NTRS chunks; report Recall@k/MRR/nDCG (§18) on it and gate on a threshold.
3. Implement cache keys (corpus version + prompt version + model) and session MAG with scope and expiry; both can be written and tested against in-memory stores first.
4. Run retrieval against the real ingested corpus (`datasets/` + the API's chunk table) rather than synthetic chunks.
5. Add a prompt registry module with versioned prompts so Ziad's gates can record the prompt version (§18).
