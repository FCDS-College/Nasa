# 🔥 Flame in Freefall

**NASA Space Apps 2026: fire-safety insights from NASA microgravity combustion data.**

Pick a spacecraft cabin atmosphere (ISS air, pre-EVA, Orion, a lunar lander, or your own). Flame in Freefall then:
- **ranks** NASA's flight investigations by how directly their data covers it;
- **summarizes** each one in NASA's own words;
- **explains** what the flight tests measured there, every number linked to its NASA source cell;
- **estimates** droplet-flame outcomes with a validated model that refuses to extrapolate;
- says plainly what the data **cannot** tell you: a coverage verdict comes before any ranking, and an atmosphere nobody flew gets no estimate. Try the historical preset **Apollo 1: pure-O₂ ground test (1967)**, which the system refuses and then points to the data-covered Orion atmosphere.

| Start here | |
|---|---|
| What it is and why | [FINAL_CHALLENGE_PRESENTATION.md](FINAL_CHALLENGE_PRESENTATION.md) |
| 3-minute pitch (deck + script, English; Arabic rehearsal script) | [flame-in-freefall-3min-pitch.pptx](docs/presentations/flame-in-freefall-3min-pitch.pptx) · [script](docs/presentations/PITCH_SCRIPT_3MIN.md) · [النص العربي](docs/presentations/PITCH_SCRIPT_3MIN.ar.md) |
| 7-slide product demo (live deck, PDF) | [demo deck](docs/presentations/demo-deck/README.md) · [PDF](docs/presentations/demo-deck/flame-in-freefall-demo.pdf) |
| The Apollo 1 scenario and how it generalises | [APOLLO1_SCENARIO_ANALYSIS.md](docs/reports/APOLLO1_SCENARIO_ANALYSIS.md) · [ADR-013](docs/architecture/adr/ADR-013-historical-scenarios-coverage-verdict.md) |
| Business plan (commercial space) | [docs/business/BUSINESS_PLAN.md](docs/business/BUSINESS_PLAN.md) |
| Run the demo | [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md) |
| What works, what doesn't | [FINAL_PROJECT_STATUS.md](FINAL_PROJECT_STATUS.md) |
| How it is built | [FINAL_ARCHITECTURE.md](FINAL_ARCHITECTURE.md) |
| What was tested | [FINAL_TEST_REPORT.md](FINAL_TEST_REPORT.md) |
| Model card | [docs/evaluation/reports/flex-outcome-model.md](docs/evaluation/reports/flex-outcome-model.md) |
| API contract | [docs/api/openapi.json](docs/api/openapi.json) (0.7.0) · [changelog](docs/api/CHANGELOG.md) |
| AURA integration | [docs/integration/README.md](docs/integration/README.md) |
| All documentation | [docs/README.md](docs/README.md) |

## Data (all committed, all public)

- **1950 flight tests** from 19 NASA PSI combustion investigations, CC0:
  - gas flames: SPICE (gas co-flow), 435; ACME CFI-G (normal and inverse flames), 333; ACME Flame Design, 327; ACME-CLD, 32; ACME E-FIELD, 31; ACME BRE, 18; ACME s-Flame, 18; SLICE, 12;
  - droplets: FLEX, 274; CFI, 79; FLEX-2, 8;
  - solids: BASS-II, 129; BASS, 122; SAFFIRE-II, 9; SAFFIRE-I, 2; SAFFIRE-III, 2;
  - smoke: SAME-R, 109; SAME, 8; DAFT, 2.
- **NASA ISA-Tab metadata** for these investigations (24 documents).
- **27 NASA NTRS reports** with `PUBLIC_USE_PERMITTED` status, including the Apollo 204 Review Board report.
- **Flight media:** a BASS-II flight video and SPICE ISS photographs, for computer vision.

Provenance and SHA-256 for every file are in `datasets/metadata/files.jsonl` and `datasets/checksums/sha256.txt`. The large raw mirrors (~6 GB of video and frames) are optional:

```bash
python knowledge/ingestion/install_datasets.py --only tables   # re-fetch the committed tables and metadata
```

```bash
python knowledge/ingestion/install_datasets.py --verify-only   # check every installed file against its hash
```

## Quick start (developers)

```bash
pip install -e "apps/api[dev,cv,ingestion,ocr,vector]" -r ai/requirements.txt
```

```bash
python -m pytest
```

```bash
ruff check .
```

```bash
cd apps/web && npm ci && npm run lint && npm run typecheck && npm run build
```

```bash
python -m ai.fire_safety.train_flex_outcome --check   # the committed model reproduces from the committed data
```

The full stack (API, worker, PostgreSQL + pgvector, Redis, S3, web, optional Ollama) is described in [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md).

## Repository layout

```
apps/api        FastAPI service, ingestion, RQ worker (contract docs/api/openapi.json)
apps/web        Next.js dashboard (server-side proxy to the API: reads, chat, passcode-gated uploads)
ai/fire_safety  investigations ranking, coverage verdict, insights, FLEX outcome model (+ artefact and evaluation),
                historical scenarios as cited data files (historical/)
ai/routing      provider-neutral model router (local / cloud, offline modes)
ai/rag          retrieval library and the retrieval benchmark
cv/             flame image and video analysis (OpenCV)
datasets/       registry, provenance, committed PSI tables, CV samples, evaluation gold sets
docs/           architecture, ADRs, API, data, evaluation reports, operations
infrastructure/ docker compose, backups, demo data script
tests/          repository-level tests (the API tests live in apps/api/tests)
```

## Legacy evaluation pipeline

`run_evaluation.py`, `render_report.py`, `evaluation_report.json` and `tests/eval/` are an earlier RAG-evaluation prototype. **Its numbers score a mock system and must not be quoted** ([docs/reviews/SYSTEM_STATUS_AUDIT.md](docs/reviews/SYSTEM_STATUS_AUDIT.md) §2). Measured results for Flame are in `docs/evaluation/reports/` (2026-11-07).

## License

NASA data: CC0 (PSI) and public use permitted (NTRS), as recorded per source in `datasets/registry/source_registry.csv`. The project code is internal to the team.
