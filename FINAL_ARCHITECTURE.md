# Final architecture: Flame in Freefall

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current (as merged on `main` at `f191bad`) | 1.1.2 | 2026-11-12 | T7, ADR-006–009 | whole repository |

Detailed, older material: [docs/architecture/overview.md](docs/architecture/overview.md) (Phase 2, Part A), [ADRs](docs/architecture/adr/README.md), [hybrid AI](docs/hybrid-ai/PHASE_2_HYBRID_AI_ARCHITECTURE.md). This file describes the system that answers the Space Apps challenge.

## 1. System at a glance

```
NASA PSI (CC0)   ┐  datasets/raw/psi_api/*/Experimental table/*.csv  (4 tables, 876 rows)
                 │  datasets/raw/psi_api/*/metadata/*.zip            (ISA-Tab: objective, hypothesis…)
NASA NTRS        ┤  docs/research/*.pdf                              (24 public-use reports)
BASS-II / SPICE  ┘  datasets/samples/cv/                             (flight video, ISS photos)
        │  seed → ingest (table parser, ISA-Tab parser, PDF + OCR fallback) → vector_index build
        ▼
PostgreSQL + pgvector ── experiment, experiment_condition, evidence, document, document_chunk, chunk_embedding,
        │                 knowledge_entity / knowledge_relation (graph, rebuilt at every ingest), video_checkpoint_frame
        │
FastAPI apps/api (contract docs/api/openapi.json 0.7.0, per-client keys with read/write/admin scopes, rate limits)
  ├─ Fire safety  /api/investigations · /api/investigations/{id} · /api/insights · /api/insights/flex-outcome
  │                └─ ai/fire_safety: canonical features, scenarios, ranking, insights, FLEX model (numpy)
  ├─ Research     /api/search (SQL candidates → ai/rag search stack: rewrite, RRF, cross-encoder reranking of the top 10) · /api/chat (grounded, citation-filtered) · documents · experiments · evidence
  ├─ Graph        /api/graph/entities · /api/graph/entities/{id} (recursive-CTE neighbourhood, every edge cited)
  └─ Analysis     /api/analyses (image + video) → S3 original → RQ worker → cv/ (OpenCV) → measurements + evidence;
                   video checkpoints per segment, resume after recovery; POST /api/analyses/{id}/cancel
        │
Next.js apps/web ── server-side read-only proxy (app/api/[...path]) holding the read key
  /  dashboard · /investigations/[id] · /explorer · /experiments · /chat · /search · /analysis · /history · /evidence · /status
        │
AURA (optional, separate system) ── compiles the read-only GET operations into 16 agent tools (Link 2)
Local models (optional) ── Ollama / llama.cpp / vLLM behind ai/routing (modes: cloud_preferred · local_first · offline_only)
```

## 2. Service responsibilities

| Service | Responsibility | State |
|---|---|---|
| `api` (uvicorn) | REST contract, auth, rate limits, search, chat orchestration, fire-safety analytics, analysis intake | stateless |
| `worker` (RQ) | image and video CV jobs; video checkpoints in PostgreSQL; stuck-job recovery at start | stateless (checkpoints are in PostgreSQL) |
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

**Knowledge graph (ADR-007).** At the end of every ingest, `knowledge_graph.build_graph` turns the tables into entities (investigations, experiments, fuels, condition variables, phenomena, ISA-Tab documents) and `table_parse` edges, each citing the cell it was read from: 951 entities and 10,683 edges (four reviewed spelling variants resolve to one material each). Rebuilds are idempotent and keep human review and merges.

**NASA summaries.** `ingest.parse_isatab` turns the metadata zip into sections (Objective, Hypothesis, Approach, Research impacts, Hardware, Publications). Each section is stored as a citable, searchable document chunk, verbatim.

**Outcome model.**
1. `train_flex_outcome.py` (scikit-learn, offline) trains on the committed FLEX table and exports `artifacts/flex_outcome_model.json` plus its evaluation report.
2. `model.py` runs the artefact with numpy, checks the applicability domain, and returns the nearest real flight tests with their evidence IDs.
3. `test_api_features_match_training_features_for_every_flex_test` proves the API rebuilds identical features from the database.

**Chat (RAG).**
1. Retrieval: the `ai/rag` search stack (ADR-006) over 315 chunks, for the question plus up to 5 key terms. The query rewrite is kept next to the original; the cross-encoder reranker (fastembed ONNX) reorders the first 10 results by default.
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

- **REST contract.** `docs/api/openapi.json` 0.7.0 is hand-authored (ADR-010). Route ↔ contract parity and schema validation of live responses are tested. Changelog: `docs/api/CHANGELOG.md`.
- **AURA (Link 2).** AURA's OpenAPI discovery compiles the GET operations into tools. At the pinned AURA revision `d696fad`, 16 tools are accepted, including `api_list_investigations`, `api_get_investigation`, `api_list_insights`, `api_estimate_flex_outcome` and the two knowledge-graph reads. Chat, cancel and admin operations carry `x-aura-exclude` (10 operations).
- **Model routing.** `ai/routing` routes chat, embeddings and vision to local or cloud providers with health checks, circuit breakers and audited mode switches.

## Known limitations
- Single API replica: the answer cache and the investigations cache are in-process.
- The relevance formula's weights are a documented design choice, not fitted to outcomes ([ADR-011](docs/architecture/adr/ADR-011-scenario-relevance-ranking.md); the ranking order is unchanged under ±50 % weight changes).
- The reranker is on by default: +0.08 hit@1 on an unreviewed 26-question set, at about 0.7 s per search on CPU, and its model downloads on first use ([retrieval-2026-11-12.md](docs/evaluation/reports/retrieval-2026-11-12.md)).
- The knowledge graph holds only what the tables record (no NLP extraction); Graph RAG in chat is not built. The web app's Knowledge page is not wired to `/api/graph/*` yet and still says the graph is unavailable.

## Changelog
- 1.0.0 (2026-11-07): first version.
- 1.0.1 (2026-11-07): ADR-006 is Accepted and only partly implemented (ADR index 1.3.0).
- 1.1.2 (2026-11-12): states the merged revision; reranking in the system diagram.
- 1.1.1 (2026-11-12): reranker on by default; reviewed graph aliases.
- 1.1.0 (2026-11-12): ADR-006 to 009 built (PR #29): contract 0.6.0, admin scope, video checkpoints and cancel, the ai/rag search stack, the knowledge graph.
