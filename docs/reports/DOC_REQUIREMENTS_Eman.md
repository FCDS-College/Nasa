# Documentation Requirements: Eman (Engineer 1, NLP / RAG / Context Engineering)

| | |
|---|---|
| **Phase** | Phase 2: Advanced Scientific Intelligence Platform |
| **Issued** | 2026-10-10 by the Lead (Anas) |
| **Your branch** | `Eman` (branch fresh from `main` for each task) |
| **Basis** | [Phase 2 Plan](https://github.com/FCDS-College/Nasa/blob/main/docs/plan/PHASE2_PLAN.md): §2 carry-over items **M2, M3, M4, M5, M13** and **Workstream D**; **Sub-phase 2H, Task 5** (Phase 2 Plan §7A); MVP Plan §5.1, §6, §19 |
| **Reviewers** | Lead (Anas) for every document. Ziad (E5) for anything with metrics. Anas (E2) for anything touching evidence, graph or knowledge versions. |

---

## 1. Why this matters

You own how Flame answers questions: retrieval, prompts, caching, memory, Graph RAG and Graph Memory. The rest of the team can only integrate, test and evaluate what is written down. The audit on 2026-10-10 found that `docs/ai/*.md` describe intended behavior that the code does not do yet. For example, CAG and MAG are documented but not implemented, and the `ai/rag` package is not used by the API. From now on, **a document describes what the code actually does**, and any planned behavior is marked as planned.

## 2. Rules for every document you write

1. **Location and format:** Markdown in the path given in §3, in English (an Arabic summary at the end is optional).
2. **Header block:** start every document with the table below.

   | Owner | Status | Version | Last updated | Plan items | Code paths |
   |---|---|---|---|---|---|
   | Eman | Draft / In review / Approved | 0.1.0 | YYYY-MM-DD | e.g. M2, D4 | e.g. `ai/rag/retrieval/` |

3. **Evidence over claims:** every "implemented" statement links to the file path, the commit, and the test command plus its result. Copy numbers (Recall@k, latency, hit rates) from a generated report or harness output, and say which run produced them. Never type numbers in by hand.
4. **Docs ship with code:** a PR that changes behavior must update the matching document in the same PR. The Lead will not merge a PR whose docs are out of date.
5. **Versions:** prompts, cache-key schemes, memory schemas and retrieval configurations carry a version string (semver), and each document ends with a **Changelog** section.
6. **Scientific integrity:** use the claim labels *observed / measured / estimated / inferred / hypothesized*. Never present an association as causation. Every example answer must show its evidence IDs.
7. **Limitations:** every design document ends with a **Known limitations** section.
8. **Safety:** no API tokens, `.env` values or real user conversations. Use synthetic examples only.
9. **Diagrams:** Mermaid or ASCII inside the Markdown, not screenshots.

## 3. Required documents

| ID | Document | Path | Covers | Due (Phase 2 week) |
|---|---|---|---|---|
| E1-1 | Retrieval pipeline design | `docs/ai/retrieval-pipeline.md` | M2 | Week 1 |
| E1-2 | Prompt registry | `docs/ai/prompts.md` (rewrite) | M3 | Week 1 |
| E1-3 | Grounded generation and abstention policy | `docs/ai/grounded-generation.md` | M3 | Week 2 |
| E1-4 | CAG implementation | `docs/ai/cag-policy.md` (rewrite) | M4 | Week 3 |
| E1-5 | Session MAG implementation | `docs/ai/mag-policy.md` (rewrite) | M5 | Week 3 |
| E1-6 | Multimodal interpretation flow | `docs/ai/multimodal-interpretation.md` | M13 | Week 3 |
| E1-7 | Scientific NLP pipeline | `docs/ai/nlp-pipeline.md` | D1 | Week 4 |
| E1-8 | Graph RAG design | `docs/ai/graph-rag.md` | D4 | Week 6 |
| E1-9 | Graph Memory design | `docs/ai/graph-memory.md` | D5 | Week 6 |
| E1-10 | Retrieval and Graph RAG evaluation results (with Ziad) | `docs/ai/retrieval-evaluation.md` (rewrite) | C3, D7 | Week 4 baseline, Week 8 final |

## 4. Required contents

### E1-1 Retrieval pipeline design (M2)
- **Consolidation decision:** today two retrieval stacks exist (`ai/rag/` and `apps/api/flame_api/main.py` with `vector_index.py`). State which one survives, what is deleted or moved, and how the API calls it. Agree this with the Lead as an ADR.
- **Stage diagram:** query → (rewrite) → lexical + dense → fusion → filters → dedup → rerank → context. For each stage give the input/output DTO and the class or function name.
- **Fusion:** the method (e.g. RRF), its parameters (`k`, weights) and how it behaves on page 2+ and with experiment filters. Today those cases skip the semantic results.
- **Reranker:** model name and version, candidate-set size, score logging. Today `ai/rag/reranking/reranker.py` passes the hybrid score through; document the real reranker that replaces it.
- **Query rewrite:** when it runs, and how the original and rewritten queries are both stored.
- **Versions recorded per request:** embedding model, chunker, reranker, corpus/knowledge version.
- **Failure behavior:** what happens when the vector index or the reranker is down (no silent fallback to an uncited answer).

### E1-2 Prompt registry (M3)
- A table of every prompt: ID, version, purpose, model capability needed, input variables, output schema, file path, content hash.
- How evidence is delimited from instructions (prompt-injection defense, MVP §19).
- A rule for when a prompt change requires a new version, and the evaluation run that approved each version.

### E1-3 Grounded generation and abstention policy (M3)
- Exact criteria for an **evidence-insufficient** response: thresholds, zero retrieved passages, contradictory evidence.
- How claim labels are assigned and checked.
- Citation validation: how every cited ID is checked against the retrieved set, and what happens to dropped citations (`citations_not_in_retrieved_evidence_removed`).
- At least 5 synthetic worked examples: supported, partially supported, missing evidence, contradictory evidence, and an injection attempt inside a document.

### E1-4 CAG implementation (M4)
- A cache inventory table: cache type, key format with namespace (e.g. `rag:v3:corpus:<ver>:rerank:<ver>:{hash}`), value, TTL, and **invalidation trigger**.
- The dependency-manifest schema stored with each entry.
- How the knowledge-version publication event (from Anas, E2) invalidates entries. Link to `docs/data/KNOWLEDGE_VERSIONING.md`.
- Where `cache_hit` comes from in the `/api/chat` response. It must be Flame's own value, not AURA's.
- Metrics exposed (hit rate, p50/p95 saved) and how to read them.

### E1-5 Session MAG implementation (M5)
- Memory record schema: scope, actor, origin (user / extracted / system summary), confidence, created, expires, superseded_by, source/evidence refs.
- How `conversation_id` is issued and how `memory_used` is disclosed in responses and in the UI.
- Retention, deletion and expiry policy. Show a cross-user leakage test and a contamination test, and link both.
- An explicit statement that memory is never merged into evidence passages.

### E1-6 Multimodal interpretation flow (M13)
- A sequence diagram: analysis result + retrieved evidence → interpretation, with no AURA required.
- Which `AnalysisResult` fields may be used, and which claims are forbidden (e.g. temperature from RGB).
- How each interpretation statement carries a label class and evidence IDs.

### E1-7 Scientific NLP pipeline (D1)
- Entity types (the D1 list) with a definition and one synthetic example each.
- Extraction method per task (rule, model or LLM), model version, and confidence semantics.
- Source-location preservation (document, page, offsets) for every extracted record.
- Precision/recall/F1 per extractor, taken from Ziad's harness.

### E1-8 Graph RAG design (D4)
- Entity resolution rules and ambiguity handling.
- Traversal limits (hops, fan-out, timeouts) and how graph and vector candidates are merged and reranked.
- The association-versus-causation guard and how confounders are surfaced.
- The D4 worked example traced step by step with synthetic IDs.

### E1-9 Graph Memory design (D5)
- A clear separation between **Scientific Graph Memory** and **Session Graph Memory**: storage, access control, retention and deletion for each.
- How Session Graph Memory extends the M5 store.
- Review rules before anything is promoted into scientific memory.

### E1-10 Retrieval and Graph RAG evaluation results (C3, D7)
- A variant comparison table (standard / hybrid / graph-only / hybrid+graph / graph+rerank) generated by Ziad's harness. Include run ID, commit, benchmark version and checksum.
- Results per question category (single-doc, cross-doc, multi-hop, missing evidence, contradiction).
- A conclusion stating which component improved which metric, with any regressions listed.

## 5. Existing documents to fix

| File | Problem found in the 2026-10-10 audit | Action |
|---|---|---|
| `docs/ai/cag-policy.md`, `docs/ai/mag-policy.md` | They describe policies that are not implemented | Rewrite as E1-4 and E1-5; mark anything still planned as **Planned** |
| `docs/ai/prompts.md` | Not a versioned registry | Rewrite as E1-2 |
| `docs/ai/context-builder.md`, `docs/ai/citation-provenance.md`, `docs/ai/document-context-schema.md` | Not verified against the code | Check each against `ai/rag/context/` and `ai/rag/citations/`; fix or mark divergences |
| `docs/ai/retrieval-evaluation.md` | No generated numbers | Rewrite as E1-10 |
| `ai/README.md` | No module map | Add a table: path, purpose, entry point, tests |
| Public functions in `ai/rag/**` | Missing docstrings | Docstrings stating inputs, outputs, raised errors and versioned behavior |

## 6. Recurring documentation

- **Weekly note**, `docs/reports/WEEKLY_Eman.md` (append a section each week): what was done (with commit and PR links), what is in progress, blockers, and which documents changed.
- **PR description:** the documents updated, plus the tests run and their output.

## 7. Acceptance checklist (the Lead checks this before approving)

- [ ] Every document in §3 exists at its path, with the header block and a changelog.
- [ ] Every "implemented" claim links code, a commit and a test, and every metric links a run ID.
- [ ] Every item in §5 is fixed.
- [ ] Each document matches the code at the commit it cites.
- [ ] Known limitations are stated.
- [ ] Ziad has signed off on the metrics documents (E1-10) and Anas (E2) on the knowledge-version contract (E1-4).

---

## 8. Sub-phase 2H: Hybrid AI Execution (added 2026-10-10)

The Phase 2 Plan now includes **Sub-phase 2H (§7A)**: Flame must keep working when the internet, cloud models or external AI services (including AURA) are unavailable. The Lead owns the provider contracts, the router and the local runtime. **You own Task 5: local RAG and offline scientific knowledge access** (P0 for lexical and vector retrieval; P1 for the graph part, after D4 in Week 5).

### 8.1 Additional required document

| ID | Document | Path | Covers | Due (Phase 2 week) |
|---|---|---|---|---|
| E1-11 | Offline RAG behaviour | `docs/ai/offline-rag.md` | 2H Task 5 | Week 4 (vector and lexical), Week 5 (graph) |

**E1-11 must contain:**
- The offline RAG flow: local query processing → hybrid retrieval (vector + graph) → evidence filtering and reranking → local LLM synthesis → citation and provenance validation → a response with evidence and limitations. Name the function for each stage.
- **Local-LLM adaptations:** context budget for smaller context windows, prompt variants per local model, and structured-output validation and retry rules.
- **Disclosure rules:**
  - Show the `knowledge_version` and last-sync time when an answer may be out of date.
  - Never claim the latest NASA or NIST information unless it is stored locally.
  - Distinguish "external search unavailable" from "local retrieval found nothing".
- The no-fabricated-citations rule, how it is enforced offline, and how evidence is kept separate from interpretation.
- What is cached for offline reuse (research results, retrieval IDs) and how cache entries record the provider and mode.
- **Local vs cloud results:** on the same benchmark through Ziad's harness, which feeds H-7. Name the run IDs.

### 8.2 Updates to your existing documents

| Document | Add |
|---|---|
| E1-1 Retrieval pipeline | The local reranker; behaviour when the reranker or vector index is unavailable offline |
| E1-2 Prompt registry | For each prompt version, the provider and model it was validated on (local vs cloud) |
| E1-3 Grounded generation | The offline disclaimers and the degraded-mode response wording |
| E1-4 CAG | Cache entries record provider, model and execution mode; which entries can be served offline |
| E1-6 Multimodal interpretation | The local LLM only interprets measured CV results and never overrides them |

### 8.3 Sign-offs you give

You review the Lead's **H-2** (hybrid architecture) and **H-4** (provider API contracts) for everything RAG depends on.

### 8.4 Acceptance (added to §7)

- [ ] E1-11 exists, and a disconnected test run answers a question about a locally indexed document with verifiable evidence references (Phase 2 Plan §7A.8).
- [ ] The §8.2 updates are made in E1-1 through E1-6.
