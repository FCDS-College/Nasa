# Final architecture: Flame in Freefall

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current (as built on `anas/vibrant-sagan-fsnckf`) | 1.0.0 | 2026-11-07 | T7 | whole repository |

Detailed, older material: [docs/architecture/overview.md](docs/architecture/overview.md) (Phase 2, Part A), [ADRs](docs/architecture/adr/README.md), [hybrid AI](docs/hybrid-ai/PHASE_2_HYBRID_AI_ARCHITECTURE.md). This file describes the system that answers the Space Apps challenge.

## 1. System at a glance

```
NASA PSI (CC0)   ┐  datasets/raw/psi_api/*/Experimental table/*.csv  (4 tables, 876 rows)
                 │  datasets/raw/psi_api/*/metadata/*.zip            (ISA-Tab: objective, hypothesis…)
NASA NTRS        ┤  docs/research/*.pdf                              (24 public-use reports)
BASS-II / SPICE  ┘  datasets/samples/cv/                             (flight video, ISS photos)
        │  seed → ingest (table parser, ISA-Tab parser, PDF + OCR fallback) → vector_index build
        ▼
PostgreSQL + pgvector ── experiment, experiment_condition, evidence, document, document_chunk, chunk_embedding
        │
FastAPI apps/api (contract docs/api/openapi.json 0.5.0, per-client keys, rate limits)
  ├─ Fire safety  /api/investigations · /api/investigations/{id} · /api/insights · /api/insights/flex-outcome
  │                └─ ai/fire_safety: canonical features, scenarios, ranking, insights, FLEX model (numpy)
  ├─ Research     /api/search (FTS + pgvector, RRF) · /api/chat (grounded, citation-filtered) · documents · experiments · evidence
  └─ Analysis     /api/analyses (image + video) → S3 original → RQ worker → cv/ (OpenCV) → measurements + evidence
        │
Next.js apps/web ── server-side read-only proxy (app/api/[...path]) holding the read key
  /  dashboard · /investigations/[id] · /explorer · /experiments · /chat · /search · /analysis · /history · /evidence · /status
        │
AURA (optional, separate system) ── compiles the read-only GET operations into 14 agent tools (Link 2)
Local models (optional) ── Ollama / llama.cpp / vLLM behind ai/routing (modes: cloud_preferred · local_first · offline_only)
```

## 2. Service responsibilities

| Service | Responsibility | State |
|---|---|---|
| `api` (uvicorn) | REST contract, auth, rate limits, search, chat orchestration, fire-safety analytics, analysis intake | stateless |
| `worker` (RQ) | image and video CV jobs; stuck-job recovery at start | stateless |
| PostgreSQL + pgvector | sources, files, evidence, experiments, documents, chunks, embeddings, analyses, audit, API clients | durable |
| Redis | job queue, rate-limit buckets, knowledge-version events | ephemeral |
| S3 / MinIO | uploaded originals and CV artifacts | durable |
| `web` (Next.js) | dashboard UI; same-origin proxy (GET allowlist + chat POST; never a write key) | stateless |
| Ollama (optional) | local LLM for chat answers and interpretation | model cache |

## 3. Key data flows

**Flight data → dashboard.**
1. `ingest._create_table_experiments` turns each table row into an `experiment` with one `experiment_condition` and one `evidence` row per published cell. Values are kept as published, with SI conversion where the unit is known; IDs are stable.
2. `investigations._load` reads them, cached per knowledge version.
3. `ai.fire_safety.investigations.canonical` maps each investigation's columns to comparable variables: O₂, pressure, flow, material, end state, duration. Unrecorded variables become `None`, never 0.
4. `envelope`, `relevance` and `insights` compute everything the dashboard shows, carrying the evidence IDs of the rows used.

**NASA summaries.** `ingest.parse_isatab` turns the metadata zip into sections (Objective, Hypothesis, Approach, Research impacts, Hardware, Publications). Each section is stored as a citable, searchable document chunk, verbatim.

**Outcome model.**
1. `train_flex_outcome.py` (scikit-learn, offline) trains on the committed FLEX table and exports `artifacts/flex_outcome_model.json` plus its evaluation report.
2. `model.py` runs the artefact with numpy, checks the applicability domain, and returns the nearest real flight tests with their evidence IDs.
3. `test_api_features_match_training_features_for_every_flex_test` proves the API rebuilds identical features from the database.

**Chat (RAG).**
1. Retrieval: hybrid search over 315 chunks, for the question plus up to 5 key terms.
2. Generation: the router (`chat.answer`) sends the passages on a data channel. Flame validates the output and drops citations outside the retrieved set, and the answer cache stores clean answers.
3. Fallbacks:
   - a model that fails gives an evidence-only answer (`generation_unavailable`);
   - with no model configured, the API returns 503 `CHAT_UNAVAILABLE`, and the UI then shows the retrieved evidence, labelled as not generated.

**Video.**
1. `POST /api/analyses` with `video` is sniffed, spooled under a size cap, probed and queued.
2. The worker samples frames in time order, runs the CV pipeline, and summarizes the temporal statistics (persistence, area change; flicker only above the Nyquist limit).
3. The results are stored as `video_measurement` evidence.

## 4. Scientific rules enforced in code

| Rule | Where |
|---|---|
| No temperature from RGB; pixel values are `measured`, scaled values `estimated` | `cv/`, contract `MeasuredValue` |
| Model outputs are `estimated`; insights are `measured_statistic` / `model_estimate` / `coverage_gap` | `investigations.py`, contract `InsightKind` |
| Never extrapolate the outcome model | `model.FlexOutcomeModel.applicability` |
| Unrecorded ≠ zero; impossible values (0 mmHg) become missing | `canonical`, `flex.features_from_values` |
| Outcome columns never used as features | `flex.FEATURES` |
| Every number on the dashboard traces to a NASA source row | evidence IDs on every insight and test reference |
| Garbled PDF text is never indexed | `ingest.text_layer_is_garbled` → OCR fallback |

## 5. Contracts and integrations

- **REST contract.** `docs/api/openapi.json` 0.5.0 is hand-authored (ADR-010). Route ↔ contract parity and schema validation of live responses are tested. Changelog: `docs/api/CHANGELOG.md`.
- **AURA (Link 2).** AURA's OpenAPI discovery compiles the GET operations into tools. At the pinned AURA revision `d696fad`, 14 tools are accepted, including `api_list_investigations`, `api_get_investigation`, `api_list_insights` and `api_estimate_flex_outcome`. Write, chat and admin operations carry `x-aura-exclude`.
- **Model routing.** `ai/routing` routes chat, embeddings and vision to local or cloud providers with health checks, circuit breakers and audited mode switches.

## Known limitations
- Single API replica: the answer cache and the investigations cache are in-process.
- The relevance formula's weights are a documented design choice, not fitted to outcomes.
- Two retrieval stacks remain (`ai/rag` vs the API's search; ADR-006 Proposed).

## Changelog
- 1.0.0 (2026-11-07): first version.
