# Flame in Freefall × AURA AI: Integration Status Report

**Date:** 2026-10-05 · **Audited revisions:**

- Flame in Freefall (`FCDS-College/Nasa`): `origin/main` = `695fca8`, plus the unmerged branches `Belal` (`8e5e213`), `Princess` (`7af8c2a`), `Ziad` and `Eman`.
- AURA AI (`anasibrahimgnedy-collab/AURA-AI`): `main` = `3a60bca`.

**Companion files:** [`FRONTEND_API_CONTRACT.md`](FRONTEND_API_CONTRACT.md) (frontend source of truth) and [`openapi.json`](openapi.json) (OpenAPI 3.1.0, validated).

**Method:** every claim below was checked against source files, not READMEs or plans. Paths are repository-relative. Paths under `AURA-AI:` are in the AURA repository.

---

## 1. Executive summary

**Flame in Freefall is a data-and-design project today; there is no running backend.** What exists:

- a verified NASA source registry and file-provenance layer (121 checksummed file records);
- two ingestion scripts;
- an example CV output payload;
- a Next.js UI shell with no network code;
- on an unmerged branch, a CV notebook that validates and resizes images.

There is **no** `apps/api`, no database, no Docker/Compose, no CI, no AI/RAG code, no CV detection or segmentation, and no OpenAPI document. None of the ten frontend endpoints is implemented.

**AURA integration has not started, by design.** The MVP plan (`docs/plan/Nasa - MVP Plan.pdf` §2 "Non-goals" and §24) puts AURA out of scope for the MVP and the six-week build. Its future direction is **AURA → Flame API**: AURA consumes Flame's stable API and never couples to Flame internals.

The AURA codebase is mature and *could* serve as Flame's reasoning layer. The audit found two hard blockers and one integrity issue:

1. AURA has no service-to-service credential (only per-user JWTs).
2. AURA's `/api/v3/chat` has no field for caller-supplied evidence or structured output.
3. Pushing NASA text through the chat `message` field would put untrusted documents on AURA's USER trust channel. That bypasses AURA's own ADR-006 defence.

**Deliverables produced by this audit**

- **The frontend API contract** (10 operations on 9 paths): `docs/openapi.json`. It passes `openapi-spec-validator`, and `@redocly/cli lint` reports 0 errors and 0 warnings. `openapi-typescript` generates types from it, and a strict `tsc` check over a sample client passes. A Prism mock server serves its examples.
- **The AURA boundary design** (§3).
- **The prioritised work list** (§9 to §12).

| Readiness | Level |
|---|---|
| AURA integration | **0% implemented**. Boundary designed. The outbound path is **blocked** on AURA service auth. |
| Flame backend for the dashboard | **0 of 10 operations implemented.** Contract complete. |
| Frontend typed client | **Can be generated now** from `docs/openapi.json` and run against a mock. Real data needs the P0 backend work in §9. |

---

## 2. Current architecture (as found in code)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ apps/web  Next.js 16.3.8 / React 19.2.8 shell (main)                             │
│   AppShell, Sidebar (7 <a> links), TopBar (hard-coded "System Online"),          │
│   Badge/Card/MetricCard/StateCard. NO fetch/API client/env usage.                │
│   Branch Belal: 7 placeholder pages ("coming soon"), StateCard removed.          │
└────────────────────────────────────────────────────────────────────────────────┘
                     (no API layer: apps/api does not exist)
┌──────────────────────────────┐  ┌─────────────────────────────────────────────┐
│ cv/                          │  │ knowledge/ingestion/                        │
│  contracts/analysis_result   │  │  psi_download.py   (PSI API mirror)         │
│   .json (example payload)    │  │  record_provenance.py (sha256 + files.jsonl)│
│  pipeline.py (1 comment line)│  └─────────────────────────────────────────────┘
│ Branch Princess:             │  ┌─────────────────────────────────────────────┐
│  CVmodel.ipynb: validate +   │  │ datasets/                                   │
│  EXIF + RGB + resize 512²,   │  │  registry/source_registry.csv + .schema.json│
│  sha256, JSONL manifest.     │  │   (7 sources)                               │
│  NO detection/segmentation.  │  │  metadata/files.jsonl (121 records)         │
└──────────────────────────────┘  │  checksums/sha256.txt, manifests/           │
                                  │  raw/ derived/ (git-ignored, not in repo)   │
