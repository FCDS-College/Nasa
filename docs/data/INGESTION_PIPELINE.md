# E2-2: Ingestion pipeline specification

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Anas (E2) | In review (peer sign-off: Eman E1) | 1.1.0 | 2026-11-14 | M9, B2, D6, 2H Task 7 | `apps/api/flame_api/seed.py`, `ingest.py`, `vector_index.py`, `knowledge/ingestion/*` |

## 1. Stages (raw → parsed → normalized → indexed)

| Stage | What happens | Module / function | Output |
|---|---|---|---|
| Acquire (connected only) | Mirror originals; record sha256 and provenance | `knowledge/ingestion/psi_download.py`, `record_provenance.py`; NTRS PDFs committed by hand | `datasets/raw/…` (git-ignored), `docs/research/*.pdf`, `files.jsonl`, `checksums/sha256.txt` |
| Register | Load the registry, file manifest, derived image assets and model manifest | `seed.seed_sources`, `seed_files`, `seed_image_assets`, `seed_models` | `source`, `file_record`, `image_asset`, `model` |
| Verify | Recompute sha256 against `file_record.sha256` | `ingest._sha256` in `ingest_file` | mismatch → quarantine |
| Parse | One adapter per format (§2) | `ingest._create_document`, `_create_text_document`, `_create_table_experiments` | `document`, `document_chunk`, `evidence`, `experiment`, `experiment_condition` |
| Normalize | Units to SI next to the originals; reported vs derived | `ingest.parse_cell`, `convert_to_si` | `value_si`, `unit_si` |
| Record | One run row per (file, transformation, input hash) | `ingest._record_run` | `ingestion_run` |
| Publish | `corpus-<hash>` knowledge version | `ingest._publish_corpus_version` → `knowledge_version.publish` | `knowledge_publication`, Redis event |
| Index | Embed chunks without a current-model vector | `vector_index.build_index` (router `embed.documents`) | `chunk_embedding`, `vector_index_manifest`, new knowledge version |

## 2. Parser adapters

| Adapter | Version | Triggers on | Output unit | Notes |
|---|---|---|---|---|
| PDF | `pymupdf-pages-0.5.0` (OCR render capped at 6,600 px, 300 s per page) | `.pdf` | one chunk per page with ≥ 12 chars of text | NTRS sources take the title and report number from the registry row |
| OCR fallback | engine `tesseract-<version>`, 300 dpi | a PDF page with < 12 chars of native text | the page's OCR text, `extraction_method = ocr`, `extraction_confidence` = mean word confidence / 100 | Needs `apps/api[ocr]` and the `tesseract` binary. Both are installed in the API image and in CI, where `test_real_tesseract_reads_a_scanned_page` OCRs a real image-only page with no mocks. A page with mean confidence < 60 is flagged: evidence `payload.low_confidence = true` and `document.payload.ocr.low_confidence_pages`. If OCR is unavailable, `document.payload.ocr.status = "unavailable"` and the page stays in `pages_without_text`. |
| HTML | `html-sections-0.1.0` | `.html`, `.htm` | one chunk per section, split at `h1`–`h3` | `script`, `style`, `noscript`, `template` and `head` are dropped; UTF-8 only |
| JSON | `json-paths-0.1.0` | `.json` | one chunk per top-level key (or array item), as `path: value` lines | stdlib parser; ≤ 20 000 chars per section |
| PSI tables | `psi-tables-0.2.0` | `.csv` whose path contains "experimental table" | experiments + one evidence row per condition cell | duplicate test IDs counted (`spice_duplicates`) |

`text_layer` describes the PDF itself: `full`, `partial` or `none`. OCR doesn't change it.

## 3. Quarantine

| Reason | Detected when |
|---|---|
| `checksum_mismatch` | the bytes on disk don't match the registered sha256 |
| `unreadable_pdf` | PyMuPDF can't open it |
| `encrypted_pdf` | the PDF needs a password |
| `empty_pdf` | 0 pages |
| `html_not_utf8` | HTML isn't UTF-8 |
| `invalid_json` | JSON doesn't parse |
| `no_text_in_html` / `no_text_in_json` | the adapter extracted nothing |

What quarantine does:
- sets `file_record.status = "quarantined"` and records `quarantine_reason`;
- writes an `ingestion_run` row with `transformation_id = "quarantine"`;
- leaves nothing parsed (the parse runs inside a savepoint that is rolled back);
- skips the file on every later run until an administrator resets the status ([E2-8 §3](ADMIN_DATA_OPERATIONS.md)).

