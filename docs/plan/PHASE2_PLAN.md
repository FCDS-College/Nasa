# FLAME IN FREEFALL

## Phase 2 — Advanced Scientific Intelligence Platform

**Project:** NASA Space Apps — Flame in Freefall
**Phase:** Phase 2 — Post-MVP Implementation (follows the [MVP Plan](Nasa%20-%20MVP%20Plan.pdf))
**Duration:** 8 weeks, subject to baseline evaluation
**Team:** 6 engineers
**Infrastructure:** NVIDIA L40S GPU
**Core technologies:** FastAPI, Next.js, PostgreSQL, vector search, PyTorch, NLP, RAG, Graph RAG, Graph Memory, LLMs, and Computer Vision.

**Document status:** Plan of record, saved 2026-10-10. Phase 2 starts once the MVP is finished. The MVP items that were still unimplemented when this was saved are carried into Phase 2 as **Workstream 0** (Section 2). They must close before the Phase 2 baseline is measured.

**Sub-phase 2H, the Hybrid AI Execution System (§7A), added 2026-10-10:** a Lead-owned sub-phase that keeps the platform working when internet connectivity, cloud-hosted models or external AI services are unavailable. It runs in parallel with Workstreams A–D across all 8 weeks.

---

# 1. Phase 2 Objectives

Phase 2 turns the completed MVP into an integrated scientific research and intelligence platform.

The system must support:

1. Advanced image and video analysis for combustion research.
2. A dedicated Admin Data Management Dashboard.
3. Systematic evaluation and ranking of analytical models, LLMs, datasets, documents, evidence, and knowledge.
4. Professional NLP and RAG pipelines enhanced by Graph Memory and Graph RAG.
5. Cross-experiment scientific comparisons.
6. Reproducible analysis workflows with evidence and provenance.
7. Production-grade API contracts, observability, testing, and deployment.

## Core architectural principle

The platform must distinguish between four different concepts:

* **Data quality:** Is the source or dataset reliable, complete, and suitable for its intended use?
* **Knowledge quality:** Is a scientific claim supported, traceable, consistent, and sufficiently contextualized?
* **Model quality:** How accurately and efficiently does a model perform its intended task?
* **Answer quality:** Does the final response answer the question correctly using appropriate evidence?

These dimensions must be evaluated separately before being combined into any overall ranking.

---

# 2. MVP Completion Audit and Carry-over (Workstream 0)

**Audit date:** 2026-10-10. **Baseline commit:** `main` at `e73dcf1`.
**Method:** The MVP Plan's §5–§22 (layers, RAG/CAG/MAG, ingestion, data model, CV, model infrastructure, API, frontend, evaluation, security, and the Definition of Done) were checked against the code in `apps/`, `ai/`, `cv/`, `knowledge/`, `datasets/`, `infrastructure/`, `tests/` and `.github/`. The test suites were also run.

**Test status at audit time**

* `python -m pytest tests` (repo root): **69 passed**.
* `python -m pytest` inside `apps/api`: **69 passed**.
* `python -m pytest` from the repo root **fails at collection**: `apps/api/tests` raises `ModuleNotFoundError: No module named 'flame_api'`. Contributors therefore have no single test command, and no CI runs either suite.

## 2.1 MVP Definition of Done: status

| # | MVP Definition of Done (§22) | Status | What exists | What is missing |
|---|---|---|---|---|
| 1 | Scientific corpus searchable | ⚠️ Partial | `GET /api/search`: Postgres full-text (`to_tsvector`) plus pgvector semantic matches (`chunk_embedding`, migration `0003`). PSI combustion sources are registered and ingested. | Lexical and semantic results are **appended, not rank-fused**. Semantic search runs only on page 1 and is skipped when an experiment filter is set. NIST WebBook (P1) is not registered. The 3 NTRS PDFs in `docs/research/` are not registered or ingested. |
| 2 | RAG answers cite resolvable evidence | ⚠️ Partial | `POST /api/chat` retrieves Flame evidence and drops citations that aren't in the retrieved set (`citations_not_in_retrieved_evidence_removed`). | **Answer generation depends on AURA**, which the MVP Plan lists as a non-goal: with AURA disabled, chat returns `503 CHAT_UNAVAILABLE`. Flame has no LLM provider of its own. Eman's `ai/rag` package (hybrid search, reranker, context builder, citation manager) is **not wired into the API**, so there are two retrieval stacks. `Reranker` passes the hybrid score through with no cross-encoder. There is no query rewrite. `/api/chat` is excluded from OpenAPI. |
| 3 | CAG with version-aware invalidation | ❌ Not implemented | Redis runs, but only as the RQ job queue and for the health check. `cv/flame_cv.py` computes version-aware cache keys. | No embedding, retrieval or response cache and no dependency manifest. `cache_hit` in chat comes from AURA's response, not Flame. The analysis worker doesn't reuse prior results by cache key. There is no knowledge-version publication event that invalidates caches. |
| 4 | Session MAG with provenance and expiration | ❌ Not implemented | The frontend keeps chat history client-side (`ChatContext.tsx`). | No memory store, scope, expiry or provenance labels. `memory_used` is hard-coded to `false`, and `conversation_id` isn't used server-side. |
| 5 | CV produces structured measurements, confidence, and artifacts | ✅ Done (baseline) | `cv/flame_cv.py` v1.1.0: Otsu-contour segmenter, geometry and appearance features, quality flags, observed/measured/… labels, no RGB temperature claims, mask and overlay artifacts. Async `POST /api/analyses` runs on an RQ worker, with an optional HF Space provider. | Inference has **no PyTorch detector or segmenter** (the detector is heuristic). See row 10 for evaluation. |
| 6 | Image plus scientific retrieval workflow | ⚠️ Partial | An analysis can link to an `experiment_id`. Optional interpretation goes through AURA. | No orchestrated multimodal path in Flame that combines analysis facts with retrieved evidence. Without AURA, interpretation is `unavailable`. |
| 7 | FastAPI contracts stable and tested | ⚠️ Mostly | 69 API tests, `docs/api/openapi.json`, RFC 7807-style error envelope, read/write bearer tokens, request IDs. | MVP endpoints are missing: **`GET /api/documents` and `GET /api/experiments` (list)**. The frontend builds the experiment list from `search?q=flame&type=experiment`. `POST /api/analysis/image` shipped as `POST /api/analyses`, and that decision has no ADR. The only CI is the AURA contract dry run. |
| 8 | Next.js core workflow complete | ⚠️ Partial | 8 screens call the real API: dashboard, chat, search, evidence, experiments, analysis, history, status. | **Knowledge Explorer is mocked**: `fetchKnowledge()` returns `mockKnowledge`. There is no document list or document viewer; the evidence viewer works only by ID. There are no frontend tests. |
| 9 | Dockerized environment works | ✅ Done | `infrastructure/compose.yaml` runs postgres with pgvector, redis, minio, the api (migrate, seed, ingest) and the worker, with health checks. A Railway deployment exists. | A clean-environment run wasn't re-verified in this audit. The Railway configuration (`.railway/`) was committed in `780d89b`; document it in the runbook. |
| 10 | Evaluation corpus with a baseline report | ⚠️ Weak | `datasets/evaluation/rag_gold.jsonl` and a schema. `tests/eval/` holds notebooks, 33 test cases and a report. `ai/rag/evaluation/` holds retrieval metrics. | The gold set has **only 6 items** (2 dev, 2 validation, 2 holdout). The report covers 6 tests. The CV report says `segmentation: NOT_EVALUATED` because there are no ground-truth masks. There is no consolidated scorecard or release gate, and much of the harness is notebooks rather than runnable code. |
| 11 | Provenance from result to original source | ✅ Mostly | SHA-256 per file, `parser_version`, evidence `locator`, stable ULIDs, `ingestion_run` records, CV `pipeline_version`. | No OCR fallback or quarantine during ingestion. Notes from 2026-10-06, to re-verify: derived DSI frames have no `parent_file_id`, and the registry CSV doesn't validate against its schema. |
| 12 | Demo reproducible from a tagged release and runbook | ❌ Not done | — | **No git tags, no runbook and no ADRs.** `docs/architecture/` holds only `overview.md`. |

**Other MVP specification gaps**

* **§5.3 / §11 model infrastructure:** No `ModelRouter`, `LLMProvider` or `EmbeddingProvider` interfaces, and no Ollama or vLLM adapters. Provider independence, a core MVP principle, isn't implemented yet.
* **§4 / §12 observability:** Structured logs carry request IDs, but there is no OpenTelemetry tracing (API → orchestration → cache → retrieval → rerank → provider/CV → persistence).
* **§9 data model:** The tables are `source`, `file_record`, `document`, `document_chunk`, `experiment`, `experiment_condition`, `evidence`, `analysis_result`, `ingestion_run` and `chunk_embedding`. **Missing:** `KnowledgeEntity`, `KnowledgeRelation`, `Memory`, `CacheEntry`, `Model`, `Dataset` and `ImageAsset`.
* **§8 ingestion:** PDF parsing is page-level (PyMuPDF) only. There are no HTML or JSON parser adapters, no OCR for scanned PDFs (`cv/telemetry_ocr.py` reads video overlays, not documents), and no quarantine for invalid files.
* **§19 security:** No secret-scanning CI, and no adversarial prompt-injection cases in the evaluation set.
* **Phase 2 consistency:** §12 of this plan defers AURA as a core dependency, but chat and interpretation currently *require* AURA. Item M1 below fixes this.

