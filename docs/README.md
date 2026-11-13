# Documentation index

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current; kept current on every PR (PR template checkbox) | 1.2.2 | 2026-11-12 | G-1, G-3 | — |

**Status key:** Draft → In review → Approved. "Due Wn" means the document doesn't exist yet and is due in Phase 2 week n. "On branch X" means it exists only on that engineer's branch. Requirements per engineer:
- `docs/reports/DOC_REQUIREMENTS_Lead.md` and `DOC_REQUIREMENTS_Anas.md` on `main`;
- `DOC_REQUIREMENTS_<name>.md` on the branches `Eman`, `Princess`, `Belal` and `Ziad`.

## 1. Lead (Anas)

| ID | Document | Status | Last updated |
|---|---|---|---|
| L-1 | [ADRs 001–012](architecture/adr/README.md) | 001–012 Accepted; 006–009 built in PR #29 (index 1.4.0 lists what is still open); all signed off 2026-11-07 (Lead's confirmation) | 2026-11-12 |
| L-2 | [Architecture overview](architecture/overview.md) | In review | 2026-10-12 |
| L-3 | delivered as H-2 + H-4 | In review | 2026-10-12 |
| L-4 | [openapi.json](api/openapi.json) 0.6.0, [API_SCHEMAS.md](api/API_SCHEMAS.md), [CHANGELOG](api/CHANGELOG.md) | Current | 2026-11-12 |
| L-5 | [Index synchronization contract](architecture/index-sync-contract.md) | In review | 2026-10-12 |
| L-6 | [Background jobs](architecture/background-jobs.md) | In review (1.1.0: video checkpoints, cancellation) | 2026-11-12 |
| L-7 | [CI/CD and testing](operations/CI_CD.md) | In review | 2026-10-12 |
| L-8 | [Runbook](operations/RUNBOOK.md) | Draft (needs a clean-machine dry run) | 2026-10-12 |
| L-9 | [Observability](operations/OBSERVABILITY.md) | In review | 2026-10-12 |
| L-10 | [Security and access control](operations/SECURITY.md) | Current (0.7.0: admin scope, ADR-009 step 2) | 2026-11-12 |
| L-11 | [Release v0.1.0-mvp](releases/v0.1.0-mvp.md) | Tag approved, push pending; sign-offs pending | 2026-10-12 |
| L-12 | [AURA integration README](integration/README.md) (entry point, contract 0.6.0, 16 tools), [audit](integration/AURA_INTEGRATION_AUDIT.md), [API integration reference](integration/API_INTEGRATION_REFERENCE.md); [status report](integration/AURA_INTEGRATION_STATUS.md) §0 is history | Current | 2026-11-12 |
| H-1 | [Dependency audit](hybrid-ai/PHASE_2_HYBRID_AI_DEPENDENCY_AUDIT.md) | In review | 2026-10-12 |
| H-2 | [Hybrid AI architecture](hybrid-ai/PHASE_2_HYBRID_AI_ARCHITECTURE.md) | In review | 2026-10-12 |
| H-3 | [Local model registry](hybrid-ai/PHASE_2_LOCAL_MODEL_REGISTRY.md) | In review (checksums partly Pending) | 2026-10-12 |
| H-4 | [Hybrid AI API contracts](hybrid-ai/PHASE_2_HYBRID_AI_API_CONTRACTS.md) | In review | 2026-10-12 |
| H-5 | [Offline acceptance tests](hybrid-ai/PHASE_2_OFFLINE_ACCEPTANCE_TESTS.md) | Plan done; Level C evidence Pending | 2026-10-12 |
| H-6 | [Offline deployment guide](hybrid-ai/PHASE_2_OFFLINE_DEPLOYMENT_GUIDE.md) | Draft (needs an offline dry run) | 2026-10-12 |
| H-7 | [Benchmark report](hybrid-ai/PHASE_2_HYBRID_AI_BENCHMARK_REPORT.md) | Draft (feasibility numbers only) | 2026-10-12 |
| G-1/G-3 | this file | Current | 2026-10-12 |
| G-2 | [PR template](../.github/pull_request_template.md) | Current | 2026-10-12 |
| G-4 | [Week 1 status](reviews/PHASE2_WEEK_1.md) | Current | 2026-10-12 |
| G-5 | [Doc audit W4](reviews/DOC_AUDIT_WEEK_4.md), [W8](reviews/DOC_AUDIT_WEEK_8.md) | Scheduled | 2026-10-12 |
| G-6 | sign-off matrix in each `releases/*.md` | Pending | 2026-10-12 |

## 2. Anas (Engineer 2, data / knowledge base)

