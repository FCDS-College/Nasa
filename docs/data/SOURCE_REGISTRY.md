# E2-1: Source registry guide

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Anas (E2) | In review (peer sign-off: Eman E1 or Ziad E5) | 1.0.0 | 2026-10-12 | M9, B2, E2-1 | `datasets/registry/source_registry.csv`, `source_registry.schema.json`, `apps/api/flame_api/registry.py`, `knowledge/ingestion/validate_registry.py` |

The registry is the list of every source Flame knows about: one CSV row per source, validated against a JSON Schema (draft 2020-12). `python -m flame_api.seed` loads it into the `source` table. Image datasets are described per source in [CV image sources](CV_IMAGE_SOURCES.md), which Princess's annotation protocol also links.

## 1. Validation command (must pass; CI job `python`)

```bash
python knowledge/ingestion/validate_registry.py
# 11 sources checked, 0 problems (datasets/registry/source_registry.csv)   ← 2026-10-12
python knowledge/ingestion/validate_registry.py --json    # the decoded rows
```

The validator checks `uri` and `date-time` formats when `jsonschema[format-nongpl]` is installed (it is part of `apps/api[dev]`). It also flags duplicate `source_id`s.

## 2. CSV encoding rules (arrays and nulls)

The audit found that the CSV "fails schema validation". The CSV was never meant to be validated raw: it needs a decoding step that didn't exist yet. `flame_api/registry.py:decode_row` is now that step, shared by the validator and `seed.py`.

| In the CSV | Becomes | Applies to |
|---|---|---|
| `video;digital stills; tables` | `["video","digital stills","tables"]` (split on `;`, trimmed, empty items dropped) | fields of schema type `array`: `data_modalities`, `primary_fire_safety_use`, `key_variables`, `key_outputs`, `provenance_requirements` |
| empty cell or `null` (any case) | JSON `null` (an empty list for array fields) | every field |
| `1,200` | `1200` | integer fields (`known_file_count`) |

**Fixed bug.** `seed.py` used to store the literal string `"null"`, for example as the `license` of `FF-NASA-CLD`, because `"null"` is truthy. It now goes through the decoder (`apps/api/tests/test_ingestion_adapters.py::test_the_three_ntrs_reports_and_nist_are_registered_and_the_pdfs_ingest` asserts this).

Text values must not contain `;` when the field is an array. Use `,` inside an item instead.

## 3. Fields

| Field | Type | Required | Allowed values / meaning | Example |
|---|---|---|---|---|
| `source_id` | string `^[A-Z0-9][A-Z0-9_-]{2,63}$` | yes | Immutable internal ID. `FF-PSI-<n>`, `FF-NTRS-<citation id>`, `FF-NASA-<slug>`, `FF-NIST-<slug>` | `FF-PSI-69` |
| `title` | string | yes | Canonical title | `Flame Extinguishment Experiment` |
| `short_name` | string/null | | Acronym or report number | `FLEX`, `NASA/TM-2000-209773` |
| `provider` | string | yes | Owning organisation | `NASA Glenn Research Center` |
| `repository` | enum | yes | `NASA PSI`, `NASA NTRS`, `NASA Science`, `NASA Open Data`, `NASA GRC FCF`, `Other` | `NASA PSI` |
| `psi_id` | string/null | | PSI investigation ID | `PSI-69` |
| `persistent_identifier` | string/null | | DOI or other durable ID | `doi:10.60555/mbq8-0451` |
| `source_type` | enum | yes | `investigation_dataset`, `technical_report`, `publication_corpus`, `media_dataset`, `supporting_documentation` | `technical_report` |
| `experiment_family` | string/null | | | `FLEX` |
| `flight_platform` | string/null | | | `ISS` |
| `data_modalities` | array | | Formats available | `video;tables;reports` |
| `primary_fire_safety_use` | array | | Why it matters | `extinction;flammability limits` |
| `key_variables` | array | | Inputs or conditions | `pressure;O2 mole fraction` |
| `key_outputs` | array | | Observations | `burning rate;extinction diameter` |
| `license` | string/null | | SPDX ID when known; `null` + an explanation in `notes` otherwise | `CC0-1.0` |
| `access_status` | enum | yes | `confirmed_public`, `public_page_verified_download_path_pending`, `reference_only` (registered, never downloaded), `unknown` | `reference_only` |
| `access_url` | URI | | Human-facing page | `https://ntrs.nasa.gov/citations/20000034017` |
| `data_access_url` | URI/null | | Direct download endpoint | NTRS `…/downloads/<id>.pdf` |
| `aws_bucket` | string/null | | | `s3://nasa-psi` |
| `version` | string/null | | Repository release | `Version 4`, `SRD 69` |
| `last_verified_utc` | date-time | | Last time a person checked the row | `2026-10-11T00:00:00Z` |
| `source_date_range` | string/null | | | `2000-03` |
| `known_file_count` | integer/null | | Files at the source (not necessarily mirrored) | `1` |
| `known_size` | string/null | | | `20 pages` |
| `ingestion_strategy` | enum | | `metadata_then_tabular_then_media`, `metadata_then_media`, `document_first`, `defer` | `document_first` |
| `notes` | string | | Provenance caveats, licence reasoning | |
| `provenance_requirements` | array | | What must be kept | `retain NTRS citation ID;hash the committed PDF` |
| `priority` | enum | yes | `P0`, `P1`, `P2` (MVP delivery priority) | `P1` |
| `p0_candidate_reason` | string/null | | Why it is (or would be) P0 | |
| `verification_state` | enum | | `verified`, `partially_verified`, `needs_followup` | `partially_verified` |