## 2.2 Carry-over backlog

Priority **P0** blocks the Phase 2 baseline measurement (Week 1–2 gate). **P1** must close by the end of Week 3. **P2** is folded into the named Phase 2 workstream.

| ID | Carry-over item | MVP ref | Owner | Priority | Feeds Phase 2 |
|---|---|---|---|---|---|
| **M1** | Provider-neutral `ModelRouter` with `LLMProvider` and `EmbeddingProvider` contracts, an **Ollama adapter** (local) and a **vLLM adapter** (L40S). `/api/chat` must answer without AURA, and AURA becomes one optional provider behind the router. **Delivered as the first slice of Sub-phase 2H, Tasks 2–4 (§7A.6)**, so there is only one router. | §5.3, §11, §24 | Lead (Anas) | P0 | C2, B5, D4, 2H |
| **M2** | **One retrieval stack.** Wire `ai/rag` into the API or retire the duplicate, then add rank fusion (e.g. RRF) of lexical and semantic results on every page and filter, a real cross-encoder reranker that logs its version and scores, and a query rewrite stored alongside the original query. | §6 RAG | Eman (E1) + Lead | P0 | C3, D4, D7 |
| **M3** | Grounded generation and abstention **owned by Flame**: an evidence-insufficient response, claim labels (observed/measured/estimated/inferred/hypothesized), and versioned prompts in a prompt registry. | §6, §10, §19 | Eman (E1) | P0 | C2, D4 |
| **M4** | **CAG**: Redis caches for query embeddings, retrieval IDs and scores, response envelopes and analysis results, each with a dependency manifest and version-aware invalidation. Add a knowledge-version publication event, report a real `cache_hit`, and make the worker reuse analyses by cache key. | §5.6, §6 CAG | Eman (E1), Lead, Anas (E2), Princess (E3) | P1 | C3, B9 (System Ops) |
| **M5** | **Session MAG**: a memory table with scope, actor, origin, confidence, expiry and superseded-by; server-side `conversation_id`; `memory_used` disclosure. This is the base for D5 Session Graph Memory. | §6 MAG | Eman (E1) | P1 | D5 |
| **M6** | API gaps: `GET /api/documents` and `GET /api/experiments` list endpoints with filters and pagination. Put `/api/chat` into OpenAPI and keep AURA from calling it with an exclusion on AURA's side. Write an ADR on the `/api/analyses` naming. | §12 | Lead (Anas) | P0 | B1, A4 |
| **M7** | Frontend: replace `mockKnowledge` (interim: entities from experiment conditions; final: the D2 graph API), use the list endpoint on the experiment page, add a document list and viewer, show real cache and memory indicators, and add UI tests. | §13 | Belal (E4) | P1 | B1, B4 |
| **M8** | Missing §9 tables: `KnowledgeEntity`, `KnowledgeRelation`, `Memory`, `CacheEntry`, `Model`, `Dataset`, `ImageAsset`. Coordinate the schemas with D2 (graph) and C1 (model registry) so the work isn't built twice. | §9 | Anas (E2) + Lead | P1 | D2, D3, C1 |
| **M9** | Ingestion completeness: OCR fallback with confidence for scanned PDFs, quarantine for invalid files, HTML and JSON parser adapters, registration and ingestion of the 3 NTRS PDFs in `docs/research/`, NIST WebBook registration (P1 source), DSI derived-frame lineage (`parent_file_id`), and registry CSV schema validation. | §7, §8 | Anas (E2) | P1 | B2, B3, C4 |
| **M10** | CV evaluation: reviewed ground-truth masks, IoU and Dice, detection precision and recall, and a PyTorch segmentation candidate compared with the Otsu baseline. Today `evaluation_report.json` reads `NOT_EVALUATED`. | §10, §18 | Princess (E3) + Ziad (E5) | P0 | A2, A3, C1 |
| **M11** | Evaluation corpus and harness: grow `rag_gold.jsonl` from 6 items to a versioned, reviewed benchmark with dev, validation and holdout splits, missing-evidence questions and prompt-injection cases. Turn the notebooks into a runnable harness that records commit, dataset checksum, model and prompt. Produce a consolidated scorecard and a release gate. Set the benchmark size in Week 1. | §18 | Ziad (E5) | P0 | C1–C3, D7 |
| **M12** | Platform: CI (Python lint and tests for `tests/` and `apps/api`; web lint, typecheck and build) and a fix for root `pytest` collection; OpenTelemetry spans; ADR-001 (monorepo), ADR-002 (pgvector first), ADR-003 (model router) and ADR-004 (AURA boundary); a runbook covering deploy, backup and restore; secret scanning; and a tagged **`v0.1.0-mvp`** release. | §4, §12, §19, §22 | Lead (Anas) | P0 | §8 integrated release |
| **M13** | An orchestrated multimodal path: analysis facts plus retrieved evidence produce an interpretation, with claim classes enforced and no AURA required. | §16 Day 11, §23 | Eman (E1) + Lead | P1 | D4, A2 |

**Rule:** The Phase 2 baseline (Week 1, "Verified MVP baseline") is measured **only after M1, M2, M3, M6, M10, M11 and M12 have landed**. Before that, Phase 2 comparisons such as hybrid versus MVP RAG, or LLM A versus LLM B, have no valid baseline.

---

# 3. Updated System Architecture

```text
                         Next.js Frontend
                                |
             +------------------+------------------+
             |                  |                  |
             v                  v                  v
      Research Dashboard   Admin Dashboard   Analysis Workspace
             |                  |                  |
             +------------------+------------------+
                                |
                         FastAPI Backend
                                |
                         AI Orchestrator
                                |
                         Workflow Router
                                |
          +---------------------+---------------------+
          |                     |                     |
          v                     v                     v
    Professional NLP       Computer Vision       Analytics Engine
          |                     |                     |
          v                     v                     v
     Advanced RAG          Video Analysis       Model Evaluation
          |                     |                     |
          v                     v                     v
       Graph RAG         Temporal Measurements   Model Ranking
          |
          v
      Graph Memory
          |
          v
     Evidence Validation
          |
          v
     Scientific Synthesis
          |
          +----------------------+--------------------+
                                 |
                         Scientific Intelligence
                                 |
          +----------------------+----------------------+
          |                      |                      |
          v                      v                      v
      PostgreSQL           Vector Search           Graph Store
          |                      |                      |
          +----------------------+----------------------+
                                 |
                           Object Storage
                                 |
               Documents / Images / Videos / Artifacts
```

This diagram describes logical components, not mandatory separate services. Keep the first implementation modular, and extract services only when operational requirements justify it.

The **Workflow Router** sits on the provider-neutral **Model Router** from M1. No Phase 2 component calls Ollama, vLLM, AURA or a hosted LLM directly.

The Model Router is **connectivity-aware**: it chooses between cloud and local providers according to the execution mode. §7A.4 shows the cloud/local split, and §7A.5 defines the execution modes.

## Required architectural rules

* Every scientific result must be traceable to its inputs.
* Graph relationships must have provenance.
* Knowledge ranking must not be confused with scientific truth.
* Model selection must depend on measured task performance.
* Video processing must support asynchronous execution.
* LLMs must not be responsible for authoritative numerical calculations.
* Existing MVP APIs should remain compatible wherever practical.

---

# 4. Workstream A — Advanced Video Analysis

**Primary owner:** Engineer 3 — Computer Vision and PyTorch
**Supporting owners:** Lead Engineer, Engineer 2, Engineer 5
**Schedule:** Weeks 2–6
**Builds on:** M10 (CV ground truth and evaluation), plus the existing `cv/video_training.py`, `cv/video_embedding.py` and `cv/telemetry_ocr.py` prototypes.

## A1. Video ingestion

Implement:

* Video format validation.
* File-size and duration limits.
* Metadata extraction.
* Frame-rate and resolution detection.
* Timestamp preservation.
* Configurable frame sampling.
* Video and frame identifiers.
* Processing status and error reporting.
* Source asset provenance.

The original video must remain immutable. Store processed frames, segmentation masks and other derived artifacts separately.

## A2. Flame analysis

Develop a pipeline containing:

1. Frame preprocessing.
2. Flame detection.
3. Flame segmentation.
4. Region and contour extraction.
5. Frame-to-frame tracking.
6. Temporal measurement.
7. Quality assessment.
8. Structured result generation.