| ID | Document | Status | Last updated |
|---|---|---|---|
| E2-1 | [Source registry guide](data/SOURCE_REGISTRY.md) | In review | 2026-10-12 |
| E2-2 | [Ingestion pipeline](data/INGESTION_PIPELINE.md) | In review | 2026-10-12 |
| E2-3 | [Data dictionary](data/DATA_DICTIONARY.md) | In review (2.1.0: migrations to `0009`) | 2026-11-12 |
| E2-4 | [Provenance and lineage](data/PROVENANCE.md) | In review | 2026-10-12 |
| E2-5 | [Knowledge versioning](data/KNOWLEDGE_VERSIONING.md) | In review (needs Eman's sign-off) | 2026-10-12 |
| E2-6 | [Knowledge graph schema](data/KNOWLEDGE_GRAPH_SCHEMA.md) | Current (0.6.0: built from the PSI tables, ADR-007) | 2026-11-12 |
| E2-7 | [Data quality scoring](data/DATA_QUALITY_SCORING.md) | Draft (method authority: Ziad's rubrics, due W4) | 2026-10-12 |
| E2-8 | [Admin data operations](data/ADMIN_DATA_OPERATIONS.md) | Draft (0.7.0: admin scope) | 2026-11-12 |
| E2-9 | [NTRS report](data/NTRS_DATASET_REPORT.md), [NIST WebBook report](data/NIST_WEBBOOK_DATASET_REPORT.md), [DSI report](data/DSI_DATASET_REPORT.md) | In review | 2026-10-12 |
| E2-10 | [Offline data and sync](data/OFFLINE_DATA_AND_SYNC.md) | Draft (restore drill Pending) | 2026-10-12 |
| — | [Weekly note](reports/WEEKLY_Anas_E2.md) | Current | 2026-10-12 |

## 3. Other engineers (required docs; tracked here, written on their branches)

| Engineer | Documents (ID → path) | State on `main` |
|---|---|---|
| Eman (E1) | E1-1 `ai/retrieval-pipeline.md` W1 · E1-2 `ai/prompts.md` W1 · E1-3 `ai/grounded-generation.md` W2 · E1-4 `ai/cag-policy.md` W3 · E1-5 `ai/mag-policy.md` W3 · E1-6 `ai/multimodal-interpretation.md` W3 · E1-7 `ai/nlp-pipeline.md` W4 · E1-8 `ai/graph-rag.md` W6 · E1-9 `ai/graph-memory.md` W6 · E1-10 `ai/retrieval-evaluation.md` W4/W8 · E1-11 `ai/offline-rag.md` W4/W5 | MVP versions of `prompts`, `cag-policy`, `mag-policy`, `retrieval-evaluation`, `context-builder`, `citation-provenance`, `document-context-schema` and `assumptions-and-boundaries` exist; the Phase 2 rewrites are due |
| Princess (E3) | E3-1 `cv/pipeline.md` W1 · E3-2 `cv/measurement-definitions.md` W2 · E3-3 `cv/annotation-protocol.md` W1 · E3-4 `cv/evaluation-report.md` W2 · E3-5 model cards W2 · E3-6 `cv/video-ingestion.md` W2 · E3-7 `cv/temporal-analysis.md` W5 · E3-8 video contract W3 · E3-9 `cv/performance.md` W7 · E3-10 `cv/offline-operation.md` W6 | Under `docs/cv/`: [pipeline](cv/pipeline.md) (E3-1), [measurement definitions](cv/measurement-definitions.md) (E3-2), [annotation protocol](cv/annotation-protocol.md) (E3-3), [evaluation report](cv/evaluation-report.md) (E3-4), [video ingestion](cv/video-ingestion.md) (E3-6), [temporal analysis](cv/temporal-analysis.md) (E3-7), [video contract](cv/video-contract.md) (E3-8), [performance](cv/performance.md) (E3-9, estimates until benchmarked), [offline operation](cv/offline-operation.md) (E3-10); model card: [local model registry](hybrid-ai/PHASE_2_LOCAL_MODEL_REGISTRY.md#computer-vision). Path and filename fixed after the `Princess` merge. |
| Belal (E4) | E4-1 `frontend/architecture.md` W1 · E4-2 `frontend/screens.md` W1 · E4-3 W2 · E4-4 `frontend/admin-dashboard.md` W2/W7 · E4-5 W3 · E4-6 `frontend/testing.md` W3 · E4-7 W5 · E4-8 W7 · E4-9 W8 · E4-10 `frontend/offline-ux.md` W4/W7 | [implementation-summary](frontend/implementation-summary.md) (to be replaced by E4-1) |
| Ziad (E5) | E5-1 `evaluation/evaluation-plan.md` W1 · E5-2 benchmark datasheet W1/W2 · E5-3 W1 · E5-4 `evaluation/harness.md` W2 · E5-5 baseline scorecard W2 · E5-6 `evaluation/quality-rubrics.md` W4 · E5-7 W5 · E5-8 W5/W8 · E5-9 `evaluation/release-gate.md` W7 · E5-10 W8 · E5-11 `evaluation/offline-testing.md` W2/W8 · E5-12 W4/W8 | [provenance checklist](evaluation/provenance_checklist.md). Root-level `tests-eval-*.py` files arrived with 856ea5a (they look like flattened copies of `tests/eval/` files) and are not collected by pytest. |

## 4. Other documents

| Document | Status | Owner |
|---|---|---|
| **Final challenge deliverables (2026-11-07, updated 2026-11-12 for PR #27–#32):** [status](../FINAL_PROJECT_STATUS.md), [architecture](../FINAL_ARCHITECTURE.md), [test report](../FINAL_TEST_REPORT.md), [demo runbook](../DEMO_RUNBOOK.md), [presentation](../FINAL_CHALLENGE_PRESENTATION.md) | Current | Lead |
| [FLEX outcome model card and evaluation](evaluation/reports/flex-outcome-model.md), [retrieval evaluation](evaluation/reports/retrieval-2026-11-07.md), [significance of retrieval differences](evaluation/reports/retrieval-significance-2026-11-13.md), [embedder and reranker comparison](evaluation/reports/model-comparison-2026-11-13.md) | Current (human review pending: Ziad, Eman) | Lead |
| 2026-10-30 system audit: [status audit](reviews/SYSTEM_STATUS_AUDIT.md), [roadmap](plan/IMPLEMENTATION_ROADMAP.md), [implementation changelog](reviews/IMPLEMENTATION_CHANGELOG.md) | Current | Lead |
| [Readiness report](reviews/FINAL_SYSTEM_READINESS_REPORT.md) (2026-10-30 assessment, with a 2026-11-12 status update in §11) | Historical snapshot | Lead |
| [Phase 2 plan](plan/PHASE2_PLAN.md) | Current | Lead |
| [Frontend API contract](api/FRONTEND_API_CONTRACT.md), [service contracts](api/service-contracts.md) | MVP-era (contract 0.1.0) | Lead / Belal |
| [AURA integration requirements](integration/AURA_INTEGRATION_REQUIREMENTS.md) | Partly superseded (see L-12 §0) | Lead |
| [Combustion dataset analysis](data/COMBUSTION_DATASET_ANALYSIS.md), [Day 1 acquisition](data/DAY1_DATA_ACQUISITION.md), [P0 candidates](data/P0_CANDIDATES.md) | MVP working notes (status line at top) | Anas (E2) |
| [Day 2 tasks](plan/DAY2_TASKS.md) | Superseded by the Phase 2 plan | Lead |
| [Day 2 review](reviews/Flame%20in%20Freefall%20Day%202%20Review.md) | Historical | — |

## 5. Review matrix (G-3)

Taken from each engineer's requirements file. Every document also gets the Lead's review. The Lead's own documents get the sign-off named in `DOC_REQUIREMENTS_Lead.md` §3. Anas's E2 documents need at least one peer sign-off (Eman or Ziad), because the Lead and E2 are the same person.

| Document type | Reviewers |
|---|---|
| Anything with metrics or evaluation | Ziad (E5) |
| Evidence, graph, knowledge versions, corpus | Anas (E2) |
| Retrieval, caching, graph consumption, RAG/LLM benchmarks | Eman (E1) |
| Citation and evidence presentation in the UI | Eman (E1) |
| CV evaluation, overlays, measurement views | Princess (E3) |
| Overlay/artifact formats used by the UI; admin data operations | Belal (E4) |
| Annotation and evaluation docs (CV) | Ziad (E5) |
| Data and knowledge quality rubrics | Anas (E2) |
| API-facing schemas | Lead |
| L-1 ADRs | the affected engineer (ADR index) |
| L-2 overview | Eman, Princess |
| L-3 / H-2 / H-4 | Eman (H-2); Belal, Eman (H-4) |
| L-4 API | Belal |
| L-5 index sync | Anas (E2), Eman |
| L-6 jobs | Princess, Anas (E2) |
| L-7 CI/CD, L-9 observability | Ziad |
| L-8 runbook, H-6 deployment | any engineer who has dry-run it |
| L-10 security | Belal, Anas (E2) |
| L-11 release | Ziad (gate verdict) |
| H-1 | Anas (E2), Princess |
| H-3 | Ziad, Princess |
| H-5, H-7 | Ziad |

## Changelog
- 1.0.0 (2026-10-12): first index.
- 1.1.0 (2026-11-07): final challenge deliverables and evaluation reports.
- 1.1.1 (2026-11-07): L-1 row: ADR-006 to 009 Accepted, partly implemented. The header version, which still read 1.0.0, is corrected.
- 1.2.0 (2026-11-12): ADR-006 to 009 built (PR #29): L-1, L-4, L-6, L-10, L-12, E2-3, E2-6 and E2-8 rows.
- 1.2.1 (2026-11-12): final deliverables updated for the merged PR #30 and AURA-AI #232.
- 1.2.2 (2026-11-12): final deliverables cover PR #32; the readiness report is listed as a historical snapshot with its 2026-11-12 update.
