# knowledge/

Source registry, acquisition, provenance and (Phase 2) the knowledge graph. **Owner:** Engineer 2 (Anas).

## Module map

| Path | Role | Run |
|---|---|---|
| `ingestion/psi_download.py` | Mirrors PSI investigation files from `psi.nasa.gov` (signed URLs) into `datasets/raw/psi_api/` (git-ignored). Needs internet. | `python knowledge/ingestion/psi_download.py datasets/manifests/psi_pilot_selection.csv` |
| `ingestion/record_provenance.py` | Hashes mirrored files and appends them to `datasets/metadata/files.jsonl` and `datasets/checksums/sha256.txt` | `python knowledge/ingestion/record_provenance.py PSI-25 FF-PSI-25 psi_api` |
| `ingestion/make_cv_samples.py` | Builds the CV sample set (`datasets/samples/cv/`), each sample with its raw `parent_file_id` | `python knowledge/ingestion/make_cv_samples.py` |
| `ingestion/validate_registry.py` | Validates `datasets/registry/source_registry.csv` against its schema with the shared decoder (CI gate) | `python knowledge/ingestion/validate_registry.py` |

Parsing, normalization, indexing and publication run inside the API package (`apps/api/flame_api/seed.py`, `ingest.py`, `vector_index.py`, `knowledge_version.py`). Specification: [docs/data/INGESTION_PIPELINE.md](../docs/data/INGESTION_PIPELINE.md).

## Rules
- Originals are immutable, and every file gets a SHA-256 ([PROVENANCE.md](../docs/data/PROVENANCE.md)).
- Every derived artefact keeps a `parent_file_id`.
- Restricted content is never scraped ([SOURCE_REGISTRY.md](../docs/data/SOURCE_REGISTRY.md) §4).
