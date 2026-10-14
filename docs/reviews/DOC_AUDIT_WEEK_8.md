# Documentation audit: Week 8

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Interim run 2026-10-14; the week-8 run is still to do | 0.2.0 | 2026-10-14 | G-5 | — |

## Procedure
1. Pick the commit at the end of week 8 and record it here.
2. For every row in `docs/README.md` §1–§3, check the document against the code at that commit:
   - the header is present;
   - the paths in "Code paths" exist;
   - every command quoted in the document still runs and gives the quoted counts;
   - the changelog is updated;
   - Known limitations are present.
3. List stale documents in the table below with an owner and a new due date, and copy them into that week's G-4 status note.

| Document | Stale because | Owner | New due date |
|---|---|---|---|
| `docs/evaluation/*` (moved from flat-named uploads) | Owner/status headers not checked and not added by this run | Ziad | next audit |
| `api/API_SCHEMAS.md` | Generated file, exempt; regenerate with `render_api_schemas.py` | Lead | - |
| MVP-era notes (`DAY1_DATA_ACQUISITION`, `P0_CANDIDATES`, `COMBUSTION_DATASET_ANALYSIS`, `DSI_DATASET_REPORT`, `plan/DAY2_TASKS`) | Working notes with a status line only | Anas | next audit |

## Interim run (2026-10-14, base commit `7d3658d`)

- **Links:** every relative Markdown link under `docs/` (141 links in 94 files). One was broken (`docs/evaluation/provenance_checklist.md` to `evaluation_report.json`); the file was regenerated with `python run_evaluation.py`. Now 0 broken.
- **Index:** `docs/README.md` pointed at `CV/pipline.md`; it now points at `docs/cv/`.
- **Missing changelog or limitations:** added to `WEEKLY_Anas_E2`, `PHASE2_WEEK_1`, `AURA_INTEGRATION_*`, `api/CHANGELOG`, `adr/README`, `service-contracts`, `FRONTEND_API_CONTRACT`.
- **Stale claim fixed:** `FRONTEND_API_CONTRACT.md` said the API was not implemented; `openapi.json` 0.2.0 marks all 15 operations implemented.
- **Gates:** `ruff check .`, `validate_registry.py` (11 sources, 0 problems), `render_api_schemas.py --check`, and pytest on `tests/unit`, `tests/cv`, `tests/eval`, `tests/integration` and `apps/api/tests` passed.

Not checked: that every command quoted in each document still gives the quoted counts (only the registry command was re-run).

## Known limitations
The interim run does not replace the end-of-week-8 audit. The `Code paths` column was not machine-verified.

## Changelog
- 0.2.0 (2026-10-14): interim run recorded.
- 0.1.0 (2026-10-12): procedure only.