Potential metrics include:

* Segmented flame area.
* Flame centroid.
* Apparent flame length.
* Contour variation.
* Frame-to-frame area change.
* Temporal persistence.
* Tracking stability.
* Flicker frequency, where sampling and signal quality support a valid estimate.

Report physical units only when the necessary calibration and measurement assumptions are available.

## A3. Video evaluation

Create a reviewed dataset of representative combustion videos.

Evaluate:

* Segmentation IoU and Dice.
* Detection precision and recall.
* False-positive rate.
* Tracking consistency.
* Measurement repeatability.
* Processing latency.
* GPU memory usage.

Record the model version, configuration, sampling policy and preprocessing parameters for each analysis.

## A4. Video analysis API

Provide versioned contracts for:

* Video submission.
* Processing status.
* Analysis results.
* Frame-level measurements.
* Temporal summaries.
* Overlay and artifact retrieval.
* Cancellation and failure reporting.

Use background jobs for long-running video analyses. Extend the existing RQ worker and `/api/analyses` job model rather than adding a second job system.

### Deliverable

A reproducible video-analysis pipeline integrated with the experiment registry, dashboard, and scientific evidence system.

---

# 5. Workstream B — Admin Data Management Dashboard

**Primary owner:** Engineer 4 — Frontend and Visualization
**Backend owner:** Lead Engineer
**Data owner:** Engineer 2
**Schedule:** Weeks 2–7
**Builds on:** M6 (list endpoints), M7 (frontend gaps), M8 (missing data-model tables), M9 (ingestion completeness).

The Admin Dashboard is an operational data-management interface, separate from the public-facing research dashboard.

## B1. Data inventory

Provide searchable inventories for:

* Scientific sources.
* Documents.
* Experiments.
* Datasets.
* Images.
* Videos.
* Extracted tables and figures.
* Knowledge entities and relationships.
* Vector indexes.
* Graph indexes.
* Analysis results.

Each record should show its status, source, version, processing history and quality information.

## B2. Ingestion management

Administrators should be able to:

* Register an approved data source.
* Start an ingestion job.
* Inspect acquisition manifests.
* Monitor processing progress.
* View failed files.
* Retry failed jobs.
* Inspect validation errors.
* Review duplicate detection.
* View checksums and metadata.
* Reprocess selected assets.

A retry must not create duplicate documents, experiments or graph relationships.

## B3. Document and dataset management

Provide workflows for:

* Inspecting extracted text.
* Reviewing document metadata.
* Correcting approved metadata fields.
* Linking documents to experiments.
* Reviewing OCR and table-extraction results.
* Viewing dataset completeness.
* Inspecting provenance.
* Flagging low-quality or conflicting records.
* Approving records for indexing.

Corrections must be audited. Preserve the original source data and distinguish original values from administrator corrections.

## B4. Knowledge Graph management

The dashboard should provide:

* Entity search.
* Relationship exploration.
* Orphaned entity detection.
* Duplicate entity detection.
* Conflicting relationship inspection.
* Provenance inspection.
* Graph extraction job monitoring.
* Controlled entity merging.
* Reindexing and graph rebuild operations.

Destructive operations must require appropriate authorization and confirmation.

## B5. Model and evaluation management

Administrators should be able to inspect:

* Registered models.
* Model versions.
* Evaluation runs.
* Benchmark versions.
* Metric results.
* Model rankings.
* Deployment status.
* Failed evaluations.
* Model and index compatibility.
* Active model routing configuration.

Model promotion should be controlled by explicit acceptance criteria, not by an automatic ranking score alone.

## B6. Access control and auditability

Implement:

* Role-based access control.
* Separate read and write permissions.
* Administrative action logs.
* Authentication and session controls.
* Protected data-ingestion operations.
* Confirmation for destructive actions.
* Audit records for metadata changes and model promotions.

The MVP has static read and write bearer tokens behind an `AuthContext`-style boundary. B6 replaces them with real identities and roles without redesigning the routes.

### Deliverable

A secure administrative interface for managing the complete scientific data lifecycle, from ingestion to indexing, evaluation, and controlled publication.

---

# 6. Workstream C — Evaluation and Ranking Framework

**Primary owner:** Engineer 5 — Evaluation and Research Intelligence
**Technical owner:** Lead Engineer
**Supporting owners:** Engineers 1, 2, and 3
**Schedule:** Weeks 1–8
**Builds on:** M11 (benchmark and harness), M10 (CV ground truth), M1 (router, so LLMs can be swapped under identical conditions).

This framework must evaluate analytical models, LLMs, datasets, documents, evidence and knowledge records.

It must not treat these different objects as interchangeable.

## C1. Analytics model evaluation

Register each model with:

* Model identifier.
* Version.
* Task.
* Architecture.
* Training-data provenance, where known.
* Evaluation dataset.
* Configuration.
* Hardware requirements.
* License.
* Intended use.
* Known limitations.

Evaluate each model against the task it actually performs.

### Computer Vision metrics

| Task                  | Evaluation metrics                                            |
| --------------------- | ------------------------------------------------------------- |
| Flame detection       | Precision, recall, F1                                         |
| Flame segmentation    | IoU, Dice                                                     |
| Video tracking        | Tracking consistency and identity stability, where applicable |
| Temporal analysis     | Measurement error and repeatability                           |
| Inference performance | Latency, throughput, GPU memory                               |

### NLP and retrieval metrics

| Task                    | Evaluation metrics                          |
| ----------------------- | ------------------------------------------- |
| Document extraction     | Field-level precision and recall            |
| Entity extraction       | Precision, recall, F1                       |
| Relationship extraction | Precision, recall, F1                       |
| Retrieval               | Recall@K, Precision@K, nDCG@K               |
| Reranking               | nDCG@K, MRR                                 |
| Citation validation     | Source and location validity                |
| Answer generation       | Correctness, evidence support, completeness |

Use expert-reviewed ground truth for scientific evaluations wherever feasible.

## C2. LLM evaluation

Evaluate candidate LLMs using the same controlled benchmark.

Measure:

* Scientific correctness.
* Evidence adherence.
* Citation correctness.
* Unsupported-claim rate.
* Appropriate abstention.
* Instruction adherence.
* Structured-output validity.
* Numerical reasoning when relevant.
* Response latency.
* Token consumption.
* GPU memory requirements.
* Reproducibility and output stability.

Include questions whose answers are missing from the knowledge base. A reliable model must recognize insufficient evidence instead of inventing a conclusion.

Use deterministic checks wherever possible, and blinded human review for scientific judgments that can't be reliably automated.

## C3. RAG pipeline evaluation

Evaluate the complete pipeline, not only the underlying LLM.

Test:

1. Query interpretation.
2. Retrieval.
3. Reranking.
4. Context construction.
5. Evidence selection.
6. Answer generation.
7. Citation validation.
8. Final response quality.

Compare pipeline variants using the same benchmark and controlled conditions.

Examples:

* Dense retrieval versus hybrid retrieval.
* Different chunking strategies.
* Different embedding models.
* Different rerankers.
* Different graph retrieval strategies.
* Different context-selection policies.
* Different LLMs using the same evidence.

This shows which component actually improves the final result.

## C4. Data quality ranking

Assess source and dataset quality across separate dimensions.

| Dimension            | Example signals                                          |
| -------------------- | -------------------------------------------------------- |
| Provenance           | Verifiable source, stable identifier, traceable origin   |
| Completeness         | Required metadata and fields present                     |
| Integrity            | Checksums, parsing validity, duplicate detection         |
| Consistency          | Compatible identifiers, units, and metadata              |
| Scientific relevance | Match to the intended research task                      |
| Temporal relevance   | Appropriate publication or acquisition period            |
| Label quality        | Reliability of annotations and review process            |
| Suitability          | Appropriate conditions and coverage for the intended use |

Not every source needs a publication date, and not every scientific dataset needs human labels. Use task-specific criteria.

## C5. Knowledge quality ranking

Evaluate individual claims, entities, relationships and evidence records.

Possible dimensions:

* Source traceability.
* Directness of evidence.
* Extraction quality.
* Corroboration.
* Context completeness.
* Contradiction status.
* Relationship confidence.
* Recency, where relevant.
* Applicability to the query.

Distinguish between:

* Source-reported facts.
* Machine-extracted facts.
* Derived measurements.
* Model-generated interpretations.
* Unverified hypotheses.

A frequently repeated claim is not necessarily true. Several documents copied from the same original source must not count as independent corroboration.

## C6. Ranking engine

Implement separate ranking functions:

* `rank_models()`
* `rank_datasets()`
* `rank_documents()`
* `rank_evidence()`
* `rank_knowledge_records()`

Each function must have documented inputs, outputs, weights or decision rules, and evaluation procedures.

Don't introduce one universal ranking formula for all these objects.

For example, model ranking should be task-specific:

