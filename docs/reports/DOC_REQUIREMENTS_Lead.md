# Documentation Requirements: Lead Engineer (Anas, Backend / AI Infrastructure / Integration / DevOps)

| | |
|---|---|
| **Phase** | Phase 2: Advanced Scientific Intelligence Platform |
| **Issued** | 2026-10-10 |
| **Branch** | `main` (task branches from `main` for larger changes) |
| **Basis** | [Phase 2 Plan](../plan/PHASE2_PLAN.md): §2 carry-over items **M1** (model router), **M6** (API gaps) and **M12** (CI, OpenTelemetry, ADRs, runbook, release); §9 "Lead Engineer priorities"; the §11 integrated-release gate; and **Sub-phase 2H, the Hybrid AI Execution System (Phase 2 Plan §7A; this file's §8)**; MVP Plan §5.2–§5.3, §11, §12, §19, §22 |
| **Reviewers** | Each Lead document needs a sign-off from the engineer most affected by it (listed per document in §3), because there is no reviewer above the Lead. |

The Lead has two documentation jobs:
1. **Write the platform documents** (§3–§4).
2. **Run documentation governance for the whole team** (§5): the docs index, the PR template, the review matrix, weekly status and release sign-off.

Each engineer has their own requirements file on their branch:
- `docs/reports/DOC_REQUIREMENTS_Eman.md` on `Eman`
- `docs/reports/DOC_REQUIREMENTS_Princess.md` on `Princess`
- `docs/reports/DOC_REQUIREMENTS_Belal.md` on `Belal`
- `docs/reports/DOC_REQUIREMENTS_Ziad.md` on `Ziad`
- `docs/reports/DOC_REQUIREMENTS_Anas.md` on `main` (Engineer 2)

---

## 1. Why this matters

The Lead's first Phase 2 priority is contracts stable enough for the team to work independently, and only written contracts are stable. The audit on 2026-10-10 found these platform gaps:
- **no ADRs**, **no runbook** and **no release tag**;
- `docs/architecture/` holds only `overview.md`;
- the only CI is the AURA contract dry run;
- `python -m pytest` from the repo root fails at collection;
- no model router exists, so chat requires AURA;
- `/api/chat` is outside OpenAPI;
- `GET /api/documents` and `GET /api/experiments` are missing;
- there is no OpenTelemetry tracing.

Sub-phase 2H adds the requirement that the platform keeps working without internet, and the audit shows it currently doesn't:
- chat and interpretation need AURA, hosted on Railway;
- the embedding weights are downloaded from Hugging Face on first use;
- the UI loads Google Fonts at runtime.

§8 sets out the full sub-phase plan and the seven handoff documents (H-1 to H-7) the Lead owns for it.

## 2. Rules for every Lead document

1. **Location and format:** Markdown at the path given in §3, in English. The OpenAPI file stays machine-generated JSON.
2. **Header block:** the same header as the engineers use (Owner, Status, Version, Last updated, Plan items, Code paths).
3. **Evidence over claims:** every operational step in a runbook has been executed at least once, and the doc records the date and the commit it was tested on. Every "CI checks X" statement links the workflow file.
4. **Contracts are versioned:** API changes follow semver, with an entry in `docs/api/CHANGELOG.md` and a deprecation window for breaking changes ("Existing MVP APIs should remain compatible wherever practical").
5. **ADRs are immutable:** a changed decision gets a new ADR that supersedes the old one; the old one isn't edited.
6. **Secrets:** no tokens, passwords or connection strings. Environment variables are documented by name and purpose only.
7. **Limitations:** every document ends with **Known limitations** (or, for an ADR, **Consequences**).

## 3. Required documents

| ID | Document | Path | Covers | Due (Phase 2 week) | Sign-off |
|---|---|---|---|---|---|
| L-1 | Architecture Decision Records | `docs/architecture/adr/ADR-NNN-<slug>.md` | M12, D3 | ADR-001 to ADR-004: Week 1; more as decisions are made | Affected engineer |
| L-2 | Architecture overview (update) | `docs/architecture/overview.md` | §3 architecture | Week 2, Week 8 | Eman, Princess |
| L-3 | Model routing and providers: **delivered as H-2 + H-4** (§8.10), with no separate `model-routing.md` | `docs/hybrid-ai/PHASE_2_HYBRID_AI_ARCHITECTURE.md`, `PHASE_2_HYBRID_AI_API_CONTRACTS.md` | M1, B5, C2, 2H | Week 1–2 | Eman, Ziad |
| L-4 | API contract and changelog | `docs/api/openapi.json` (generated), `docs/api/API_SCHEMAS.md`, `docs/api/CHANGELOG.md` | M6, A4, B, C | Continuous; every API PR | Belal |
| L-5 | Index synchronization contract | `docs/architecture/index-sync-contract.md` | D3, D6 | Week 4 | Anas (E2), Eman |
| L-6 | Background jobs | `docs/architecture/background-jobs.md` | A4, B2 | Week 3 | Princess, Anas (E2) |
| L-7 | CI/CD and testing guide | `docs/operations/CI_CD.md` | M12 | Week 1 | Ziad |
| L-8 | Runbook (offline deployment is in H-6 and linked from here) | `docs/operations/RUNBOOK.md` | M12, §11, 2H | Week 2, Week 8 | Any engineer who has dry-run it |
| L-9 | Observability guide | `docs/operations/OBSERVABILITY.md` | M12, §11 | Week 3 | Ziad |
| L-10 | Security and access control | `docs/operations/SECURITY.md` | B6, MVP §19 | Week 7 | Belal, Anas (E2) |
| L-11 | Release notes | `docs/releases/<version>.md` | M12, Week 8 | `v0.1.0-mvp` in Week 1; release candidate in Week 8 | Ziad (gate verdict) |
| L-12 | AURA boundary (update) | `docs/integration/AURA_INTEGRATION_STATUS.md` | M1, §12 | Week 2 | — |

## 4. Required contents

### L-1 Architecture Decision Records
Template: **Title, Status (proposed/accepted/superseded), Date, Context, Decision, Alternatives considered, Consequences, Links**. Required ADRs:
- **ADR-001** Monorepo layout (MVP §14 and the 2026-10-06 restructure).
- **ADR-002** PostgreSQL + pgvector before a dedicated vector DB.
- **ADR-003** Provider-neutral model router (Ollama local, vLLM on L40S, AURA optional).
- **ADR-004** AURA boundary: optional provider, never a core dependency, and why `/api/chat` is kept out of AURA's derived tools.
- **ADR-005** `/api/analyses` naming vs the MVP's `/api/analysis/image`.
- **ADR-006** Single retrieval stack (with Eman, M2).
- **ADR-007** Graph storage strategy (with Anas E2, D3).
- **ADR-008** Job system for image and video analysis (RQ or a replacement).
- **ADR-009** Authentication and RBAC model (B6).

### L-2 Architecture overview
- The Phase 2 logical architecture mapped to **actual** modules, services and deployments: what is a separate service and what is a module.
- Request lifecycle diagrams for chat, search, image/video analysis and admin operations.
- Where every version identifier is set (corpus, model, prompt, pipeline, benchmark).

### L-3 Model routing and providers (delivered through H-2 and H-4, §8.10)
- The `LLMProvider` / `EmbeddingProvider` / CV provider interfaces and their DTOs.
- The capability → provider/model map, approved versions, and how routing configuration is changed and audited (B5).
- Timeout, retry (idempotent only), fallback and concurrency rules. A failed retrieval returns evidence-insufficient, never an uncited answer.
- L40S allocation: vLLM vs CV memory budgets and the profiles measured (with Princess's performance doc).

### L-4 API contract and changelog
- `openapi.json` generated from the code, plus a CI check that it is current.
- `API_SCHEMAS.md` regenerated with `docs/tools/render_api_schemas.py`.
- The error-envelope reference, auth requirements per route, and pagination rules.
- Phase 2 endpoints (video, admin, evaluation, graph), each with a request/response example and its contract-test file.
- `CHANGELOG.md` with semver entries and deprecations.

### L-5 Index synchronization contract
- The stable-ID rules across PostgreSQL, pgvector and the graph store.
- How a knowledge-version publication (Anas's E2-5) triggers re-embedding, graph updates and cache invalidation, and how partial failures are detected and recovered.
- An observable rebuild procedure (status, progress, rollback), as required by §11.

### L-6 Background jobs
Queues, job types, payload schemas, status lifecycle, retries, cancellation, timeouts, idempotency keys, failure reporting, and how jobs appear in the Admin "System Operations" module.

### L-7 CI/CD and testing guide
- Every workflow and what it runs: Python lint and tests for `tests/` and `apps/api`; web lint, typecheck and build; the OpenAPI freshness check; contract tests; the AURA dry run; secret scanning.
- The **single repo-root test command** (after fixing the `flame_api` import collection).
- Required checks for merging, and how deployments (Railway, then L40S) are triggered.

### L-8 Runbook
- Local setup from a clean machine: Compose, `.env` from `infrastructure/.env.example`, seed, ingest, vector index build.
- Deployment, migrations, rollback, secret rotation, **backup and restore drill** (performed and dated), the L40S model load and health check, and common incidents with fixes.
- How to reproduce the demo from a tagged release (MVP §22).

### L-9 Observability guide
OpenTelemetry span names and attributes along the API → orchestration → cache → retrieval → rerank → provider/CV → persistence path; the structured-log field list; metrics (latency p50/p95, queue depth, cache hit rate, GPU memory, tokens/s); dashboards; alert thresholds; and a description of how to follow one `request_id` end to end.

### L-10 Security and access control
Roles and permissions (read/write/admin), session handling, protected ingestion and destructive operations, the audit-log schema, upload validation limits, document-parsing isolation, prompt-injection defenses (with Eman), a threat model summary, and the result of the Week 8 security review.

### L-11 Release notes
For each release: the version and tag, commit, included changes (by plan item), migrations, evaluation summary (linking Ziad's scorecard), known limitations, upgrade steps and rollback target.

### L-12 AURA boundary
Update the status document so it describes AURA as an optional provider behind M1, and mark the MVP-era statements that are superseded.

## 5. Team documentation governance (Lead-owned)

| ID | Item | Path | Due |
|---|---|---|---|
| G-1 | **Documentation index**: one table listing every team document with its owner, status and last update | `docs/README.md` | Week 1, kept current |
| G-2 | **PR template** with a documentation checklist (docs updated? numbers generated? header and changelog updated? limitations?) | `.github/pull_request_template.md` | Week 1 |
| G-3 | **Review matrix**: who reviews which document type, taken from each engineer's requirements file | `docs/README.md` (section) | Week 1 |
| G-4 | **Weekly integration status**: per engineer, the plan items closed (with evidence links), the docs delivered vs due, blockers, and risks | `docs/reviews/PHASE2_WEEK_<n>.md` | End of every week |
| G-5 | **Documentation audit** at Weeks 4 and 8: check every doc against the code at a commit and list stale ones with owners | `docs/reviews/DOC_AUDIT_WEEK_<n>.md` | Weeks 4 and 8 |
| G-6 | **Release sign-off matrix**: each owner signs off their area for the release candidate | `docs/releases/<version>.md` (section) | Week 8 |

**Enforcement:** a PR that changes behavior without updating its documentation is not merged. Overdue documents go into the weekly status (G-4) with a new due date and an owner.

## 6. Existing documents to fix

| File | Problem found in the 2026-10-10 audit | Action |
|---|---|---|
| `docs/architecture/overview.md` | Pre-Phase 2; no ADRs referenced | Update as L-2 and link the ADRs |
| `docs/api/openapi.json`, `API_SCHEMAS.md` | `/api/chat` excluded; list endpoints missing | Update with M6 (L-4) |
| `docs/integration/AURA_INTEGRATION_*.md` | Describe AURA as required for chat | Update as L-12 |
| `README.md`, `tests/README.md` | The root test command fails at collection | Fix the command and document it (L-7) |
| `infrastructure/README.md`, `apps/api/README.md` | No backup/restore, rollback or incident steps | Move operational steps into L-8 and link it |
| `docs/plan/DAY2_TASKS.md` | MVP-era task list | Add a status line pointing to the Phase 2 plan |
| `.railway/railway.py`, `.railway/requirements.txt` (committed in `780d89b`) | Not documented | Explain what it deploys and how, in the runbook (L-8) |

## 7. Acceptance checklist (affected engineer signs off)

- [ ] ADR-001 to ADR-004 are accepted in Week 1, and every later architectural decision has an ADR.
- [ ] The OpenAPI file is generated and checked in CI, and every endpoint has a contract test and a changelog entry.
- [ ] The runbook has been executed from a clean machine by someone other than the Lead, and the backup/restore drill is dated.
- [ ] One repo-root test command passes, and CI enforces the required checks.
- [ ] `v0.1.0-mvp` is tagged, with release notes.
- [ ] The docs index, PR template and weekly status (G-1 to G-4) are running from Week 1.
- [ ] Sub-phase 2H: H-1 to H-7 exist in `docs/hybrid-ai/`; every §8.8 scenario has execution evidence (automated plus one real disconnection run); every §8.9 Definition of Done item is met.
- [ ] Known limitations or consequences are stated in every document.

---

## 8. Sub-phase 2H — Hybrid AI Execution System (Lead Engineer)

> Keep this section in sync with **Phase 2 Plan §7A**. Change both in the same commit; if they differ, §7A is authoritative.
> **Owner:** Lead Engineer, Anas Ibrahim: AI infrastructure, backend orchestration, model routing, storage integration, reliability and deployment.
> **Delegated parts:**
> - Eman: Task 5, local RAG behaviour.
> - Princess: Task 6, offline CV and video.
> - Belal: Task 8, offline-aware UI.
> - Anas (E2): Task 7, data and backup rules.
> - Ziad: H-5 automation and the H-7 benchmark.

### 8.1 Objective

Implement a **Hybrid AI Execution System** that lets Flame in Freefall keep operating when internet connectivity, cloud-hosted models or external AI services become unavailable. The system combines:

* Cloud-hosted LLMs and AI services, when available.
* Locally hosted LLMs for scientific NLP, research assistance and selected reasoning tasks.
* Local computer vision models for flame and video analysis.
* Local embedding and reranking models for semantic retrieval.
* Local scientific knowledge and Graph RAG for evidence-based responses.
* Local data storage, task queues and cached results to support disconnected operation.

**Primary requirement:** losing internet connectivity must not stop the whole system. Instead, the system automatically switches to the best available local capabilities and clearly communicates any limitations.

### 8.2 How this fits the existing plan

* **One router.** The M1 `ModelRouter` is the Task 3 router. Its Week 1–2 slice has three parts: the provider contracts, one local LLM (Ollama), and AURA as an optional cloud provider. That slice unblocks the Phase 2 baseline.
* **Local vs external is about network location, not hardware.** Ollama, llama.cpp, vLLM on the L40S, fastembed and `cv/flame_cv.py` are local when they are reachable on the same disconnected network. AURA, hosted LLM APIs and the Hugging Face Space CV provider are external.
* **No duplicate registries.** The model manifest uses the `Model` table (M8) and the C1 model cards. The knowledge base is the existing PostgreSQL + pgvector + MinIO corpus. Benchmarks use Ziad's harness.
* **Deployment.** Railway stays for connected demos; offline deployment runs `infrastructure/compose.yaml` on local hardware.

**Known external dependencies to start the H-1 audit from (2026-10-10):**

| Component | External dependency today | Offline behaviour today | Required local path |
|---|---|---|---|
| `/api/chat` generation | AURA (Railway) | `503 CHAT_UNAVAILABLE` | Local LLM through the router |
| Image interpretation | AURA | `unavailable` | Local LLM on measured results |
| Embeddings | fastembed `BAAI/bge-small-en-v1.5`, weights downloaded from Hugging Face on first use | Fails with an empty cache | Pre-download, checksum, offline cache flag |
| CV inference | Optional HF Space provider | The local provider works | Force the local provider in Offline-Only mode |
| Frontend fonts | Google Fonts in `apps/web/app/layout.tsx` | System-font fallback | Self-host the fonts |
| Deployment | Railway | Unreachable | Local Compose |
| Container images | Docker Hub | A fresh machine can't start | Pre-pull or export the images |
| Data acquisition | `psi.nasa.gov`, NTRS | No new data | Local mirrors only, with the sync age disclosed |

### 8.3 Target architecture

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

The local intelligence layer must not depend on a cloud provider for its core functions. The orchestrator chooses between cloud and local execution based on connectivity, task requirements, model availability, resource capacity and configured policies.

### 8.4 Execution modes

| Mode                   | Behavior                                                                       | Purpose                                             |
| ---------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------- |
| Cloud-Preferred Hybrid | Use cloud models when available and appropriate; keep a local fallback         | Normal connected operation                          |
| Local-First            | Prefer locally hosted models, with permitted cloud fallback                    | Fewer external dependencies and better continuity   |
| Offline-Only           | Block external AI and data requests; use only local resources                  | Disconnected operation                              |

The active mode is configurable through an environment variable (proposed: `FLAME_AI_EXECUTION_MODE=cloud_preferred|local_first|offline_only`) and through the Admin Dashboard "Models and LLMs" module. Every mode change is audited. Offline-Only mode must never silently send data to external providers.

### 8.5 Lead Engineer tasks

**Task 1 — Audit existing AI dependencies (P0).**

*Actions:*
- inspect all FastAPI routes, orchestration services, AI providers, background workers and storage integrations;
- identify cloud LLM dependencies in NLP, research search, RAG, summarization and analysis;
- identify external embedding, reranking, transcription and CV dependencies;
- check whether authentication, frontend assets, metadata access and database operations can work locally;
- separate the data sources that are unavailable offline from those already cached or acquired;
- document the local resource requirements of every proposed model.

*Deliverable:* H-1. *Acceptance:* every critical AI dependency has a documented fallback, a defined degraded mode, or the documented reason it can't operate offline.

**Task 2 — Unified AI provider interface (P0).**

*Interfaces:*
- chat and text generation;
- structured JSON output;
- embeddings;
- reranking;
- image inference;
- video-analysis inference;
- speech transcription, if it is in scope.

*Capabilities:*
- provider registration and discovery;
- capability metadata;
- health checks, timeouts, error normalization, retry policies and cancellation;
- availability checks;
- token and resource limits;
- provider-specific configuration;
- tracing and metrics.

Use typed contracts and keep the existing API contracts.

*Placement:* `ai/providers/{contracts,cloud,local}/` and `ai/routing/{registry,health,router,policies}.py` (MVP §14 already reserves these paths). These existing modules move behind the contracts: `apps/api/flame_api/aura_integration.py`, `hf_cv.py`, and the embedder in `vector_index.py`.

*Acceptance:*
- application services don't depend directly on a specific cloud provider;
- local and cloud implementations satisfy the same applicable interfaces;
- a provider can be replaced through configuration alone;
- provider failures return normalized, traceable errors.

**Task 3 — Connectivity-aware model routing (P0).**

*Routing inputs:*
1. the task;
2. the required capabilities;
3. network and provider health;
4. local model availability;
5. GPU and RAM availability;
6. estimated complexity;
7. latency requirements;
8. context-window requirements;
9. whether internet-only information is needed;
10. whether the operation is permitted in Offline-Only mode.

*Flow:* identify the task → check the mode → check availability → execute on a suitable cloud model (if permitted) or a suitable local model (if ready) → validate the result → attach model and provenance metadata → return. When the cloud fails, the router picks a suitable local model instead of retrying the dead provider.

*Policies:*
- use short, bounded connectivity checks;
- keep provider health state with a circuit breaker;
- make timeouts and retry limits configurable;
- don't auto-retry non-idempotent operations without idempotency controls;
- route by capability;
- keep a task-specific fallback registry;
- prevent routing loops;
- never silently replace a scientific vision task with a text-only LLM;
- never report an external search as successful when it wasn't reachable.

*Acceptance:*
- a failed cloud request can fall back to a compatible local provider;
- the application isn't blocked by a failed provider;
- with no compatible local model, the request returns a clear, actionable degraded-mode response;
- every routing decision appears in logs and metrics.

**Task 4 — Local model runtime (P0).**

Evaluate **Ollama** and **llama.cpp** behind a runtime abstraction, and evaluate a GPU server (vLLM on the L40S) where the hardware justifies it.

*Model categories:*
- a general LLM;
- a scientific-NLP LLM validated on scientific prompts;
- an embedding model (current: `BAAI/bge-small-en-v1.5`);
- a reranker (a compact cross-encoder, if the budget allows);
- CV (`cv/flame_cv.py` or a selected lightweight model);
- video (local frame sampling, tracking and the CV pipeline);
- speech-to-text, if required.

*Selection rule:* don't choose by popularity. Benchmark scientific accuracy, memory, cold start, warm latency, throughput, quantization loss, CPU-only operation, GPU compatibility, license, and interface compatibility. Start with one reliable model per critical capability.

*Deliverables:*
- runtime configuration;
- model registry and capability manifest;
- download and verification procedure;
- version and checksum records;
- startup health checks;
- resource limits;
- warm-up and loading policies.

*Acceptance:* after installation and model preparation, one local LLM, one local embedding model and the local CV pipeline run without internet access.

**Task 5 — Local RAG and offline scientific knowledge access (P0; the graph part is P1, after D4).**

*Capabilities:*
- local document retrieval, embeddings and vector search;
- local graph retrieval, and hybrid vector + graph retrieval;
- local reranking;
- source-aware generation;
- cached research results;
- provenance;
- explicit disclosure of missing or inaccessible sources.

*Flow:* local query processing → hybrid retrieval (vector + graph) → evidence filtering and reranking → local LLM synthesis → citation and provenance validation → a response with evidence and limitations.

*Rules:*
- the local knowledge base is the offline source of truth;
- never fabricate citations;
- keep evidence separate from interpretation;
- preserve IDs, versions and page or timestamp references;
- flag information that may be out of date since the last sync (show the `knowledge_version` and the sync time);
- never claim the latest NASA or NIST information unless it is already stored locally.

*Acceptance:* while disconnected, a research question about a locally indexed document gets an answer with verifiable evidence references.

**Task 6 — Offline video and CV analysis (P1).**

*Capabilities:*
- local upload and storage;
- frame extraction with configurable sampling;
- local segmentation and detection;
- tracking where supported;
- temporal measurements;
- local job queues with progress and resumable processing;
- persisted results and failure states;
- optional local audio extraction and transcription.

Dedicated CV components do the computation; a local LLM only interprets documented measurements. RGB values are never calibrated temperature.

*Acceptance:*
- a locally stored video can be processed without connectivity, once the required models are installed;
- long jobs don't need a continuous frontend connection.

**Task 7 — Offline-capable backend and data layer (P0).**

*Required:*
- PostgreSQL, the vector store and the graph store run locally or on the same disconnected network;
- models, documents and assets are stored locally;
- local object storage (MinIO) or the filesystem is used;
- background jobs are durable, and their status and results survive restarts;
- ingestion and indexing are resumable;
- there are no unnecessary cloud-managed dependencies;
- local backup and recovery are documented (shared with L-8).

*Synchronization on reconnection:*
1. detect that external services are back;
2. re-establish approved connections;
3. sync queued metadata and permitted changes;
4. resolve conflicts with explicit policies;
5. record the outcomes;
6. resume eligible cloud operations.

Never auto-upload local videos, documents, prompts or research data; follow the configured privacy and transfer policies.

*Acceptance:* core local research, model and analysis data stays accessible after a disconnection and an application restart.

**Task 8 — Offline-aware frontend (P1, with Belal).**

*Indicators:*
- the current mode;
- connectivity;
- cloud and local provider availability;
- the active model and provider;
- local progress, and queued and failed jobs;
- sync status;
- limitations that affect the current result.

*UX:*
- never block the whole UI because a cloud provider is down;
- keep local workflows running;
- distinguish unavailable external search from failed local retrieval;
- show local versus remote generation;
- give a useful message when local resources are exceeded;
- never imply live external data while offline;
- self-host the fonts.

*Acceptance:* users can see the mode and understand which operations are still available offline.

**Task 9 — Security, isolation and scientific reliability (P0).**

*Requirements:*
- no credentials in code;
- no cloud credentials needed for local inference;
- the model server is reachable only by authorized application components;
- local admin endpoints are authenticated and authorized;
- uploads are validated and resource-limited, and uploaded content is never executed;
- retrieved documents are treated as untrusted, with prompt-injection defenses in ingestion and RAG;
- model versions, routing decisions and evidence IDs are logged;
- reproducibility metadata is preserved;
- structured output is validated before use;
- an LLM never silently overrides measured CV results or validated calculations.

*Acceptance:* the system runs locally without an unauthenticated model server and without weaker authorization or provenance controls.

### 8.6 Schedule

| Week   | Lead Engineer tasks                                                                                                   | Deliverables                                                 |
| ------ | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Week 1 | Audit dependencies; define provider contracts, operating modes, routing policies and the local resource budget; M1 slice (Ollama adapter, AURA behind the router) | H-1, ADRs (ADR-003, ADR-004), provider contracts, `/api/chat` without AURA |
| Week 2 | Provider registry, health checks, normalized errors, first cloud/local routing                                        | Provider abstraction and routing prototype; H-2, H-4; H-5 plan |
| Week 3 | Local runtime and first selected LLM; model manifest; reproducible setup                                              | Local inference service and model registry; H-3; H-6 draft   |
| Week 4 | Local embeddings, retrieval, reranking and scientific RAG                                                             | Offline research-query workflow; first H-7                   |
| Week 5 | Local model routing with Graph RAG and persistent scientific knowledge                                                | Offline graph-and-vector retrieval                           |
| Week 6 | Local CV/video jobs, durable queues, local result persistence                                                         | Offline analysis workflow                                    |
| Week 7 | Recovery, sync policies, observability, resource management, UI integration                                           | Resilience and monitoring implementation                     |
| Week 8 | Offline acceptance tests, failure injection, performance benchmarks, security checks, release preparation             | H-5 evidence, H-6 final, H-7 final                           |

**Scheduling rule:** stabilize the shared contracts before parallel integration. Reuse the existing data, evidence and evaluation models; don't introduce duplicate registries.

### 8.7 Priorities

**P0 — must have:**
- dependency audit;
- provider abstraction;
- connectivity-aware routing;
- local LLM runtime;
- local embedding and retrieval;
- local knowledge-base access;
- local persistence and durable jobs;
- offline security and acceptance tests.

**P1 — complete scientific workflow:**
- offline video analysis;
- local reranking;
- Graph RAG integration;
- offline-aware frontend;
- recovery and synchronization.

**P2 — future:**
- adaptive model selection;
- automatic selection among multiple local models;
- advanced optimization and batching;
- local transcription and multimodal interpretation;
- controlled model updates with evaluation-based promotion.

Don't make the first release depend on many models or on a complex distributed serving system.

### 8.8 Required test scenarios

Each scenario needs an automated test, plus evidence from at least one run with the network physically disconnected.

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

### 8.9 Definition of Done

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

### 8.10 Handoff package: documentation requirements

All files go in `docs/hybrid-ai/`, use the §2 header block and rules, and end with Known limitations and a Changelog.

| ID | Document | Covers | Due | Sign-off |
|---|---|---|---|---|
| H-1 | `PHASE_2_HYBRID_AI_DEPENDENCY_AUDIT.md` | Task 1 | Week 1 | Anas (E2), Princess |
| H-2 | `PHASE_2_HYBRID_AI_ARCHITECTURE.md` | Tasks 2–3 (replaces L-3) | Week 1 draft, Week 2 | Eman |
| H-3 | `PHASE_2_LOCAL_MODEL_REGISTRY.md` | Task 4 | Week 3 | Ziad, Princess |
| H-4 | `PHASE_2_HYBRID_AI_API_CONTRACTS.md` | Task 2 | Week 2 | Belal, Eman |
| H-5 | `PHASE_2_OFFLINE_ACCEPTANCE_TESTS.md` | §8.8 | Week 2 plan, Week 8 evidence | Ziad |
| H-6 | `PHASE_2_OFFLINE_DEPLOYMENT_GUIDE.md` | Tasks 4, 7 | Week 3 draft, Week 8 | Engineer who dry-runs it offline |
| H-7 | `PHASE_2_HYBRID_AI_BENCHMARK_REPORT.md` | Task 4, C2 | Week 4 first, Week 8 | Ziad |

**Required contents**

- **H-1 Dependency audit:**
  - an inventory table (component, file path, external endpoint or service, data sent, current offline behaviour);
  - the online-only operations;
  - the required local replacement for each;
  - the fallback or degraded mode;
  - limitations while disconnected;
  - GPU/RAM/CPU/disk requirements per proposed model;
  - priorities (P0/P1/P2).

  Start from the §8.2 table and complete it for every route, worker, the auth path, the frontend and CI.
- **H-2 Architecture:**
  - the target diagram mapped to real modules (`ai/providers`, `ai/routing`, `apps/api`);
  - the three modes, with what each one allows and blocks;
  - the local vs external classification of every provider;
  - routing inputs, policies, circuit-breaker parameters and fallback registry;
  - dependency boundaries (what may call what);
  - the Offline-Only egress guarantee and how it is enforced.
- **H-3 Local model registry:**
  - per model: capability, runtime, exact version or tag, quantization, license, source URL, **checksum**, size on disk, RAM/VRAM, cold start and warm latency, CPU-only viability;
  - the download and verification procedure;
  - the link to its C1 model card and `Model` table row;
  - the reason it was selected over the other candidates, with numbers from H-7.
- **H-4 API contracts:**
  - typed request/response contracts per capability;
  - health and availability endpoints;
  - the execution-metadata fields attached to every response (provider, model, version, local/remote, mode, fallback used, routing reason);
  - the normalized error codes, including the degraded-mode response;
  - the changes to the public API recorded in `docs/api/CHANGELOG.md` (L-4).
- **H-5 Offline acceptance tests:**
  - every §8.8 scenario, with setup, steps, expected result and the automated test file;
  - the method for simulating a disconnection (egress block, network namespace, physical unplug);
  - the execution evidence for each run (date, commit, mode, logs or captures, pass/fail).
- **H-6 Offline deployment guide:**
  - hardware prerequisites;
  - pre-pulling and exporting container images;
  - installing and verifying models (with checksums) and setting offline cache flags;
  - storage layout and sizes;
  - environment configuration, by variable name only;
  - first start with no network;
  - backup and restore;
  - recovery from a missing or corrupt model;
  - the reconnection and synchronization procedure.

  Link it from L-8.
- **H-7 Benchmark report:**
  - local versus cloud, per capability, on the same benchmark through Ziad's harness: quality metrics, latency p50/p95, throughput, memory, quantization loss;
  - the task-specific acceptance verdict;
  - the run metadata (commit, benchmark checksum, hardware, model versions).

**Engineering principle: cloud connectivity enhances the platform; it is not a prerequisite for its core operation.** When a capability is unavailable, the system explains the limitation, preserves existing data, and keeps providing everything that still works.