ai/  infrastructure/  tests/      └─────────────────────────────────────────────┘
 → README stubs, "not started"
```

Evidence, one line each:

| Area | File(s) | Finding |
|---|---|---|
| Frontend | `apps/web/package.json`, `apps/web/app/page.tsx`, `apps/web/components/layout/TopBar.tsx:13-17` | Scripts are `dev/build/start/lint` only. Metric cards render `"—"`. TopBar is a static green dot labelled "System Online". There is no `lib/`, `fetch`, or `process.env`. |
| Frontend (unmerged) | `origin/Belal: apps/web/app/{research,search,evidence,experiments,analysis,history,status}/page.tsx` | Seven identical placeholder pages. All export `ResearchPage` and render "Research workspace — coming soon." |
| Backend/API | `apps/README.md` ("Status: not started"); `git ls-files` | No `apps/api`. The only Python is `cv/pipeline.py` (a comment) and two ingestion scripts. `git grep` for fastapi/sqlalchemy/alembic/redis/minio/ollama/torch/cv2 matches only READMEs and docs. |
| Infra | `infrastructure/README.md` ("Status: not started") | No Dockerfile, no compose file, no `.env.example`, no `.github/`. |
| AI (RAG/CAG/MAG) | `ai/README.md` ("Status: not started") | No code. |
| CV | `cv/pipeline.py` (1 comment line); `cv/contracts/analysis_result.json`; `origin/Princess:cv/CVmodel.ipynb` | Example payload with internal contradictions (DAY2_TASKS §5). The notebook writes `"detectorBaseline": "Contour-Based-Thresholding-v1.0"` into its manifest, but **no thresholding/contour code exists in it** (no `cv2`, threshold, contour or mask call). It is a label only. |
| Data/provenance | `datasets/registry/*`, `datasets/metadata/files.jsonl`, `knowledge/ingestion/record_provenance.py` | Implemented and the strongest asset. Per-file sha256, source URL, retrieval time, `parent_file_id`. Known gaps (DAY2_TASKS §4): the CSV fails its own schema (`;` arrays, literal `"null"`), and the three NTRS PDFs in `docs/research/` are not registered. |
| Sample CV data | `origin/Princess:datasets/samples/cv/manifest.jsonl` | FLEX frames converted BMP→PNG with sha256 and `parent_file_id`. This is good provenance practice to reuse for analysis inputs (`source_file_id`, `frame_index` in the contract). |
| Tests | `tests/README.md`; `tests/eval/day1_ziad/*` | No automated tests. The archived Day 1 eval uses a fictional domain with hand-typed scores (DAY2_TASKS §7). |
| OpenAPI | repository-wide search for `openapi*`/`swagger*` | None existed before this audit. |

**Target architecture** (MVP plan §3, §12; unchanged by this audit): Next.js → FastAPI service layer → AI orchestrator → model router → {Ollama/vLLM, PyTorch CV} → knowledge engine (RAG/CAG/MAG) → evidence and provenance → PostgreSQL + pgvector + S3/MinIO, with Redis as a non-authoritative cache.

---

## 3. AURA integration assessment

### 3.1 What AURA actually offers (verified in `AURA-AI` at `3a60bca`)

| Capability | Where | Relevant facts |
|---|---|---|
| HTTP API | `AURA-AI: aura_backend/aura_core/api/v3.py:102` (`/api/v3`) | 30 routes, including `POST /chat` (`:277`), `POST /chat/stream` (`:334`), `POST /knowledge/documents` (`:443`), `POST /knowledge/documents/upload` (`:470`, PDF with page-aware extraction and OCR), `POST /knowledge/search` (`:523`), `GET /knowledge/documents` (`:640`), and memory and feedback routes. |
| Health | `v3.py:1291` `/health/live`, `:1298` `/health/ready` (503 when unhealthy), `:1309` `/health/version`; `container.py:1492` | Readiness reports providers, index, tools and environment. Flame can probe `/health/ready` for its `services.aura`. |
| Auth | `AURA-AI: aura_backend/aura_service.py:34-110` | Bearer JWT verified by `services/jwt_auth.verify_access_token` (`services/jwt_auth.py:272`). Subject is the `uid` claim. Tokens are issued per **user** (`issue_token_pair`) or per **paired device** (`issue_device_token`). **No API key, client-credentials or service principal exists.** The plan for one is AP12a "scoped API keys per surface", status **DOCUMENTED** (`docs/roadmaps/AURA_ADAPTIVE_PLATFORM_ROADMAP.md:687,749`). |
| Chat request | `v3.py:106-125` `ChatRequest` | `message` (≤ 32k), `use_knowledge/use_memory/use_tools`, `plan`, `require_local`, `max_output_tokens`, `temperature`. There is **no field for caller-supplied context or evidence and no response schema or structured-output option.** |
| Chat response | `v3.py:308-331` | `message`, `citations: string[]`, `confidence`, `provider`, `model`, `cached`, `degraded`, `correlation_id`, `turn_id`, `usage`. |
| Citations | `AURA-AI: aura_core/domain/knowledge.py:170-186` | A citation is the string `"{document_id}@v{version} (page N)"`, keyed to **AURA's** document IDs. |
| RAG/CAG/MAG | `aura_core/knowledge`, `cag`, `memory`; `v3.py:523` | Hybrid retrieval, CAG pinning, scoped memory. Retrieval is **per owner** (`owner_id=caller.user_id`). |
| Trust channels | `AURA-AI: aura_core/domain/messages.py:3-51` (ADR-006) | Retrieved chunks and tool output travel on `DATA` and are "never instructions". **Text placed in `message` is on the `USER` channel.** |
| Model routing | `aura_core/llm/router.py` (5 policies, failover before the first token) | Self-hosted only: `echo`, `openai_compatible`, `ollama` (`CLAUDE.md`, fitness-tested). |
| Throughput | `AURA-AI: CLAUDE.md` ("Deploy") | Production LLM is `qwen2.5:3b` on CPU at **~5–10 tokens/s**. The planner's 700 tokens are budgeted against a 180 s timeout. |
| Multimodal | `aura_core/domain/llm.py:115-120` | `Modality.IMAGE` exists as **provider capability metadata only**. No v3 route accepts an image for a model (only PDFs via upload, and audio for voice). |
| Async jobs | `v3.py` `/agents/runs`, `/engineering/runs` | Agent-run records for AURA's own agents. There is **no generic job API** for external callers. |
| Webhooks | – | None for external consumers. |
| Idempotency | `v3.py:177-180` (`Idempotency-Key`) | Available on `/chat` and ingestion. |
| Attach-to-existing-system | `aura_core/adaptation/connectors.py`; `domain/connectors.py:48-58` (`OPENAPI`, `POSTGRES`, …) | Track AP: AURA can register a **read-only OpenAPI connector** to an external API and generate tools from it. AP3 (OpenAPI discovery) is **IMPLEMENTED, CI pending**. AP7 is implemented, but its dev-stack run and CI are pending (roadmap `:740-744`): built, not proven. |

### 3.2 Recommended boundary

The pattern requested in the brief (Dashboard → Flame API → {Scientific Layer, AURA} → Evidence Layer) is **correct in its key property**: the frontend sees only Flame's API. The code adds two refinements:

1. **The Flame → AURA call is optional, asynchronous and post-validated**, and it is used only for *interpretation*. AURA never computes measurements and never owns evidence. Three facts drive this:
   - AURA's RAG cites AURA document IDs, not Flame evidence IDs.
   - Its CPU throughput makes any synchronous call a 30–90 s request.
   - Its output is free text with no claim classes.
2. **The MVP plan's own direction (AURA → Flame) is the second, independent link.** AURA consumes Flame's public API through a Track AP read-only OpenAPI connector. It never reads Flame's database, vector index or buckets.

```
                         Next.js dashboard (apps/web)
                                   │  HTTPS/JSON — docs/openapi.json only
                                   ▼
                    ┌──────── Flame API (apps/api, FastAPI) ────────┐
                    │  auth boundary · request_id · error envelope  │
                    └──┬──────────┬───────────┬──────────┬──────────┘
                       │          │           │          │
           Search/Documents   Evidence/    Flame CV     Analysis history
           /Experiments       Provenance   (worker,     (Postgres records +
           (Postgres FTS →    (evidence    queue)       object storage
            pgvector hybrid)   table)         │          artefacts)
                       │          │           │
                       └────┬─────┴───────────┘
                            ▼
              PostgreSQL + pgvector · MinIO/S3 · Redis (cache, queue)
                            ▲
                            │ (Flame-owned; AURA never touches these)
   ┌────────────────────────┴───────────────────────────────────────────┐
   │ OPTIONAL, ASYNC — InterpretationProvider port inside Flame          │
   │   AuraInterpreter ──► AURA /api/v3/chat ──► Flame validator ──►     │
   │   (after measurements are final)  statements[] with verified        │
   │                                   evidence_ids, or rejected         │
   └────────────────────────────────────────────────────────────────────┘
   FUTURE (MVP plan §24): AURA ──read-only OpenAPI connector──► Flame API
```

**Ownership**

| Belongs to Flame in Freefall | Belongs to AURA | Stays independent |
|---|---|---|
| Source registry, ingestion, file/sha256 provenance | General reasoning/generation via its router (Ollama/OpenAI-compatible) | The two databases, vector stores and object stores |
| Document, experiment and condition records; the **evidence table** | Session memory and conversational UX in AURA's own clients | Model weights/serving for CV (Flame-only) |
| Search API (lexical → hybrid) over the Flame corpus | Optional: its knowledge store as a *mirror* of Flame passages (Option B below) | Auth domains (separate issuers; a scoped credential links them) |
| CV pipeline: validation, detection, segmentation, **all measurements**, quality flags, artefacts | Track AP connector, if AURA should consume Flame | Frontend ↔ AURA: no direct link, ever |
| Claim-class labelling and **validation of every AI statement** | | |
| The frontend contract (`docs/openapi.json`) | | |

**Data that crosses the boundary (Flame → AURA, per interpretation):**

- *Sent:* the analysis's measured values, units, classes and quality flags (Flame-generated, trusted); the image's experiment conditions when linked; a fixed instruction template; and `Idempotency-Key: <analysis_id>` plus `X-Correlation-Id: <request_id>`.
- *Never sent:* raw images (AURA has no image route), database rows, or credentials.
- *Received:* text, a `citations[]` of strings, `model` and `provider`.

**API classes**

| Class | APIs |
|---|---|
| Frontend-facing | The 10 operations in `docs/openapi.json`, nothing else. |
| Flame-internal | CV worker job queue, `InterpretationProvider`, repositories. These are not HTTP-exposed. |
| AURA-facing (outbound) | Existing `POST /api/v3/chat`, `GET /health/ready`, and for Option B `POST /api/v3/knowledge/documents`. **No new Flame endpoint is created for AURA.** |
| Flame-facing for AURA (inbound, future) | The same public `/api/*`, consumed through the AURA OpenAPI connector with a scoped Flame credential. |

### 3.3 The two options for grounding AURA's interpretation

| | Option A: measurements only (recommended first) | Option B: Flame corpus mirrored into AURA |
|---|---|---|
| Call | `POST /api/v3/chat` with `use_knowledge=false, use_memory=false, use_tools=false, plan=false, require_local=true, max_output_tokens≈400` | Ingest each published Flame passage with `POST /api/v3/knowledge/documents` using `document_id = <Flame document ULID>` and `metadata.page`. Then `/chat` with `use_knowledge=true`. |
| Evidence | None. Every AURA statement is stored as `hypothesized` or `unsupported`, with `evidence_ids: []`. | AURA citations `"{flame_doc_id}@v1 (page 5)"` resolve to Flame `(document_id, page)` → `evidence_id`. A citation that does not resolve causes the statement to be rejected. |
| Trust | Only Flame-generated numbers go in `message` (no untrusted text on USER). | Passages stay on AURA's DATA channel (ADR-006 preserved). |
| Cost / risk | Trivial | Duplicated corpus with version drift. AURA chooses which evidence to retrieve. Re-ingest on every `knowledge_version` publish. |
| Blocked by | AURA service credential | Same, plus a mirror job and version sync |

Option C, putting NASA passages into `message`, is **rejected**. It moves untrusted document text onto AURA's USER channel and defeats its prompt-injection controls.

**Timeouts and failure behaviour (both options):**

- The call runs only in the analysis worker *after* `result` is final, with a 120 s timeout (sized for ~400 tokens at 5–10 tok/s with planning off).
- On timeout, 5xx, 429 or a circuit break, set `interpretation.status = "unavailable"` and add the warning `INTERPRETATION_UNAVAILABLE`. The analysis remains `completed`.
- Flame parses AURA's text into statements. Anything unparseable, any statement claiming a disallowed class (`observed`/`measured`/`estimated`), and anything mentioning temperature is dropped and counted in `rejected_statement_count`.

---

## 4. Current implementation status

Legend: **IMPLEMENTED**, **PARTIAL**, **PLANNED** (documented, no code), **MOCKED**, **MISSING** (not even planned in detail), **BLOCKED**, **REQ-AURA** (requires AURA-side work), **REQ-BACKEND** (requires Flame backend work).

| Area | Current status | Evidence | Existing implementation | Missing work | Integration needed |
|---|---|---|---|---|---|
| Backend API | MISSING / REQ-BACKEND | `apps/README.md` "not started"; no `apps/api` in `git ls-files` | None | FastAPI app, routers, Pydantic models matching `openapi.json`, error envelope, request-ID middleware | Contract tests against `docs/openapi.json` |
| Health | MISSING | No route. `TopBar.tsx:13-17` hard-codes "System Online" | None (static UI) | `GET /api/health` with dependency probes | Frontend status page + TopBar |
| Documents | PARTIAL (data only) | `datasets/metadata/files.jsonl` (121 file records), `docs/research/*.pdf` (3 PDFs, unregistered) | File provenance records; no `document` records | Document records, PyMuPDF page extraction, `document` table, `GET /api/documents/{id}` | – |
| Experiments | PARTIAL (data only) | Registry rows FF-PSI-25/69/98/107; BASS-II table file `sha256:71e792bf6b5fb5ea` in `files.jsonl` | Raw tables mirrored (git-ignored) | Table parsers → `experiment` / `experiment_condition` with SI columns; `GET /api/experiments/{id}` | – |
| Analyses | PARTIAL (preprocessing only, unmerged) | `origin/Princess:cv/CVmodel.ipynb`; `cv/contracts/analysis_result.json` | Validate, EXIF, RGB, 512² resize, sha256 (notebook) | Detection, segmentation, measurements, artefacts, job worker, persistence, 3 endpoints | – |
| Search | MISSING | `ai/README.md` "not started" | None | Postgres FTS over page chunks, then pgvector hybrid; `GET /api/search` | – |
| Evidence | PLANNED | Field list: `docs/data/DATA_DICTIONARY.md` "Evidence-level fields" | Schema on paper only | `evidence` table, writers in parsers/CV, `GET /api/evidence/{id}` | – |
| Flame analysis | PLANNED / MOCKED | `cv/contracts/analysis_result.json` is an example with nulls and contradictory confidences; notebook's `detectorBaseline` is a label with no code behind it | None that measures | Whole CV stage per MVP plan §10 | Optional AURA interpretation |
| Analysis history | MISSING | – | – | `analysis_result` table, list/detail endpoints | – |
| RAG | MISSING | `ai/README.md` | – | Retriever, reranker, answer composer, citation validation (MVP plan §6) | Option: AURA as reasoning layer (§3.3) |
| CAG | MISSING | `ai/README.md` | – | Redis cache with version manifests | – |
| MAG | MISSING | `ai/README.md` | – | Session memory (MVP plan §6) | AURA has MAG, but plan §6 says memory is never evidence |
| AURA integration | MISSING by design; **BLOCKED** outbound; REQ-AURA | MVP plan §2, §24; `AURA-AI: aura_service.py:34-110` (user JWT only) | None | `InterpretationProvider` + `AuraInterpreter` in Flame | AURA service credential (AP12a); optional context/structured-output field |
| OpenAPI | **IMPLEMENTED (spec only)** | `docs/openapi.json` (this audit) | Hand-authored 3.1.0 spec, validated, with schema-checked examples | FastAPI must serve an equivalent `/api/openapi.json` plus a diff test | Frontend codegen |
| Authentication | MISSING | No code; MVP plan §12 asks for a dev `AuthContext` | – | Dev identity adapter, `AuthContext` interface; bearer optional in v0.1 | Scoped credential if AURA calls Flame |
| Storage | MISSING (local mirror only) | `.gitignore` excludes `datasets/raw/`, `datasets/derived/` | Files on a developer disk | MinIO/S3 service, artefact keys by sha256 | – |
| Model serving | MISSING | No Ollama/vLLM/PyTorch code or config | – | Router, Ollama dev provider, CV model packaging | AURA router is an alternative for text only |
| Observability | MISSING | – | – | JSON logs with request_id, OpenTelemetry spans (MVP plan §12) | Propagate `X-Correlation-Id` to AURA |

---

## 5. Integration gaps

1. **Nothing to integrate yet on the Flame side.** AURA can only be attached to a Flame API and a Flame CV result, and neither exists.
2. **Service identity:** AURA accepts only user or device JWTs (`aura_service.py:34-110`). Flame needs a scoped, non-human credential, and AP12a is documented only.
3. **Caller-supplied context:** `ChatRequest` (`v3.py:106`) cannot carry DATA-channel context, so Option C is unsafe and Option B needs a mirror.
4. **Structured output:** AURA returns free text, while Flame needs typed statements with claim classes. For now Flame must parse and validate the text. A JSON-schema response mode in AURA would remove that fragility.
5. **Citation identity:** AURA citations reference AURA document IDs. Only Option B (ingesting with Flame's document ID) makes them resolvable.
6. **Latency:** CPU-only AURA sits at ~5–10 tok/s, which forces asynchronous interpretation. This is already reflected in the contract (`interpretation.status = pending`).
7. **Image understanding:** AURA has no image-input route. All visual analysis stays in Flame's CV pipeline, and that is the correct boundary anyway.

---

## 6. Final frontend API contract (summary)

The full per-endpoint documentation is in [`FRONTEND_API_CONTRACT.md`](FRONTEND_API_CONTRACT.md).

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| GET | `/api/health` | System health / dependency status | REQ-BACKEND |
| GET | `/api/dashboard/counts` | Documents / experiments / analyses counts | REQ-BACKEND |
| GET | `/api/search` | Research search (lexical → hybrid) | REQ-BACKEND |
| GET | `/api/documents/{document_id}` | Document details and provenance | REQ-BACKEND |
| GET | `/api/experiments/{experiment_id}` | Experiment conditions (target of experiment hits) | REQ-BACKEND |
| GET | `/api/evidence/{evidence_id}` | Evidence and provenance | REQ-BACKEND |
| POST | `/api/analyses` | Upload image → 202, async flame analysis | REQ-BACKEND (+ CV) |
| GET | `/api/analyses` | Analysis history | REQ-BACKEND |
| GET | `/api/analyses/{analysis_id}` | Status, result, measurements, interpretation | REQ-BACKEND (+ CV) |
| GET | `/api/analyses/{analysis_id}/artifacts/{artifact_kind}` | Original / preprocessed / mask / overlay image | REQ-BACKEND (+ storage) |

Key decisions:

- **Async analysis** with states `queued / processing / completed / failed / cancelled`.
- **Evidence is a resource; claims are embedded** statements carrying `evidence_ids`.
- **No temperature field.** Pixel measurements are `measured`; scale-derived millimetres are `estimated`.
- **One error envelope** `{ "error": { code, message, request_id, retryable, field_errors, details } }`.
- **Artefacts are served through the API**, never as raw bucket URLs.
- **`aura` is a health entry and an interpretation provider**, never a dependency of any endpoint.

---

## 7. OpenAPI status

| Item | Value |
|---|---|
| Existed before the audit? | **No.** No `openapi.*` or `swagger.*` file, and no FastAPI app to generate one. |
| File | `docs/openapi.json` |
| Version | OpenAPI **3.1.0**, API `info.version` **0.1.0** |
| Content | 9 paths / 10 operations, 81 component schemas, shared parameters, headers, responses and `bearerAuth`. Every operation has `x-implementation-status: not_implemented`. 10 response examples. |
| Validation | `openapi-spec-validator` → **OK**. `@redocly/cli lint` (recommended ruleset) → **valid, 0 warnings**. All 10 examples validated against their schemas with JSON Schema 2020-12 at generation time. |
| Codegen check | `openapi-typescript` 7.13.0 + TypeScript 5.9.3 generate 1,631 lines of types. A strict `tsc --noEmit` over a sample client (discriminating `status`, reading `geometry_px.area.value`, asserting via `@ts-expect-error` that `Measurements.temperature` does not exist) **passes**. |
| Mock check | `@stoplight/prism-cli mock` serves `GET /api/health` (example body, 200) and `GET /api/analyses/{id}` (200), and rejects `GET /api/search` without `q` (400). |
| Served at runtime? | **No.** `/api/openapi.json` will exist once FastAPI is up (`FastAPI(openapi_url="/api/openapi.json")`), and a contract test must keep it equivalent to this file. |

---

## 8. Frontend integration guidance

1. **Generate the types now:** `npx openapi-typescript docs/openapi.json -o apps/web/lib/api/schema.d.ts`. Pin TypeScript 5.x, because openapi-typescript 7 does not run on TypeScript 6. Use `openapi-fetch` over the generated `paths`.
2. **Develop against a mock** (`npx @stoplight/prism-cli mock -p 4010 docs/openapi.json`) and switch per endpoint as `x-implementation-status` flips.
3. **Wire `/api` same-origin** with a Next.js `rewrites()` to the API service, so no CORS and no API host is baked into the client.
4. **Send `X-Request-ID`** on every call and show it in error toasts for support.
5. **State rules:**
   - Health starts as *unknown*.
   - Counts on error stay `—`, never 0.
   - Treat `null` quality flags as "not checked".
   - `searched_but_empty` is a result, not an error.
   - Render the interpretation panel separately from measurements, and label AI text.
6. **Fix the honesty issues already flagged:** the hard-coded "System Online" (`TopBar.tsx`), and the placeholder pages on `Belal` that all say "Research".
7. **Polling:** follow `poll_after_ms` and stop at a terminal status (FRONTEND_API_CONTRACT §5).

---

## 9. Backend work remaining (Flame, Lead + owners)

| # | Task | Owner | Unblocks |
|---|---|---|---|
| B1 | `infrastructure/compose`: api, postgres (pgvector image), redis, minio, with health checks; `.env.example` | Lead | Everything |
| B2 | `apps/api` skeleton: FastAPI, `openapi_url="/api/openapi.json"`, request-ID middleware, `ErrorResponse` exception handlers, dev `AuthContext` | Lead | All endpoints |
| B3 | `GET /api/health` with probes for postgres, pgvector, minio, redis, CV worker, llm and aura (all with timeouts) | Lead | Status page, TopBar |
| B4 | Alembic migrations: `source`, `file_record`, `document`, `document_chunk`, `evidence`, `experiment`, `experiment_condition`, `image_asset`, `analysis_result` (ULIDs, sha256 columns) | Lead + Eng 2 | Counts, search, evidence |
| B5 | Seed: registry (after the validator fix) + `files.jsonl` (121 rows) + 3 NTRS PDFs registered | Eng 2 | Documents |
| B6 | Page extraction (PyMuPDF) → `document_chunk` + `evidence` (verbatim_text, page locator); OCR flags | Eng 2 | Search, evidence |
| B7 | BASS-II/FLEX/SPICE tables → `experiment_condition` (+ `evidence` table_row) | Eng 2 | Experiments, counts |
| B8 | `GET /api/dashboard/counts`, `/api/documents/{id}`, `/api/experiments/{id}`, `/api/evidence/{id}` | Lead | Dashboard, viewer |
| B9 | `GET /api/search` (Postgres FTS, `domain` filter excluding FF-PSI-DSI, highlights) | Lead + Eng 1 | Search |
| B10 | CV stage per MVP plan §10: a classical baseline first (threshold + contours), with measurements mapped to original pixels, mask/overlay PNGs, `TEMPERATURE_NOT_AVAILABLE` always set, quality flags `null` until implemented | Eng 3 | Analysis |
| B11 | Upload validation (by content, 10 MiB, 64 px to 50 MP), MinIO storage by sha256, Redis job queue + worker, analysis persistence, the 4 analysis operations | Lead + Eng 3 | Analysis, history |
| B12 | Contract tests: served `/api/openapi.json` ≡ `docs/openapi.json`; schemathesis/Prism-proxy responses validate | Eng 5 + Lead | API stability |
| B13 | CI (GitHub Actions): Python lint + tests, web lint + typecheck, OpenAPI lint | Lead | Merge safety |

## 10. AURA work remaining

| # | Task | Side | Status |
|---|---|---|---|
| A1 | Scoped **service credential** for Flame (AP12a scoped API keys, or a dedicated JWT issuer with `uid=svc-flame`, its own role and a rate limit) | AURA | **BLOCKER**: DOCUMENTED only |
| A2 | `InterpretationProvider` port + `AuraInterpreter` adapter (Option A), behind `FLAME_AURA_ENABLED` (default false) | Flame | Not started (P2) |
| A3 | Statement parser and validator: allowed classes, evidence-ID resolution, temperature-claim filter, `rejected_statement_count` | Flame | Not started (P2) |
| A4 | `services.aura` health probe → AURA `GET /health/ready` | Flame | Not started (P1, trivial) |
| A5 | *(Option B)* Corpus mirror job into AURA, keyed by Flame document ULID, re-run per `knowledge_version` | Flame | Not started (P2/P3) |
| A6 | *(Nice-to-have)* `ChatRequest.context[]` on the DATA channel and a JSON-schema response mode | AURA | Not planned in AURA's roadmap |
| A7 | *(MVP plan §24, post-MVP)* Register Flame's `openapi.json` as an AURA read-only OpenAPI connector (Track AP), using a scoped Flame credential | Both | AURA side IMPLEMENTED but not proven (AP3/AP7); Flame API missing |

---

## 11. Risks

| Risk | Impact | Mitigation in the contract or plan |
|---|---|---|
| **Scientific validity:** RGB statistics read as physical quantities | False science in a NASA demo | No temperature field exists. `appearance.physical_interpretation: "none"`. `TEMPERATURE_NOT_AVAILABLE` on every result. Physical sizes only `estimated`, with a caller-stated `scale_source`. |
| **Evidence integrity:** AI citations that resolve to nothing | Fabricated provenance | Only `source_evidence` and `calculated_measurement` can be evidence. Every AI statement's `evidence_ids` is checked server-side, and failures are dropped and counted. `extraction_confidence` is null unless a method produced it. |
| **Model reliability:** CV not built; the baseline's confidence is meaningless | Misleading confidence badges | `detection.confidence` and `segmentation.confidence` are nullable. Classical baselines report null instead of an invented score. |
| **Latency:** CV on CPU/GPU unknown; AURA at 5–10 tok/s | Timeouts, frozen UI | Async from day one. Interpretation runs after measurements and its failure never fails the analysis. |
| **Asynchronous processing:** lost jobs, duplicates | Stuck `processing` rows | `Idempotency-Key`. Worker heartbeats; on timeout set `failed` with code `TIMEOUT`. Clients give up after 5 min and the record stays in History. |
| **Storage:** artefacts on laptops today | Irreproducible results | MinIO keyed by sha256. Originals immutable. Artefacts served through the API with `ETag` = sha256. |
| **API stability:** a contract written before code | Drift between doc and FastAPI | `x-implementation-status` per operation. Contract diff test (B12). Semver in `meta.api_version`. |
| **Authentication:** optional bearer in v0.1 | Uploads open on a public deploy | Keep the demo deploy private or behind basic auth at the proxy. Make bearer required before any public URL. |
| **AURA dependency:** AURA down, or its contract changes | Lost interpretations | AURA is never on the request path, its status is reported as `disabled/down` in health, and nothing in the six dashboard areas requires it. |
| **Team integration:** branches far behind `main` (`Eman` at the initial commit) | Merge conflicts on moved folders | Branch fresh from `main` (DAY2_TASKS §1). |

---

## 12. Recommended implementation sequence

**P0: make the dashboard real (Days 2–6)**

1. B1 Compose → B2 API skeleton → B3 `/api/health`. The frontend replaces the hard-coded status.
2. B4 migrations → B5 seed → B8 `/api/dashboard/counts`. The metric cards show real numbers.
3. B6 page extraction → B8 documents and evidence endpoints → B9 lexical search.
4. B12 contract test and B13 CI from the first endpoint onward.

**P1: flame analysis end to end (Days 8–11)**

5. B10 classical CV baseline (honest nulls, warnings) → B11 upload, queue, worker, artefacts → the 4 analysis operations.
6. B7 experiment conditions → `/api/experiments/{id}` and analysis↔experiment links.
7. A4 AURA health probe (reports `disabled` until configured).

**P2: intelligence (Days 12–14, then Weeks 3–6)**

8. Hybrid retrieval (pgvector) behind the same `/api/search` (`retrieval.mode = "hybrid"`).
9. A1 (AURA service credential) → A2 + A3 Option A interpretation behind a flag.
10. `POST /api/chat` per MVP plan §12, either on Flame's own router or via AURA Option B. Decide based on the Day 7 RAG evaluation results, not on preference.
11. A7: AURA consumes Flame through the Track AP OpenAPI connector (MVP plan §24).