```text
Model candidates
      |
      v
Task compatibility filter
      |
      v
Minimum quality thresholds
      |
      v
Scientific evaluation
      |
      v
Performance and resource evaluation
      |
      v
Task-specific ranking
      |
      v
Human-approved promotion
```

A model that performs well on flame segmentation must not automatically be considered the best model for scientific question answering.

### Deliverable

A repeatable evaluation framework with versioned benchmarks, comparable results, task-specific rankings, and controlled model promotion.

---

# 7. Workstream D — Professional NLP, RAG, Graph Memory, and Graph RAG

**Primary owner:** Engineer 1 — NLP, RAG, and Context Engineering
**Knowledge owner:** Engineer 2
**Integration owner:** Lead Engineer
**Evaluation owner:** Engineer 5
**Schedule:** Weeks 2–8
**Builds on:** M2 (single retrieval stack with fusion and reranking), M3 (grounded generation), M4 (CAG), M5 (session MAG), M8 (entity and relation tables), M13 (multimodal path).

## D1. Professional NLP pipeline

Develop a scientific NLP pipeline that supports:

* Document classification.
* Scientific entity recognition.
* Experiment identifier extraction.
* Scientific relation extraction.
* Metadata extraction.
* Table and figure association.
* Scientific terminology normalization.
* Unit and quantity extraction.
* Claim extraction.
* Contradiction detection.
* Query classification.
* Query expansion.
* Evidence-aware summarization.

Every extracted record must keep a link to its original source location when one is available.

### Initial entity types

* Experiment.
* Investigation.
* Scientific publication.
* Dataset.
* Combustion phenomenon.
* Fuel.
* Oxidizer.
* Environmental condition.
* Measurement.
* Instrument.
* Physical quantity.
* Material.
* Research finding.
* Hypothesis.

Extend the schema only when actual research requirements justify it.

## D2. Scientific Knowledge Graph

Introduce an explicit graph representation of scientific entities and relationships. It implements the MVP's `KnowledgeEntity` and `KnowledgeRelation` (M8) rather than a parallel schema.

### Suggested entities

```text
Document
Experiment
Dataset
Asset
Researcher
CombustionPhenomenon
Fuel
Oxidizer
EnvironmentalCondition
Measurement
Instrument
ScientificClaim
Evidence
Analysis
```

### Suggested relationships

```text
Document       --DESCRIBES-------> Experiment
Experiment     --USES------------> Fuel
Experiment     --USES------------> Oxidizer
Experiment     --HAS_CONDITION---> EnvironmentalCondition
Experiment     --PRODUCES--------> Dataset
Dataset        --CONTAINS--------> Measurement
Asset          --BELONGS_TO------> Experiment
Document       --SUPPORTS--------> ScientificClaim
Evidence       --SUPPORTS--------> ScientificClaim
ScientificClaim--CONTRADICTS-----> ScientificClaim
Analysis       --DERIVED_FROM----> Dataset
Analysis       --REFERENCES------> Evidence
```

These are candidate relationship types. Only create relationships supported by extracted information or explicitly curated records.

Every important edge should carry provenance, extraction method, confidence semantics and review status.

## D3. Graph storage strategy

Use PostgreSQL for authoritative records and transactional metadata.

Choose a graph-storage implementation based on:

* Query requirements.
* Deployment complexity.
* Available integrations.
* Operational expertise.
* Data size.
* Performance measurements.

Possible strategies include:

1. PostgreSQL tables for nodes and edges.
2. A PostgreSQL graph extension or compatible graph-query implementation.
3. A dedicated graph database, when traversal and operational requirements justify it.

Don't introduce a dedicated graph database solely because Graph RAG is required.

The system must keep stable identifiers across PostgreSQL, the vector index and the graph representation. The existing ULIDs and SHA-256 content addresses are the shared keys.

## D4. Graph RAG

Graph RAG should complement conventional retrieval, not replace it.

Implement:

* Entity-aware query interpretation.
* Entity resolution.
* Graph neighborhood retrieval.
* Multi-hop relationship traversal.
* Graph-based context construction.
* Hybrid graph and vector retrieval.
* Relationship-aware reranking.
* Evidence aggregation.
* Source-backed response generation.

### Example

Research question:

"Which experimental conditions are associated with the documented differences in flame behavior between these two investigations?"

Expected workflow:

```text
Research Question
       |
       v
Identify Experiment Entities
       |
       v
Resolve Experiment IDs
       |
       +-----------------------+
       |                       |
       v                       v
 Graph Traversal         Hybrid RAG
       |                       |
       +-----------+-----------+
                   |
                   v
          Merge Candidate Evidence
                   |
                   v
         Check Source Provenance
                   |
                   v
         Compare Experimental Data
                   |
                   v
         Identify Confounders
                   |
                   v
          Evidence-Backed Answer
```

The system must distinguish an observed association from a causal relationship.

## D5. Graph Memory

Graph Memory should represent relationships and contextual state that plain text-based memory can't represent as effectively.

Implement two separate forms of memory.

### Scientific Graph Memory

Stores persistent, source-grounded scientific relationships:

* Experiments and conditions.
* Documents and datasets.
* Measurements and methods.
* Claims and supporting evidence.
* Conflicting claims.
* Derived analytical findings.

Scientific Graph Memory is part of the scientific knowledge system and must follow the provenance and review rules.

### Session Graph Memory

Stores relevant conversational context:

* Current research objective.
* Selected experiments.
* Previously examined evidence.
* User-selected filters.
* Pending analytical questions.
* Relationships between current tasks.

Session Graph Memory must stay separate from authoritative scientific records. It extends the session MAG store from M5; it doesn't replace it.

It should support retention limits, access controls and deletion policies.

## D6. Graph updates and consistency

Build a versioned graph ingestion pipeline:

```text
Validated Document
       |
       v
Entity and Relation Extraction
       |
       v
Entity Resolution
       |
       v
Relationship Validation
       |
       v
Provenance Attachment
       |
       v
Graph Update
       |
       v
Consistency Checks
       |
       v
Vector / Graph Index Synchronization
```

Updates must be idempotent and recoverable.

When a source is corrected or removed, the system must be able to identify the affected entities, edges and derived indexes. The knowledge-version publication event (M4) triggers the related cache invalidation.

## D7. Evaluate Graph RAG

Compare:

* Standard RAG.
* Hybrid RAG.
* Graph-only retrieval.
* Hybrid RAG with graph retrieval.
* Graph RAG with reranking.

Use questions that require different levels of reasoning:

* Single-document questions.
* Cross-document questions.
* Entity-resolution questions.
* Multi-hop relationship questions.
* Cross-experiment comparison questions.
* Contradiction and missing-evidence questions.

Measure retrieval quality, final answer correctness, evidence coverage, latency and resource usage.

### Deliverable

A professional scientific NLP and retrieval system combining structured extraction, hybrid RAG, provenance-aware Graph RAG, and persistent scientific Graph Memory.

---

# 7A. Sub-phase 2H — Hybrid AI Execution System (Workstream E)

**Primary owner:** Lead Engineer — Anas Ibrahim (AI infrastructure, backend orchestration, model routing, storage integration, reliability and deployment)
**Supporting owners:**
- Eman (E1): local RAG behaviour (Task 5).
- Princess (E3): offline CV and video (Task 6).
- Belal (E4): offline-aware UI (Task 8).
- Ziad (E5): local-versus-cloud benchmark and offline acceptance tests.
- Anas (E2): local data, backups and synchronization data rules (Task 7).

**Schedule:** Weeks 1–8, in parallel with Workstreams A–D (§7A.7)
**Builds on:**
- M1: its model router *is* the router this sub-phase extends.
- M2: retrieval stack.
- M4: caches.
- M12: observability and runbook.
- Workstream A: video.
- Workstream D: Graph RAG.

**Lead documentation for this sub-phase:** `docs/reports/DOC_REQUIREMENTS_Lead.md` §8.

## 7A.1 Objective

Implement a **Hybrid AI Execution System** that lets Flame in Freefall keep operating when internet connectivity, cloud-hosted models or external AI services become unavailable.

The system must combine:

* Cloud-hosted LLMs and AI services, when available.
* Locally hosted LLMs for scientific NLP, research assistance and selected reasoning tasks.
* Local computer vision models for flame and video analysis.
* Local embedding and reranking models for semantic retrieval.
* Local scientific knowledge and Graph RAG for evidence-based responses.
* Local data storage, task queues and cached results to support disconnected operation.

**Primary requirement:** losing internet connectivity must not stop the whole system. Instead, the system automatically switches to the best available local capabilities and clearly communicates any limitations.

## 7A.2 How this sub-phase fits the rest of the plan

