# 🔥 Flame in Freefall

**NASA Space Apps 2026: fire-safety insights from NASA microgravity combustion data.**

Pick a spacecraft cabin atmosphere (ISS air, pre-EVA, Orion, a lunar lander, or your own). Flame in Freefall then:
- **ranks** NASA's flight investigations by how directly their data covers it;
- **summarizes** each one in NASA's own words;
- **explains** what the flight tests measured there, every number linked to its NASA source cell;
- **estimates** droplet-flame outcomes with a validated model that refuses to extrapolate;
- says plainly what the data **cannot** tell you.

| Start here | |
|---|---|
| What it is and why | [FINAL_CHALLENGE_PRESENTATION.md](FINAL_CHALLENGE_PRESENTATION.md) |
| Run the demo | [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md) |
| What works, what doesn't | [FINAL_PROJECT_STATUS.md](FINAL_PROJECT_STATUS.md) |
| How it is built | [FINAL_ARCHITECTURE.md](FINAL_ARCHITECTURE.md) |
| What was tested | [FINAL_TEST_REPORT.md](FINAL_TEST_REPORT.md) |
| Model card | [docs/evaluation/reports/flex-outcome-model.md](docs/evaluation/reports/flex-outcome-model.md) |
| API contract | [docs/api/openapi.json](docs/api/openapi.json) (0.5.0) · [changelog](docs/api/CHANGELOG.md) |
| AURA integration | [docs/integration/README.md](docs/integration/README.md) |
| All documentation | [docs/README.md](docs/README.md) |

## Data (all committed, all public)

- **840 flight tests** from four NASA PSI investigations, CC0:
  - FLEX (droplets), 274;
  - BASS-II (solids), 129;
  - SPICE (gas co-flow), 435;
  - SAFFIRE-I (large-scale fabric), 2.
- **NASA ISA-Tab metadata** for the same four investigations.
- **24 NASA NTRS reports** with `PUBLIC_USE_PERMITTED` status.
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
apps/web        Next.js dashboard (server-side read-only proxy to the API)
ai/fire_safety  investigations ranking, insights, FLEX outcome model (+ artefact and evaluation)
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
