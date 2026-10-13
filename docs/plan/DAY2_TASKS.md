# Day 2 Task Lists + Day 1 Review

> **Status (2026-10-12): MVP task list, superseded** by the [Phase 2 plan](PHASE2_PLAN.md). Its open items are carried over there as M1–M13.

**Date:** 2026-10-04 · **Basis:** MVP plan §15 (team responsibilities) and §16 (two-week plan), checked against `origin/main` at `2e0f9e8`, the remote branches, and the local `Eng5/` folder.
**Day 2 theme (MVP plan §16):** *Database/vector foundation, source registry, first NASA sources.*

---

## 1. Day 1 status at a glance

| Role | Day 1 requirement (§16) | Delivered | Status |
|---|---|---|---|
| **Lead** (Anas) | Monorepo, Compose, ADRs, API skeleton | Repo layout + READMEs (restructure commits `060ffbc`, `563d4f4`, `691826f`) | ⚠️ Partial: **no Compose, no ADRs, no API skeleton, no CI** |
| **Engineer 1** (Eman): AI/RAG | RAG/MAG interfaces, prompt registry outline | `ai/README.md` stub only | ❌ Not started |
| **Engineer 2** (Anas): Data | Source registry schema, P0 candidates | Registry + schema, data dictionary, acquisition spec, DSI mirror, **PSI combustion inventory + 3.1 GB pilot**, provenance scripts | ✅ Done, with fixes below |
| **Engineer 3** (Princess): CV | CV IO / AnalysisResult contract | `cv/contracts/analysis_result.json` (example payload), `cv/pipeline.py` (one comment line) | ⚠️ Partial: contract has inconsistencies, no schema |
| **Engineer 4** (Belal): Frontend | Next.js shell / design system | `apps/web` (Belal, PR #4): AppShell, Sidebar, TopBar, Badge/Card/MetricCard/StateCard | ✅ Done, with fixes below |
| **Engineer 5** (Ziad): Evaluation | Evaluation rubric, JSONL schema, acceptance baseline | 20 test cases + 3 notebooks (now archived in `tests/eval/day1_ziad/`) | ❌ Needs a redo (wrong domain, scores typed in by hand) |

**Team-wide issues**
- Branches `Princess` and `Ziad` stop at the pre-restructure layout, and `Eman` is still at the initial commit. Everyone should **branch fresh from the latest `main`** before Day 2 work. Otherwise merges will conflict on the moved folders (`data/` → `datasets/`, `CV/` → `cv/`, `Docs/` → `docs/`).
- Use one branch per task, a small PR into `main`, and at least one reviewer. Don't merge `main` into personal branches and back again (see merge commits `1c0b667`, `db16ba5`).
- ✅ Done 2026-10-04: the untracked `Eng5/` folder was archived to `tests/eval/day1_ziad/`, and its MVP-plan PDF (an exact duplicate) was removed.

---

## 2. Lead (Anas): Backend, AI infrastructure, platform

### Day 1 carry-over (do first)
- [ ] **`infrastructure/compose/docker-compose.yml`** with `api`, `postgres` (pgvector image), `redis` and `minio`, plus health checks. Secrets go in `.env` (git-ignored), with a committed `.env.example`.
- [ ] **`apps/api` skeleton**: FastAPI + Pydantic, `GET /api/health` returning `request_id`, server time, API version and the status of each dependency (db/redis/object store). Use the RFC 7807 error envelope (§12).
- [ ] **ADRs** in `docs/architecture/adr/`:
  - ADR-001 monorepo layout
  - ADR-002 Postgres + pgvector before a dedicated vector DB
  - ADR-003 provider-neutral model router
- [ ] **CI** (GitHub Actions): Python lint + tests and web lint + typecheck on every PR.

### Day 2: database/vector foundation (§16)
- [ ] Postgres, pgvector, Redis and MinIO running via Compose, reachable from `apps/api`.
- [ ] **Alembic migrations** for the §9 core tables:
  - `source` (mirrors `datasets/registry/source_registry.csv`)
  - `file_record` (mirrors `datasets/metadata/files.jsonl`)
  - `document`, `document_chunk` (with a `vector` column and the embedding version)
  - `evidence`, `experiment`, `experiment_condition`, `image_asset`, `analysis_result`
- [ ] Use **ULID primary keys**, `sha256` columns for artefacts, and `created_at`/`version` columns.
- [ ] A seed script that loads the registry and `files.jsonl` into `source`/`file_record`. That proves the data path end to end.
- [ ] Publish the OpenAPI document at `/api/openapi.json` (Engineer 4 generates the client from it).

**Done when:** `docker compose up` brings up a healthy stack, `GET /api/health` reports every dependency green, migrations apply to an empty DB, and `file_record` holds 121 rows that match `files.jsonl`.

---

## 3. Engineer 1 (Eman): AI / RAG / context engineering

### Day 1 carry-over
- [ ] **Interfaces** (Python `Protocol`s or ABCs, no implementations yet) in `ai/`: `Retriever`, `Reranker`, `EmbeddingProvider`, `LLMProvider`, `CacheService`, `MemoryStore`, `AnswerComposer`.
- [ ] **Prompt registry outline** in `ai/prompts/`: one file per prompt with `id`, `version`, `purpose`, `template`, `required_variables` and `output_schema`. Include the grounded-answer and the evidence-insufficient prompts.

### Day 2: retrieval DTOs and cache-key design (§16)
- [ ] **Pydantic DTOs** in `ai/rag/dto.py`:
  - `RetrievalRequest`: `query`, `rewritten_query?`, `filters`, `top_k`. Filters cover domain, source_id, document_type, experiment, gravity_regime.
  - `RetrievedChunk`: `chunk_id`, `evidence_id`, `document_id`, `source_id`, `locator` (page/section/row/frame), `score_dense`, `score_lexical`, `score_fused`, `rerank_score?`, `corpus_version`.
  - `EvidenceBundle`: chunks plus `retriever_version`, `reranker_version`, `embedding_model@version`, and `token_budget_used`.
- [ ] **Cache-key spec** (`docs/architecture/cache_keys.md`):
  - Key pattern: `rag:v1:corpus:{corpus_version}:emb:{model}@{ver}:retr:{ver}:rerank:{ver}:{sha256(normalized_query + sorted_filters)}`
  - A **dependency manifest** per entry.
  - Invalidation rules for each §6 cache type.
- [ ] **Domain filter rule:** non-combustion sources (`FF-PSI-DSI`) must never be retrieved for combustion questions. Encode this as a default filter and write a test for it.
- [ ] Agree DTO field names with Engineer 2 (evidence/locator) and the Lead (DB columns) **before** the end of the day.

**Done when:** the DTOs import cleanly, the unit tests validate example payloads, and the cache-key doc is reviewed by the Lead.

---

## 4. Engineer 2 (Anas): Scientific data / knowledge base

### Day 1 fixes
- [ ] **Registry validator** (`knowledge/ingestion/validate_registry.py`):
  - Split `;` arrays.
  - Map literal `"null"` strings to real nulls.
  - Validate each row against `datasets/registry/source_registry.schema.json`, and fail CI on errors.
  - Today the CSV would fail the schema: array fields are strings and nulls are the text `"null"`.
- [ ] **Register the 3 NTRS PDFs** in `docs/research/` as `technical_report` rows: `20000034017` (NASA/TM-2000-209773), `20040053557` and `20080034883` (NASA/TM-2008-215260).
- [ ] Fill in the **DSI PSI DOI** (registry row `FF-PSI-DSI`).
- [x] ~~Move the in-place extraction to `datasets/derived/DSI/`~~: done 2026-10-04; the old `data/` folder is gone.
- [ ] Note in `P0_CANDIDATES.md` that the P0 combustion data *is* downloadable through the PSI API (see `docs/data/CV_IMAGE_SOURCES.md`).

### Day 2: registry and first NASA documents (§16)
- [ ] **Document records** for the first corpus:
  - the 3 NTRS PDFs
  - the pilot's PSI documents: BASS-II SRD and Summary Report, FLEX Test Plan, SPICE Final Report and thesis, SAFFIRE objectives
- [ ] For each document record: `document_id`, `source_id`, title, identifier/DOI, `file_id` (sha256 from `files.jsonl`), page count, text-layer present yes/no, and `parser_version`.
- [ ] **Page-aware text extraction** (PyMuPDF) to `datasets/processed/documents/<document_id>.jsonl`, one record per page with the text and the page number.
  - Flag pages with no text layer for OCR. Example: `20080034883.pdf` pp. 14–15.
- [ ] **Experiment tables to conditions:**
  - Parse the BASS-II (129 tests), FLEX and SPICE experimental-table CSVs into `ExperimentCondition` rows.
  - Store the original value + unit + an SI column, per the units policy in `DATA_DICTIONARY.md`.
  - Use `null`, never `0`, for missing values.
- [ ] Hand the Lead a loader for these into the `document` and `experiment_condition` tables.

**Done when:** every registry row validates, ≥ 10 NASA documents have page-level records traceable to a sha256, and BASS-II conditions are queryable by test ID (e.g. B1 → 100 µm PMMA film, initial O₂ 22.2 %).

---

## 5. Engineer 3 (Princess): Computer vision / PyTorch

### Day 1 fixes to `cv/contracts/analysis_result.json`
- [ ] Turn the example into a **JSON Schema** (`analysis_result.schema.json`) and keep one **valid** example beside it.
- [ ] Fix the internal contradictions in the current example:
  - `detection.status: "PRESENT"` with `detection.confidence: null` and a null bounding box, while `detectorConfidence: 0.96` appears elsewhere. **Pick one place for confidence.**
  - `classification: "MEASURED"` while every measurement is `null`. MEASURED requires values.
  - `saturationScore: 0.85` while the colour means are `null`.
  - Remove the leftover text `[cite: 8]` from the warning string.
- [ ] Add the missing provenance and metadata fields:
  - input `image_sha256` and `source_file_id`, plus frame index/timecode when the image comes from video
  - `schema_version`, `request_id`, `created_at`
  - model artefact digest
  - explicit **units** (`px`, `px²`)
- [ ] Replace the one-line `cv/pipeline.py` with typed function stubs for each stage (validate → preprocess → detect → segment → features → measurements → confidence), each returning a typed result.

### Day 2: image dataset intake specification (§16)
Write `docs/data/IMAGE_INTAKE_SPEC.md` and a small reference script:
- [ ] **Sources and formats from the pilot** (`datasets/raw/psi_api/`):
  - FLEX BMP/TIFF sequences (8 fuel × diluent classes, about 9,200 frames)
  - SAFFIRE-I JPEG (1,556 frames)
  - SPICE PNG/JPEG (65 frames)
  - BASS-II MP4 (17 videos)
  - Record the bit depth and colour/mono for each camera. Check the FLEX TIFFs before assuming RGB.
- [ ] **Frame sampling rule:** every *k*-th frame, with a per-test cap, so near-duplicates don't dominate.
- [ ] **Derived layout:** `datasets/derived/frames/<source_id>/<test_id>/frame_<idx>.png` (never under `raw/`).
- [ ] **Frame record fields** (from `DAY1_DATA_ACQUISITION.md`): `media_id`, `source_file_id`, `test_id`, `frame_index`/`timecode`, `width`, `height`, `fps`, `extraction_method`, `sha256`.
- [ ] **Label set:** `flame`, `igniter/hardware`, `back-lit/illumination frame (not flame)`, `background`. Masks are PNG; every label record carries the annotator and the date.
- [ ] **Quality-flag definitions with numeric thresholds:** blur, saturation/clipping, low light, multiple flames, occlusion, scale absent, calibration absent.
- [ ] **Split rule:** split by **test**, never by frame, and keep a holdout of whole tests per investigation.
- [ ] Reference extraction script run on **1 test per source**, writing frame records with sha256.

**Done when:** the spec is reviewed by Engineers 2 and 5, the contract schema validates its own example, and about 50 sample frames exist in `datasets/derived/` with records traceable to raw sha256s.

---

## 6. Engineer 4: Frontend / visualization (Belal)

### Day 1 fixes to `apps/web`
Good, clean shell. These fixes keep it honest:
- [ ] **`TopBar.tsx`: remove the hard-coded green "System Online".** Status must come from `GET /api/health`. Until it does, show *Unknown* in grey. The blueprint forbids showing confidence the system doesn't have.
- [ ] **`page.tsx`:** the static `StateCard` "running successfully" message has the same problem. Drive it from data or remove it.
- [ ] **`Sidebar.tsx`:** use `next/link` instead of `<a>`, and add placeholder pages for `/research`, `/search`, `/evidence`, `/experiments`, `/analysis`, `/history` and `/status`. Today all 7 links lead to 404s.
- [ ] Replace the `create-next-app` boilerplate in `apps/web/README.md` with how to run it, the env vars, and the folder conventions.
- [ ] Add an `npm run typecheck` script; lint and typecheck run in CI (with the Lead).

### Day 2: API client and status view (§16)
- [ ] **Typed API client** in `apps/web/lib/api/`:
  - Generated from the Lead's `/api/openapi.json` (e.g. `openapi-typescript`).
  - Until the API exists, use a mock that follows the agreed `/api/health` shape.
  - Every request carries and logs the `request_id`.
- [ ] **`/status` page:**
  - API, Postgres, Redis and object storage health.
  - Corpus/knowledge version, model provider, build/release ID.
  - Explicit *loading*, *error* and *unknown* states.
- [ ] Dashboard metric cards (Documents / Experiments / Analyses) read real counts once the Lead's seed lands. Until then they show "—" (already correct).

**Done when:** the status page reflects real `/api/health` responses, including a dependency-down case, no route 404s, and CI runs lint and typecheck.

---

## 7. Engineer 5 (Ziad): AI evaluation / research intelligence

### Day 1 redo (from the Day 1 review; files in `tests/eval/day1_ziad/`)
The current work rates **2.5 / 10**. The code is tidy and the test-design ideas are good: "no answer" cases, a false-premise case, questions combining two sources, and image/video questions. But:
- the 20 cases are about a fictional "movie fire ship", not our corpus
- the scores are **typed into the test file**, so "passed baseline" isn't a measurement
- the format lacks the §18 fields

Fixes:
- [ ] **Rewrite the gold set from real sources:** BASS-II/FLEX/SPICE tables and documents plus the 3 NTRS papers, in the §18 format.
  - Fields: `id`, `split`, `task`, `query`, `filters`, `expected_evidence` (source_id + file + locator), `expected_claims`, `answerable`, `rubric_version`, `source_scope`.
  - Start with 30 cases and grow to 50–100. Split by **document** across dev/validation/holdout.
  - Include "no answer" cases from our data: "What flame temperature did BASS-II test B1 reach?" (the table has none), "Does DSI contain flame images?" (no), "Show 1 g SPICE flame images" (those files are calibration sheets).
- [ ] **Separate gold from runs.** `datasets/evaluation/rag_gold.jsonl` holds expectations only. `tests/eval/runs/<run_id>.jsonl` holds system outputs plus a run manifest: commit, corpus version, model, prompt and scorer version.
- [ ] **Compute metrics, don't enter them:**
  - Recall@k / MRR against expected evidence
  - citation locator validity
  - abstention accuracy
  - faithfulness via a written 1–5 rubric (`docs/evaluation/rubric_v1.md`)
- [ ] **Gates per case and per slice, not just averages.** One invented answer on a "no answer" case fails the run, and the script exits non-zero.
  - Fix the threshold mismatch: faithfulness needs 4.5 in `evaluator`, but `rag_evaluator` only flags scores below 4.
- [ ] Convert the notebooks (archived in `tests/eval/day1_ziad/`) into `tests/eval/` modules with a JSON Schema for cases and pytest tests.

### Day 2: source-quality and provenance checklist (§16)
- [ ] **`docs/evaluation/provenance_checklist.md`**, covering each source:
  - licence confirmed, DOI present, access path verified
  - every mirrored file has a sha256 and its size matches the inventory, and originals are untouched
  - domain tag set
  - parser version recorded, page locators resolvable
  - known-unavailable files listed
- [ ] **Automated check** `tests/eval/test_provenance.py`:
  - `files.jsonl` ↔ `sha256.txt` ↔ inventory agree
  - every registry row validates
  - no derived files under `raw/`
  - every `files.jsonl` source_id exists in the registry
- [ ] **Run it on today's data and file the findings.** Known so far: 3 NASA-side unavailable PSI files, DSI DOI missing, NTRS PDFs unregistered, and derived frames for DSI `S1 activity 4` (in `datasets/derived/DSI/`) that have no frame records with `parent_file_id` yet.

**Done when:** the gold set has ≥ 30 real-domain cases that pass schema validation, `pytest tests/eval` runs in CI, and the provenance report lists concrete pass/fail per source.

---

## 8. Day 2 hand-offs (who needs what from whom)

| From → To | What | When |
|---|---|---|
| Lead → Engineer 4 | `/api/health` shape + `/api/openapi.json` | Midday |
| Engineer 2 ↔ Engineer 1 ↔ Lead | Evidence/locator field names (DTOs ↔ DB columns ↔ document records) | Morning sync |
| Engineer 2 → Lead | Loaders for `source`, `file_record`, `document`, `experiment_condition` | End of day |
| Engineer 3 → Engineers 2, 5 | Image intake spec for review | Afternoon |
| Engineer 2 → Engineer 5 | Document records + experiment conditions to build gold cases from | Afternoon |
| Engineer 5 → everyone | Provenance check results | End of day |

**End-of-day demo (rule from §16):** a working artefact plus a test or evidence for each item, not a verbal status.