* **One router, not two.** The M1 `ModelRouter` is the connectivity-aware router of Task 3. M1's Week 1–2 slice delivers three things: the provider contracts, one local LLM through Ollama, and AURA as an optional cloud provider. That slice is enough for `/api/chat` to answer without AURA before the baseline is measured. Tasks 2–4 then complete the router: health, circuit breakers, execution modes, and the full local runtime and model manifest.
* **"Local" means where a model runs, not what hardware it uses.** The following count as **local** when they are reachable on the same (possibly disconnected) network: Ollama or llama.cpp on a workstation, vLLM on the L40S, fastembed embeddings, and the `cv/flame_cv.py` pipeline. AURA, hosted LLM APIs and the Hugging Face Space CV provider are **external**. If the L40S can only be reached over the internet, Offline-Only mode treats it as external.
* **No duplicate registries.** The local model registry and capability manifest reuse the `Model` table (M8) and the C1 model cards. The offline knowledge base is the existing PostgreSQL + pgvector + MinIO corpus. Benchmarks run on Ziad's harness (M11).
* **Deployment:** the Railway deployment stays for connected demos. Offline deployment runs `infrastructure/compose.yaml` on local hardware.
* **Graph part of Task 5:** Task 5 is P0 for lexical and vector retrieval. Its graph-retrieval part depends on D4 (Week 5), so it is P1.

## 7A.3 Known external dependencies (starting point for Task 1, from the 2026-10-10 audit)

| Component | External dependency today | Current behaviour when offline | Required local path |
|---|---|---|---|
| `/api/chat` answer generation | AURA, hosted on Railway (`FLAME_AURA_BASE_URL`) | No fallback: returns `503 CHAT_UNAVAILABLE` | Local LLM through the router (M1, Tasks 2–4) |
| Image interpretation | AURA | Interpretation status becomes `unavailable` | Local LLM interpretation of measured results (M13, Task 6) |
| Embeddings | `fastembed` runs `BAAI/bge-small-en-v1.5` locally, but **downloads the weights from Hugging Face on first use** | Fails if the model cache is empty | Pre-download, record a checksum, and set an offline cache flag (Task 4) |
| CV inference | Local by default; the optional `FLAME_CV_PROVIDER=hf_space` calls a Hugging Face Space | Local provider works; HF Space fails | Force the local provider in Offline-Only mode (Task 6) |
| Frontend fonts | `apps/web/app/layout.tsx` loads Google Fonts at runtime | Browser falls back to system fonts | Self-host the fonts (Task 8) |
| Deployment | Railway (cloud) | Not reachable | Local Compose stack (Task 7, H-6) |
| Container images | Docker Hub pulls (`pgvector`, `redis`, `minio`) | A fresh machine can't start the stack | Pre-pull or export the images (H-6) |
| Data acquisition | `psi.nasa.gov` API, NTRS | No new data | Use already-acquired local mirrors only, and disclose sync age (Task 5) |

Task 1 completes this inventory. It also covers auth, the background workers, CI and every remaining route.

## 7A.4 Target architecture

```text
                    Next.js Frontend
                           |
                           v
                     FastAPI Backend
                           |
                           v
                  AI Orchestrator / Router
                           |
             +-------------+-------------+
             |                           |
             v                           v
       Cloud AI Providers          Local AI Runtime
       (when available)            (always preferred
             |                      when offline)
             |                           |
             |                 +---------+----------+
             |                 |         |          |
             |                 v         v          v
             |              Local LLM   Local CV   Local NLP
             |              Inference   Models     Models
             |                 |         |          |
             +-----------------+---------+----------+
                               |
                               v
                     Local Intelligence Layer
                               |
                  +------------+-------------+
                  |            |             |
                  v            v             v
              Local RAG    Graph RAG     Analytics
                  |            |             |
                  +------------+-------------+
                               |
                               v
                      Local Data Services
                               |
              +----------------+----------------+
              |                |                |
              v                v                v
          PostgreSQL       Vector Store     Object Storage
          / Metadata       / Embeddings     / Video / Images
```

The local intelligence layer must not depend on a cloud provider for its core functions.

The orchestrator chooses between cloud and local execution based on connectivity, task requirements, model availability, resource capacity and configured policies.

## 7A.5 Execution modes

| Mode                   | Behavior                                                                       | Purpose                                             |
| ---------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------- |
| Cloud-Preferred Hybrid | Use cloud models when available and appropriate; keep a local fallback         | Normal connected operation                          |
| Local-First            | Prefer locally hosted models, with permitted cloud fallback                    | Fewer external dependencies and better continuity   |
| Offline-Only           | Block external AI and data requests; use only local resources                  | Disconnected operation                              |

The active mode is configurable in two places: an environment variable (proposed name: `FLAME_AI_EXECUTION_MODE=cloud_preferred|local_first|offline_only`) and the Admin Dashboard "Models and LLMs" module (§10). Every mode change is audited (B6).

Offline-Only mode must never silently send data to external providers.

## 7A.6 Lead Engineer tasks

### Task 1 — Audit existing AI dependencies (P0)

Before implementation, identify every component that depends on the internet or an external service.

**Actions**

* Inspect all FastAPI routes, orchestration services, AI providers, background workers and storage integrations.
* Identify cloud LLM dependencies in NLP, research search, RAG, summarization and analysis.
* Identify external embedding, reranking, transcription and computer vision dependencies.
* Check whether authentication, frontend assets, metadata access and database operations can work locally.
* Separate the data sources that are unavailable offline from those already cached or acquired locally.
* Document the local resource requirements of every proposed model.

**Deliverable:** `docs/hybrid-ai/PHASE_2_HYBRID_AI_DEPENDENCY_AUDIT.md`. Contents:
- component and dependency inventory;
- current online-only operations;
- required local replacements;
- fallback behavior for each component;
- known limitations while disconnected;
- GPU, RAM, CPU and disk requirements;
- implementation priorities.

**Acceptance:** every critical AI dependency has one of the following documented: a fallback, a defined degraded mode, or the reason it can't operate offline.

### Task 2 — Implement the unified AI provider interface (P0)

Create a provider abstraction so the application can switch between cloud and local inference without changing business logic.

**Required interfaces:**
- chat and text generation;
- structured JSON output;
- embedding generation;
- reranking;
- image inference;
- video-analysis inference;
- speech transcription, if it is in the selected offline feature set.

Provider-specific code stays behind these interfaces.

**Required capabilities:**
- provider registration and discovery;
- model capability metadata;
- health checks, request timeouts, error normalization, retry policies and cancellation;
- model availability checks;
- token and resource limits;
- provider-specific configuration;
- request tracing and metrics.

Use typed request and response contracts, and keep the existing API contracts wherever possible.

**Placement in this repository.** MVP §14 already reserves `ai/providers/` and `ai/routing/`. Use them rather than creating a parallel `app/ai/` tree:

```text
ai/
  providers/
    contracts/   chat.py, structured.py, embeddings.py, reranking.py,
                 vision.py, video.py, transcription.py
    cloud/       aura.py (from apps/api/flame_api/aura_integration.py), hosted-LLM adapters
    local/       ollama.py, llamacpp.py, vllm.py, fastembed_embeddings.py,
                 cross_encoder.py, flame_cv.py (wraps cv/flame_cv.py)
  routing/
    registry.py  health.py  router.py  policies.py
```

These existing modules move behind the contracts: `apps/api/flame_api/aura_integration.py`, `apps/api/flame_api/hf_cv.py`, and the embedder in `apps/api/flame_api/vector_index.py`.

**Acceptance**
* Application services don't depend directly on any specific cloud provider.
* Local and cloud implementations satisfy the same applicable interfaces.
* A provider can be replaced through configuration, without rewriting business logic.
* Provider failures return normalized, traceable errors.

### Task 3 — Implement connectivity-aware model routing (P0)

Build the router that selects an appropriate model for each task.

**Routing inputs:**
1. the requested task;
2. the required model capabilities;
3. current network and provider health;
4. local model availability;
5. GPU and RAM availability;
6. estimated task complexity;
7. latency requirements;
8. context-window requirements;
9. whether the operation needs internet-only information;
10. whether the operation is permitted in Offline-Only mode.

**Routing flow**

```text
Incoming AI Request
        |
        v
Identify Task and Required Capabilities
        |
        v
Check Operating Mode
        |
        v
Check Provider and Model Availability
        |
        +---------------------------+
        |                           |
        v                           v
Suitable Cloud Model          Suitable Local Model
Available and Permitted?      Available and Ready?
        |                           |
       Yes                         Yes
        |                           |
        v                           v
Execute Cloud Request        Execute Local Request
        |                           |
        +-------------+-------------+
                      |
                      v
             Validate the Result
                      |
                      v
        Attach Model and Provenance Metadata
                      |
                      v
               Return Response
```

When the cloud provider fails, the router selects a suitable local model instead of retrying the unavailable provider again and again.

**Required policies**
* Use short, bounded connectivity checks, not a check on every token or inference step.
* Keep provider health state, with a temporary circuit breaker for providers that fail repeatedly.
* Apply configurable timeouts and retry limits.
* Don't retry non-idempotent operations automatically unless idempotency controls protect them.
* Route by capability, not just by model name.
* Keep a task-specific fallback registry.
* Prevent routing loops.
* Never silently replace a scientific vision task with a text-only LLM.
* Never report an external research search as successful when no external connection was available.