## 4. Adding a source (review checklist)

1. **Licence and terms.** Record the licence, or `null` with the reason in `notes`. Never scrape restricted content (MVP §7). A source whose terms aren't reviewed is `reference_only`.
2. **Relevance.** It must serve microgravity combustion or fire safety. Non-combustion sources get `domain = non_combustion` in `seed.py` (today only `FF-PSI-DSI`).
3. **Duplicates.** Search the registry for the same DOI, PSI ID or report number.
4. **Trust tier and priority.** P0 = needed for the MVP corpus; P1 = Phase 2; P2 = context. The trust tier comes from C4 / E2-7.
5. **Files.** For each mirrored file, add a line to `datasets/metadata/files.jsonl` and to `datasets/checksums/sha256.txt` (E2-4). Run `cd datasets && sha256sum -c checksums/sha256.txt`.
6. **Validate.** `python knowledge/ingestion/validate_registry.py` must print 0 problems.
7. **Report.** Write `docs/data/<SOURCE>_DATASET_REPORT.md` (E2-9), and add a row to the weekly note.

## 5. Current registry (generated from the CSV, 2026-10-12)

| source_id | Title | Repository | Type | Access | Strategy | Priority | Verification | License | Files |
|---|---|---|---|---|---|---|---|---|---|
| `FF-PSI-25` | Burning and Suppression of Solids-II | NASA PSI | investigation_dataset | confirmed_public | metadata_then_tabular_then_media | P0 | verified | CC0-1.0 | 695 |
| `FF-PSI-69` | Flame Extinguishment Experiment | NASA PSI | investigation_dataset | confirmed_public | metadata_then_media | P0 | verified | CC0-1.0 | 6555 |
| `FF-PSI-98` | Spacecraft Fire Safety Experiment-I | NASA PSI | investigation_dataset | confirmed_public | metadata_then_tabular_then_media | P0 | verified | CC0-1.0 | 76 |
| `FF-PSI-107` | Smoke Point in Co-flow Experiment | NASA PSI | investigation_dataset | confirmed_public | metadata_then_tabular_then_media | P0 | verified | CC0-1.0 | 188 |
| `FF-NASA-CLD` | Coflow Laminar Diffusion Flame | NASA Science | investigation_dataset | public_page_verified_download_path_pending | defer | P0 | partially_verified | — | — |
| `FF-NASA-FLEX2` | Flame Extinguishment Experiment-2 | NASA GRC FCF | investigation_dataset | public_page_verified_download_path_pending | defer | P0 | partially_verified | — | — |
| `FF-PSI-DSI` | Dynamical Selection of Three-Dimensional Interfacial Pattern | NASA PSI | investigation_dataset | confirmed_public | document_first | P2 | verified | — | 121811 |
| `FF-NTRS-20000034017` | Testing and Selection of Fire-Resistant Materials for Spacec | NASA NTRS | technical_report | confirmed_public | document_first | P1 | partially_verified | — | 1 |
| `FF-NTRS-20040053557` | Extinction Criteria for Opposed-Flow Flame Spread in a Micro | NASA NTRS | technical_report | confirmed_public | document_first | P1 | partially_verified | — | 1 |
| `FF-NTRS-20080034883` | Microgravity Flame Spread in Exploration Atmospheres: Pressu | NASA NTRS | technical_report | confirmed_public | document_first | P1 | partially_verified | — | 1 |
| `FF-NIST-WEBBOOK` | NIST Chemistry WebBook (SRD 69) | Other | supporting_documentation | reference_only | defer | P1 | needs_followup | — | — |

The DSI file count is the bucket listing. The four PSI P0 sources are mirrored locally under `datasets/raw/` (git-ignored, E2-10). The three NTRS PDFs are committed in `docs/research/`. NIST WebBook is registered only.

## Known limitations
- `FF-PSI-DSI` is `confirmed_public` with no licence recorded; it needs a follow-up.
- The NTRS rows were verified from the PDFs' own title pages, not from the NTRS record pages, so their licence is `null` until the record terms are read.
- `last_verified_utc` is set by hand; nothing re-checks the URLs automatically.

## Changelog
- 1.0.0 (2026-10-12): first guide. Shared decoder and validator added; 3 NTRS sources and NIST WebBook registered.
