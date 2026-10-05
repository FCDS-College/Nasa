# Flame in Freefall

An evidence-first scientific intelligence platform for **combustion and flame behaviour in microgravity** (NASA Space Apps Challenge). It combines a curated NASA/NIST knowledge base, cited RAG answers, traceable computer-vision analysis of flame images, and a web dashboard. Every consequential result must trace back to its original source file.

The full engineering blueprint is in [`docs/plan/Nasa - MVP Plan.pdf`](docs/plan/Nasa%20-%20MVP%20Plan.pdf).

## Repository layout

```
.
├── docs/
│   ├── plan/            MVP engineering blueprint (PDF)
│   ├── data/            Data dictionary, acquisition spec, source candidates, dataset reports
│   ├── openapi.json     Frontend API contract (OpenAPI 3.1, not yet implemented) — see FRONTEND_API_CONTRACT.md
│   └── research/        Reference NTRS papers (PDF)
├── datasets/
│   ├── registry/        source_registry.csv + JSON schema (one row per source)
│   ├── manifests/       Bucket/API file inventories and download selections
│   ├── checksums/       sha256.txt for every mirrored file
│   ├── metadata/        files.jsonl: per-file provenance records
│   └── raw/             Mirrored originals (git-ignored, immutable)
├── knowledge/
│   └── ingestion/       Download + provenance scripts (NASA PSI)
├── cv/                  Flame-image analysis: AnalysisResult contract, pipeline
├── ai/                  RAG / CAG / MAG orchestration (planned)
├── apps/                web (Next.js) and api (FastAPI) (planned)
├── infrastructure/      Docker, Compose, CI/CD (planned)
└── tests/               Unit, integration and evaluation tests (planned)
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

The dashboard's API is defined contract-first in [`docs/openapi.json`](docs/openapi.json), documented for the frontend in [`docs/FRONTEND_API_CONTRACT.md`](docs/FRONTEND_API_CONTRACT.md), with every response schema listed field by field in [`docs/API_SCHEMAS.md`](docs/API_SCHEMAS.md) (regenerate with `python docs/tools/render_api_schemas.py`). No endpoint is implemented yet. The current system status and the AURA AI boundary are in [`docs/AURA_INTEGRATION_STATUS.md`](docs/AURA_INTEGRATION_STATUS.md).

## Engineering rules (from the blueprint)

Contract first · evidence over claims · provenance is mandatory · version important artefacts · preserve uncertainty · never claim implementation without evidence.