**Acceptance**
* A failed cloud request can fall back to a compatible local provider.
* The router doesn't block the application while it waits on a failed provider.
* If no compatible local model is available, the request returns a clear, actionable degraded-mode response.
* All routing decisions are visible in logs and metrics.

### Task 4 — Deploy a local model runtime (P0)

Deploy and manage a local inference runtime that can host small models on the available workstation or server.

Evaluate **Ollama** and **llama.cpp** for quantized local language-model inference, behind a runtime abstraction so the project isn't permanently tied to either one. Where the hardware justifies it, also evaluate a GPU inference server; vLLM on the L40S is the MVP Plan's choice for this.

**Initial model categories**

| Capability      | Local Model Requirement                                 | Primary Use                                    |
| --------------- | ------------------------------------------------------- | ---------------------------------------------- |
| General LLM     | Small instruction-tuned model                           | Chat, summaries, basic reasoning               |
| Scientific NLP  | Instruction-tuned model validated on scientific prompts | Research explanation and structured extraction |
| Embeddings      | Compact embedding model (current: `BAAI/bge-small-en-v1.5` via fastembed) | Local semantic retrieval |
| Reranking       | Compact cross-encoder, if the resource budget allows    | Evidence relevance ranking                     |
| Computer Vision | Existing `cv/flame_cv.py` pipeline or a selected lightweight vision model | Image-based flame analysis   |
| Video Analysis  | Local frame sampling, tracking and CV pipeline (Workstream A) | Video processing                         |
| Speech-to-Text  | Compact local transcription model, if required          | Extracting speech from video                   |

**Model selection rules.** Don't choose models by popularity. Benchmark the candidates, using Ziad's harness, on:
- scientific task accuracy;
- memory footprint;
- cold-start time and warm inference latency;
- throughput;
- quality loss from quantization;
- CPU-only operation and GPU acceleration compatibility;
- license and deployment constraints;
- compatibility with the project's existing interfaces.

Start with one reliable local model per critical capability rather than downloading several overlapping models.

**Deliverables:**
- local inference runtime configuration;
- model registry and capability manifest (reusing the `Model` table from M8);
- model download and verification procedure;
- model version and checksum records;
- startup health checks;
- resource-limit configuration;
- model warm-up and loading policies.

**Acceptance:** after installation and model preparation, the following run without internet access:
- at least one compatible local LLM;
- one local embedding model;
- the existing or selected local CV pipeline.

### Task 5 — Implement local RAG and offline scientific knowledge access (P0; the graph part is P1)

Make sure the research assistant can answer from locally available scientific documents and knowledge when external search is unavailable. Eman owns the retrieval and generation behaviour; the Lead owns routing and integration.

**Required capabilities:**
- local document retrieval;
- local embedding generation;
- local vector search;
- graph-based retrieval over locally available graph data;
- hybrid vector and graph retrieval;
- local evidence reranking;
- source-aware response generation;
- cached research results;
- document and evidence provenance;
- explicit disclosure of missing or inaccessible sources.

**Offline RAG flow**

```text
Research Question
       |
       v
Local Query Processing
       |
       v
Hybrid Retrieval
  |            |
  v            v
Vector Search  Graph Retrieval
  |            |
  +------+-----+
         |
         v
Evidence Filtering and Reranking
         |
         v
Local LLM Synthesis
         |
         v
Citation and Provenance Validation
         |
         v
Response with Evidence and Limitations
```

**Rules**
* The locally available scientific knowledge base is the offline source of truth.
* Don't fabricate citations when a document is missing.
* Keep retrieved evidence separate from model-generated interpretation.
* Preserve document identifiers, versions, and the relevant page or timestamp references.
* Say clearly when an answer depends on information that may have changed since the last synchronization (show the `knowledge_version` and the sync time).
* Don't claim an offline answer includes the latest NASA or NIST information unless that information is already stored locally.

**Acceptance:** while disconnected, a user can ask a research question about a locally indexed document and get a response with verifiable evidence references.

### Task 6 — Support offline video and computer vision analysis (P1)

Extend the video-analysis pipeline (Workstream A) so its core processing runs locally. Princess owns the CV components; the Lead owns jobs, routing and persistence.

**Required capabilities:**
- local video upload and storage;
- local frame extraction with configurable sampling;
- local flame segmentation and detection;
- tracking across frames, where supported;
- temporal measurements and feature extraction;
- local job queues, with progress tracking and resumable processing;
- persisted results and failure states;
- optional local audio extraction and transcription.

**Processing strategy.** Dedicated CV and temporal-analysis components do the video processing. A local LLM only interprets documented measurements and summarizes results; it never replaces the underlying scientific computation.

Ordinary RGB values are not calibrated temperature measurements. Temperature estimates need suitable calibration and a supporting measurement method.

**Acceptance**
* A video already stored on the machine can be submitted and processed without external connectivity, provided all required models and dependencies are installed.
* Long-running jobs don't need an uninterrupted frontend connection.

### Task 7 — Make the backend and data layer offline-capable (P0)

Local models alone aren't enough if the application can't reach its database, documents or job queue while disconnected.

**Required actions**
* Verify that PostgreSQL is available locally or on the same disconnected network.
* Verify that the vector store and graph store run without cloud access.
* Keep the required model files, scientific documents and application assets available locally.
* Use a local object store (MinIO) or configured filesystem storage.
* Make background-job persistence durable. Job status and results must survive application restarts.
* Make document ingestion and indexing jobs resumable.
* Avoid unnecessary runtime dependencies on cloud-managed services.
* Add local database backup and recovery procedures (shared with the M12 runbook).

**Synchronization when connectivity returns**
1. Detect that external services are available.
2. Re-establish approved connections.
3. Synchronize queued metadata and permitted changes.
4. Resolve conflicts with explicit policies.
5. Record the synchronization outcomes.
6. Resume eligible cloud operations.

Don't automatically upload all local videos, documents, prompts or research data. Synchronization must follow the configured privacy and data-transfer policies.

**Acceptance:** core locally stored research, model and analysis data stays accessible after the internet disconnects and the application restarts.

### Task 8 — Add an offline-aware frontend experience (P1)

Coordinate with Belal (E4) to show the operating mode and which capabilities are available.

**Required UI indicators:**
- current mode (Cloud-Preferred Hybrid, Local-First or Offline-Only);
- internet connectivity status;
- cloud provider availability and local model availability;
- the active model and execution provider;
- local processing progress, and queued and failed jobs;
- synchronization status;
- clear limitations that affect the current result.

**UX requirements**
* Don't block the whole interface because a cloud provider is unavailable.
* Let locally supported workflows continue.
* Distinguish unavailable external search from failed local retrieval.
* Show whether a response was generated locally or remotely.
* Give a useful message when a task exceeds local resource limits.
* Never imply that the application has live external data while it is offline.
* Self-host the web fonts, so the UI doesn't depend on Google Fonts at runtime.

**Acceptance:** users can see the current execution mode and understand which operations remain available without internet access.

### Task 9 — Security, isolation and scientific reliability (P0)

Offline operation must preserve the platform's security and scientific integrity.

**Requirements**
* Keep credentials and provider keys out of source code.
* Don't require cloud credentials for local inference.
* Restrict access to the local model server to authorized application components; never expose it unauthenticated.
* Apply authentication and authorization to local administrative endpoints.
* Validate uploaded files and limit resource consumption.
* Prevent uploaded content from being executed as code.
* Treat retrieved documents as untrusted input, and apply prompt-injection defenses to document ingestion and RAG.
* Log model versions, routing decisions and evidence identifiers.
* Preserve reproducibility metadata for scientific analysis.
* Validate structured model output before application logic uses it.
* Don't let an LLM silently override measured CV results or validated scientific calculations.

**Acceptance:** the system runs locally without an unauthenticated model server and without weakening the existing authorization and provenance controls.

## 7A.7 Lead Engineer schedule for Sub-phase 2H

This is the Lead Engineer's track within the eight-week schedule in §8. It doesn't replace the other engineers' schedules.

| Week   | Lead Engineer tasks                                                                                                   | Deliverables                                                 |
| ------ | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Week 1 | Audit dependencies; define provider contracts, operating modes, routing policies and the local resource budget. **Also the M1 slice:** first local LLM adapter (Ollama) with AURA behind the router | Dependency audit, ADRs, provider contracts, `/api/chat` without AURA |
| Week 2 | Implement the provider registry, health checks, normalized errors and the first cloud/local routing                   | Provider abstraction and routing prototype                   |
| Week 3 | Deploy the local runtime and the first selected LLM; set up the model manifest and a reproducible setup               | Local inference service and model registry                   |
| Week 4 | Integrate local embeddings, retrieval, reranking and scientific RAG                                                   | Offline research-query workflow                              |
| Week 5 | Integrate local model routing with Graph RAG and persistent scientific knowledge                                      | Offline graph-and-vector retrieval                           |
| Week 6 | Integrate local CV and video jobs, durable queues and local result persistence                                        | Offline analysis workflow                                    |
| Week 7 | Add recovery, synchronization policies, observability, resource management and UI integration                         | Resilience and monitoring implementation                     |
| Week 8 | Run the offline acceptance tests, failure injection, performance benchmarks and security checks; prepare the release  | Test report and deployment documentation                     |

