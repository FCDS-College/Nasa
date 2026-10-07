# Flame in Freefall

An evidence-first scientific intelligence platform for **combustion and flame behaviour in microgravity** (NASA Space Apps Challenge). It combines a curated NASA/NIST knowledge base, cited RAG answers, traceable computer-vision analysis of flame images, and a web dashboard. Every consequential result must trace back to its original source file.

The full engineering blueprint is in [`docs/plan/Nasa - MVP Plan.pdf`](docs/plan/Nasa%20-%20MVP%20Plan.pdf).

## Repository layout

```
.
├── docs/
│   ├── plan/            MVP engineering blueprint (PDF) and daily task lists
│   ├── api/             openapi.json (OpenAPI 3.1, not yet implemented), API_SCHEMAS, FRONTEND_API_CONTRACT, service contracts
│   ├── ai/              RAG/CAG/MAG policies, prompts, context builder, citations, retrieval evaluation
│   ├── architecture/    System overview (ADRs go in adr/)
│   ├── integration/     AURA integration status and requirements
│   ├── data/            Data dictionary, acquisition spec, source candidates, dataset reports
│   ├── research/        Reference NTRS papers (PDF)
│   ├── reviews/         Daily engineering reviews
│   ├── presentations/   Project slide decks
│   └── tools/           Doc generators (render_api_schemas.py)
├── datasets/
│   ├── registry/        source_registry.csv + JSON schema (one row per source)
│   ├── manifests/       Bucket/API file inventories and download selections
│   ├── checksums/       sha256.txt for every mirrored file
│   ├── metadata/        files.jsonl: per-file provenance records
│   ├── evaluation/      Versioned gold sets (rag_gold.jsonl)
│   ├── samples/         Small committed CV sample frames
│   ├── processed/       Committed CV outputs (processed frames, masks)
│   └── raw/, derived/   Mirrored originals and extractions (git-ignored)
├── knowledge/
│   └── ingestion/       Download + provenance scripts (NASA PSI)
├── ai/
│   └── rag/             Ingestion, embeddings, retrieval, reranking, context, citations, evaluation
├── cv/                  Flame-image analysis: contracts/ and notebooks/
├── apps/
│   ├── api/             FastAPI service, Alembic migrations and API tests
│   └── web/             Next.js dashboard
├── infrastructure/      Docker Compose and Railway service configuration
└── tests/
    ├── unit/            pytest unit tests (python -m pytest)
    ├── integration/     Cross-system checks (AURA blueprint dry run)
    └── eval/            Evaluation notebooks and test cases (day1_ziad, day2_ziad)
```

Each top-level folder has a README giving its owner and rules.

## Data quick start

Raw data is **not** stored in Git. To rebuild the local mirror:

```bash
# DSI sample (public S3 bucket, anonymous)
aws s3 cp --no-sign-request --recursive "s3://nasa-psi/DSI/" datasets/raw/nasa_psi/DSI/ --exclude "*" --include "DECLIC-DSI DoD.docx" --include "SRD/*" --include "Taskbook Downloads/*" --include "Data/*Solidification Plan.xlsx" --include "Data/S1 activity 4.zip"
python knowledge/ingestion/record_provenance.py DSI FF-PSI-DSI

# Combustion pilot set: BASS-II, FLEX, SAFFIRE-I, SPICE (psi.nasa.gov API, anonymous)
python knowledge/ingestion/psi_download.py datasets/manifests/psi_pilot_selection.csv
python knowledge/ingestion/record_provenance.py PSI-25 FF-PSI-25 psi_api

# Verify integrity
cd datasets && sha256sum -c checksums/sha256.txt
```

Run `record_provenance.py` for each PSI ID you downloaded (PSI-25, PSI-69, PSI-98, PSI-107).

What each dataset contains and how to use it is covered in [`docs/data/DSI_DATASET_REPORT.md`](docs/data/DSI_DATASET_REPORT.md) and [`docs/data/CV_IMAGE_SOURCES.md`](docs/data/CV_IMAGE_SOURCES.md).

## API contract

The dashboard's API is defined contract-first in [`docs/api/openapi.json`](docs/api/openapi.json), documented for the frontend in [`docs/api/FRONTEND_API_CONTRACT.md`](docs/api/FRONTEND_API_CONTRACT.md), with every response schema listed field by field in [`docs/api/API_SCHEMAS.md`](docs/api/API_SCHEMAS.md) (regenerate with `python docs/tools/render_api_schemas.py`). The FastAPI implementation is in `apps/api`; the OpenAPI contract is served at `/api/openapi.json`. AURA Track AP Link 2 compatibility is checked by [`tests/integration/aura_blueprint_dryrun.py`](tests/integration/aura_blueprint_dryrun.py) and its pinned-revision CI workflow. The current integration status and requirements are in [`docs/integration/AURA_INTEGRATION_STATUS.md`](docs/integration/AURA_INTEGRATION_STATUS.md) and [`docs/integration/AURA_INTEGRATION_REQUIREMENTS.md`](docs/integration/AURA_INTEGRATION_REQUIREMENTS.md). They build on the measured dataset picture in [`docs/data/COMBUSTION_DATASET_ANALYSIS.md`](docs/data/COMBUSTION_DATASET_ANALYSIS.md).

## Engineering rules (from the blueprint)

Contract first · evidence over claims · provenance is mandatory · version important artefacts · preserve uncertainty · never claim implementation without evidence.