A file that is simply **not on disk** is *skipped*, not quarantined. Git-ignored mirrors are legitimately absent on CI and on fresh machines.

Any **other parser exception** (a `UnicodeDecodeError` in a table, a `csv.Error`, a PyMuPDF page error, a parser bug) makes the file *failed*, not quarantined, because the fault may be the parser's rather than the file's. Its savepoint is rolled back, the error is logged as `ingest_file_failed` with its traceback, no `ingestion_run` row is written and the run goes on with the next file, so the next run retries it. The totals count it under `failed` and `python -m flame_api.ingest` exits with status 1. Before the KB audit (2026-11-13) such an error rolled back the whole run. Database errors still end the run: they say nothing about the file.

## 4. Idempotency and retry

- **IDs.** All IDs are `stable_ulid` of content keys ([L-5 §1](../architecture/index-sync-contract.md)), and every write is a `merge`. Running ingest twice creates no duplicates. Tested by `test_ingestion_adapters.py::test_reingesting_creates_no_duplicates`, and CI runs `ingest` twice against PostgreSQL.
- **Run rows.** `ingestion_run` is unique on `(file_id, transformation_id, input_sha256)`. A rerun updates the same row.
- **Retry.** Rerunning `python -m flame_api.ingest` retries every non-quarantined file. A crash mid-run loses nothing already committed: the run commits once at the end, and the stable IDs make the rerun converge.
- **Parser upgrade.** IDs don't include the parser version, so upgrading a parser updates the rows in place. The stored `parser_version` / `transformation_id` say which parser produced them.

## 5. Replay and run manifest

`ingestion_run` fields: `run_id`, `source_id`, `file_id`, `transformation_id`, `input_sha256`, `started_at`, `finished_at`, `counts`. To reproduce a corpus version, check out the commit (parser versions) and restore the same files (sha256 per `files.jsonl`), then run `seed` and `ingest`. The resulting `corpus-<hash>` is a hash of the sorted `(file_id, input_sha256, transformation_id)` triples, so identical inputs give the identical version.

## 6. Running it

```bash
# Compose (runs at API start-up)
docker compose -f infrastructure/compose.yaml exec api python -m flame_api.ingest
# Local (L-8 §1)
cd apps/api && python -m flame_api.seed && python -m flame_api.ingest && python -m flame_api.vector_index build
```

Sample output on 2026-10-11, with the committed corpus only (no `datasets/raw/` mirror):

```text
{"sources": 11, "files": 124, "files_skipped_unknown_source": 0, "image_assets": 182, "models": 7}
{"pdf_documents": 3, "pdf_pages": 39, "pdf_chunks": 37, "ocr_pages": 0, "ocr_low_confidence": 0, "text_documents": 0,
 "text_chunks": 0, "experiments": 0, "table_evidence": 0, "spice_duplicates": 0, "skipped": 100, "quarantined": 0}
{'embedded': 37, 'total': 37, 'knowledge_version': 'bge-small-en-v1.5-37-20261011'}
```

The 2 pages without chunks are pp. 14–15 of `20080034883.pdf`, which have no text layer; OCR was not installed. With the PSI mirror present, the table stage adds 840 experiments (the counts are asserted by `test_mirrored_psi_tables_are_ingested_with_provenance_and_stable_ids`).

## 7. Offline behaviour and resumable checkpoints (2H)

| Stage | Offline | Resumable |
|---|---|---|
| Acquire | no (needs psi.nasa.gov / S3 / NTRS) | `psi_download.py` skips files already present |
| Register, Verify, Parse, Record, Publish | yes, fully local | yes (stable IDs, merge) |
| OCR | yes (local Tesseract) | yes |
| Index | yes, if the embedding cache is prepared (`FLAME_EMBEDDING_OFFLINE=true` never downloads) | yes: embeds only chunks missing a current-model vector |

## Known limitations
- Ingestion is a CLI step (start-up or manual). There's no admin endpoint or queue job yet (B2).
- The commit happens once per run. A run interrupted halfway leaves nothing for its parsed files, but a rerun repeats the work.
- OCR quality is not evaluated yet.

## Changelog
- 1.1.0 (2026-11-14): an unexpected parser exception fails one file (`failed`, retried next run, exit status 1) instead of rolling back the whole run (KB audit 2026-11-13).
- 1.0.0 (2026-10-12): first specification (OCR, HTML/JSON, quarantine, run records, corpus version).