**Scheduling rule:** if the shared contracts aren't stable yet, finish the relevant contracts before parallel integration. The hybrid system reuses the existing data, evidence and evaluation models; it doesn't introduce duplicate registries.

## 7A.8 Required test scenarios

Verify every scenario before declaring the sub-phase complete. Each one must have automated tests and at least one run with the network physically disconnected.

| Scenario                                    | Expected Behavior                                                                         |
| ------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Internet is disconnected before startup     | Local services start and supported offline workflows remain available                     |
| Internet disappears during a cloud request  | The request fails over when it is safe and a compatible local model exists                |
| Cloud LLM is unavailable                    | Local LLM handles supported language tasks                                                |
| Cloud embedding service is unavailable      | Local embedding model supports local indexing and retrieval                               |
| External research search is unavailable     | The system uses local sources and discloses the limitation                                |
| A video is already stored locally           | Local video processing can complete without external connectivity                         |
| Local LLM exceeds available memory          | The system reports a controlled resource error instead of crashing the whole application  |
| A local model is missing or corrupt         | Health checks report the unavailable capability and give an actionable error              |
| The application restarts during a video job | The job resumes or enters a clearly defined recoverable state                             |
| Connectivity returns                        | Eligible cloud operations and approved synchronization resume                             |
| Offline-Only mode is active                 | No external AI-provider requests are made                                                 |
| A local answer has incomplete evidence      | The response states the uncertainty or missing evidence instead of inventing citations    |
| Local and cloud models disagree             | The system preserves the source evidence and records the model/version metadata           |

## 7A.9 Definition of Done

Sub-phase 2H is complete only when all of the following are true:

1. The application has explicit operating modes and a documented routing policy.
2. Critical cloud-dependent AI operations have compatible local alternatives or clearly documented limitations.
3. Local LLM, embedding, retrieval and CV/video capabilities work after the initial model and dependency installation.
4. The scientific knowledge base and analysis results remain available without internet access.
5. Provider failures don't cause uncontrolled retry loops or cascade into application-wide failures.
6. The frontend clearly shows the operating mode, the active provider and the relevant limitations.
7. Local and cloud model versions and execution provenance are recorded.
8. Offline behavior passes automated tests and a real network-disconnection test.
9. The deployment guide documents model installation, storage requirements, resource budgets and recovery.
10. The system never fabricates scientific evidence or claims to have run external searches that were unavailable.

## 7A.10 Handoff package

All files live in `docs/hybrid-ai/`. Their detailed contents are specified in `docs/reports/DOC_REQUIREMENTS_Lead.md` §8.

| ID | Document | Covers | Due |
|---|---|---|---|
| H-1 | `PHASE_2_HYBRID_AI_DEPENDENCY_AUDIT.md` | Task 1 | Week 1 |
| H-2 | `PHASE_2_HYBRID_AI_ARCHITECTURE.md`: target architecture, operating modes, routing strategy, dependency boundaries | Tasks 2–3 | Week 1 (draft), Week 2 |
| H-3 | `PHASE_2_LOCAL_MODEL_REGISTRY.md`: candidate models, capabilities, licenses, versions, checksums, resource requirements, benchmark results | Task 4 | Week 3 |
| H-4 | `PHASE_2_HYBRID_AI_API_CONTRACTS.md`: provider interfaces, health endpoints, execution metadata, normalized errors | Task 2 | Week 2 |
| H-5 | `PHASE_2_OFFLINE_ACCEPTANCE_TESTS.md`: scenarios, expected results, automation strategy, execution evidence | §7A.8 | Week 2 (plan), Week 8 (evidence) |
| H-6 | `PHASE_2_OFFLINE_DEPLOYMENT_GUIDE.md`: runtime setup, model installation, storage, environment configuration, backups, recovery | Tasks 4, 7 | Week 3 (draft), Week 8 |
| H-7 | `PHASE_2_HYBRID_AI_BENCHMARK_REPORT.md`: local-versus-cloud quality, latency, resource consumption, task-specific acceptance results (generated with Ziad's harness) | Task 4, C2 | Week 4 (first), Week 8 |

## 7A.11 Execution priorities

**P0 — must have:**
- dependency audit;
- provider abstraction;
- connectivity-aware routing;
- local LLM runtime;
- local embedding and retrieval;
- local access to the scientific knowledge base;
- local persistence and durable jobs;
- offline security and acceptance tests.

**P1 — required for a complete scientific workflow:**
- offline video analysis;
- local reranking;
- Graph RAG integration;
- offline-aware frontend status;
- recovery and synchronization.

**P2 — future improvements:**
- adaptive model selection based on measured quality and available resources;
- automatic selection among multiple local models;
- advanced local model optimization and batching;
- optional local transcription and multimodal interpretation;
- controlled model updates with evaluation-based promotion.

Don't make the first release depend on deploying many models or on a complex distributed serving system.

**Engineering principle: cloud connectivity enhances the platform; it is not a prerequisite for its core operation.**
- The local execution path supports the essential workflows: research, retrieval, scientific document access and video analysis.
- When cloud services are available, they may add model quality, scale, or access to fresh external information.
- The system degrades gracefully: when a capability is unavailable, it explains the limitation, preserves existing data, and keeps providing everything that still works.

---

# 8. Updated Eight-Week Execution Schedule

| Week | Engineering priority                                               | Expected output                                                | Sub-phase 2H, Lead track (§7A.7) |
| ---- | ------------------------------------------------------------------ | -------------------------------------------------------------- | -------------------------------- |
| 1    | **MVP carry-over P0 items (M1, M2, M3, M6, M10, M11, M12)**, audit, API contracts, evaluation baseline | Model router with Ollama/vLLM, single retrieval stack, list endpoints, CI, ADRs, runbook, `v0.1.0-mvp` tag; benchmark size agreed | Dependency audit (H-1); provider contracts; operating modes; local resource budget; M1 slice |
| 2    | Close remaining P0 items; **verified MVP baseline**; data management foundations, video ingestion, evaluation framework | Baseline scorecard on the expanded benchmark; registry updates, video input support, benchmark definitions | Provider registry, health checks, normalized errors, cloud/local routing prototype |
| 3    | **MVP carry-over P1 items (M4, M5, M7, M8, M9, M13)**; professional NLP, document quality controls, admin inventory | CAG and session MAG live; §9 tables migrated; scientific extraction pipeline and initial Admin Dashboard | Local runtime, first selected LLM, model manifest, reproducible setup |
| 4    | Hybrid RAG, video segmentation, model evaluation                   | Improved retrieval and initial temporal CV results             | Offline research-query workflow (local embeddings, retrieval, reranking, RAG) |
| 5    | Knowledge Graph, relationship extraction, ranking engine           | Graph records, provenance-aware relationships, first rankings  | Offline graph-and-vector retrieval |
| 6    | Graph RAG, Graph Memory, multimodal analysis integration           | Multi-hop retrieval and integrated visual/scientific workflows | Offline CV/video jobs, durable queues, local result persistence |
| 7    | Admin controls, performance tuning, complete dashboard             | Operational management and integrated research experience      | Recovery, synchronization, observability, resource management, UI indicators |
| 8    | Benchmark evaluation, security, release candidate                  | Validated Phase 2 release candidate and evaluation report      | Offline acceptance tests, failure injection, benchmarks (H-7), security checks |

## Critical path

Respect these dependencies:

0. MVP carry-over P0 items close before the Phase 2 baseline is measured (Section 2.2 rule).
1. Stable document and experiment identifiers precede graph integration.
2. Validated data precedes trustworthy knowledge ranking.
3. Evaluation datasets precede meaningful model rankings.
4. Graph provenance precedes trustworthy Graph RAG responses.
5. Video metadata and frame identifiers precede reproducible temporal analysis.
6. Stable API contracts precede final frontend integration.
7. A provider-neutral model router (M1) precedes LLM comparison (C2) and routing configuration (B5).
8. Provider contracts and the dependency audit (Sub-phase 2H, Tasks 1–2) precede local runtime integration. A locally indexed corpus with pre-downloaded embedding weights precedes offline RAG (Task 5).

Work can proceed in parallel wherever interfaces and fixtures are available.

---

# 9. Updated Six-Engineer Ownership

| Owner                | Main responsibility                                            | MVP carry-over (Section 2.2) | Additional Phase 2 work                                                                          |
| -------------------- | -------------------------------------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------ |
| Lead Engineer — Anas | Backend, AI infrastructure, orchestration, integration, DevOps | M1, M6, M12; support on M2, M4, M8, M13 | **Sub-phase 2H owner (Hybrid AI Execution, §7A)**; evaluation integration, ranking interfaces, graph-service integration, model routing |
| Engineer 1 — Eman    | NLP, RAG, Context Engineering                                  | M2, M3, M4, M5, M13          | Graph RAG, Graph Memory, entity resolution, evidence-aware synthesis; 2H Task 5 (local RAG behaviour on the local LLM) |
| Engineer 2 — Anas    | Scientific data and knowledge base                             | M8, M9; M4 publication event | Admin data operations, graph entity registry, source-quality scoring, provenance; 2H Task 7 (local data, backups, sync data rules) |
| Engineer 3 — Princess | Computer Vision and PyTorch                                   | M10; M4 analysis cache reuse | Video analysis, temporal tracking, CV benchmarking, analysis artifacts; 2H Task 6 (offline CV/video) |
| Engineer 4 — Belal   | Frontend and visualization                                     | M7                           | Admin Data Management Dashboard, model-ranking views, graph exploration, video workspace; 2H Task 8 (offline-aware UI) |
| Engineer 5 — Ziad    | Evaluation and research intelligence                           | M11; M10 evaluation design   | LLM evaluation, analytics-model evaluation, dataset ranking validation, RAG/Graph RAG benchmarks; 2H local-vs-cloud benchmark (H-7) and offline acceptance test automation (H-5) |

**Lead capacity note:** Sub-phase 2H adds to the Lead's Week 1–3 load, which already includes M1, M6 and M12. To stay within capacity, the Lead owns the contracts, router, runtime and integration, and delegates the 2H tasks listed above to their owners. This follows the rule below.

## Lead Engineer priorities

Your first priority is to make the contracts stable enough that the team can work independently.

You should own:

* API and result schemas.
* Model registry integration.
* Evaluation execution interfaces.
* Analysis orchestration.
* Graph and vector index synchronization contracts.
* Background job infrastructure.
* Deployment and observability.
* Final integration and release gates.

Don't take ownership of all the model evaluations, graph extraction and frontend functionality yourself.

---

# 10. Updated Admin Dashboard Sections

The Admin Dashboard should contain these major modules:

1. **Overview**

   * System health.
   * Ingestion status.
   * Model status.
   * Index synchronization.
   * Evaluation activity.
   * Execution mode, internet connectivity, and cloud/local provider availability (§7A).

2. **Sources**

   * Source registry.
   * Source validation.
   * Acquisition history.
   * Data access and licensing metadata.

3. **Documents and Datasets**

   * Metadata.
   * Extraction status.
   * Quality checks.
   * Duplicate detection.
   * Reprocessing.

4. **Experiments**

   * Experiment registry.
   * Conditions.
   * Associated documents and datasets.
   * Metadata completeness.

5. **Knowledge Graph**

   * Entities.
   * Relationships.
   * Provenance.
   * Conflicts.
   * Graph validation.

6. **Models and LLMs**

   * Model registry.
   * Model versions.
   * Evaluation results.
   * Task-specific rankings.
   * Deployment and routing configuration.
   * Execution mode (Cloud-Preferred Hybrid / Local-First / Offline-Only), local model health, circuit-breaker state (§7A.5).

7. **Knowledge Quality**

   * Evidence quality.
   * Extraction confidence.
   * Contradictions.
   * Missing provenance.
   * Review queues.

8. **Evaluation Center**

   * Benchmark management.
   * Evaluation runs.
   * Metric comparisons.
   * Regression detection.
   * Release acceptance.

9. **System Operations**

   * Background jobs.
   * Failed tasks.
   * Logs.
   * Index rebuilds.
   * Cache status and invalidation (CAG, from M4).
   * Synchronization status after reconnection (§7A, Task 7).
   * Storage and GPU usage.

10. **Audit and Access**

    * Administrator roles.
    * Change history.
    * Model promotion history.
    * Data modification history.

---

# 11. Updated Phase 2 Acceptance Criteria

Phase 2 must pass the following acceptance gates.

## MVP carry-over (gate before the Phase 2 baseline)

* Every Section 2.2 item is closed, or explicitly re-scoped with an owner and a written reason.
* `/api/chat` and image interpretation work with AURA disabled, through the provider-neutral model router (Ollama locally, vLLM on the L40S).
* One retrieval stack serves the API, with rank fusion, a versioned reranker and a stored query rewrite.
* CAG and session MAG work, with version-aware invalidation, expiry and `memory_used` / `cache_hit` disclosure.
* `GET /api/documents` and `GET /api/experiments` exist and are covered by contract tests. No frontend screen uses mock data.
* The §9 data-model tables exist, including KnowledgeEntity, KnowledgeRelation, Memory, CacheEntry, Model, Dataset and ImageAsset.
* A single test command passes from the repo root, and CI runs Python and web checks on every PR.
* The CV segmentation report has a real IoU/Dice result on reviewed masks, not `NOT_EVALUATED`.
* `v0.1.0-mvp` is tagged and reproducible from the runbook. ADR-001 to ADR-004 are written.

## Hybrid AI execution (Sub-phase 2H)

* Every item of the §7A.9 Definition of Done is met.
* All §7A.8 scenarios pass in automated tests, and in at least one run with the network physically disconnected.
* Offline-Only mode makes no external AI-provider requests, as verified by network capture or egress blocking.
* The local model server is not reachable without authentication.
* The H-1 to H-7 handoff documents exist and match the deployed configuration.

## Video analysis

* Supported videos can be submitted and processed asynchronously.
* Frame timestamps and asset identifiers are preserved.
* Visual measurements are generated with documented definitions.
* Analysis outputs include pipeline versions and provenance.
* CV performance is measured on a reviewed test set.

## Admin data management

* Authorized administrators can inspect sources, documents, datasets, experiments and processing jobs.
* Ingestion failures can be inspected and retried safely.
* Metadata corrections are audited.
* Destructive operations require authorization.
* Graph and vector index rebuilds are observable and recoverable.

## Model and knowledge evaluation

* LLMs are compared on the same controlled benchmark.
* Analytical models are evaluated against task-specific metrics.
* Data quality and knowledge quality are ranked separately.
* Ranking results include their methodology and version.
* Models can't be promoted solely because they have the highest aggregate score.
* Critical scientific failures block release.

## NLP, RAG, and Graph Memory

* Scientific entity and relationship extraction is traceable to source evidence.
* Hybrid RAG is benchmarked against the MVP baseline.
* Graph RAG supports validated multi-hop retrieval.
* Graph Memory distinguishes persistent scientific knowledge from session context.
* Graph relationships keep their provenance.
* Contradictory evidence is surfaced, not silently discarded.
* Retrieval and answer quality are measured on a reviewed benchmark.

## Integrated release

* Core research workflows pass end-to-end tests.
* Critical API contract tests pass.
* Analysis results can be audited.
* Deployment and recovery procedures are documented.
* Performance is benchmarked under representative workloads, with OpenTelemetry traces across API, retrieval, provider and CV.
* Known limitations are documented and visible to users.

---

# 12. Features to Defer

Keep the following off the Phase 2 critical path unless the team demonstrates a specific need:

* Autonomous model training without review.
* Automatic model promotion based only on ranking.
* Unvalidated combustion risk scoring.
* Unsupported physical predictions.
* Complex distributed infrastructure before scaling requirements are measured.
* Unrestricted self-modifying knowledge graphs.
* Automatic causal conclusions from correlations.
* AURA AI integration as a core dependency. *The current MVP chat and interpretation paths depend on AURA; M1 removes that dependency, and AURA stays an optional provider behind the stable Flame API.*
* Many overlapping local models, or a complex distributed serving system, for the first hybrid release. Sub-phase 2H starts with one reliable local model per critical capability (§7A.11, P2 items).

The system may support controlled retraining experiments and future AURA integration, but these must not compromise scientific reproducibility.

---

# 13. Final Phase 2 Outcome

At the end of Phase 2, Flame in Freefall should have five integrated capabilities. All of them run on the hybrid execution base from Sub-phase 2H, so their core workflows keep working when connectivity or cloud services are lost:

1. **Scientific Data Intelligence:** A managed, traceable, quality-assessed scientific corpus.
2. **Advanced Visual Intelligence:** Image and video analysis with temporal measurements and explicit limitations.
3. **Professional Retrieval Intelligence:** Hybrid NLP/RAG, Graph RAG, and Graph Memory.
4. **Model and Knowledge Evaluation:** Reproducible benchmarks and task-specific ranking.
5. **Scientific Operations:** An Admin Dashboard for managing data, models, knowledge, evaluations, and system health.

The target is not to maximize the number of AI components. It is a reliable scientific platform where every major result can be inspected, evaluated, and traced back to its supporting evidence.
