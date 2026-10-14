# Weekly note: Anas (E2)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Anas (E2) | Current (append one section per week) | — | 2026-10-13 | E2 §6 | — |

## Week 1 (to 2026-10-13)

**Sources added:** `FF-NTRS-20000034017`, `FF-NTRS-20040053557`, `FF-NTRS-20080034883` (ingested), and `FF-NIST-WEBBOOK` (reference only). The registry now has 11 sources (`python knowledge/ingestion/validate_registry.py` → 11 checked, 0 problems).

**Ingestion counts** (PostgreSQL, committed corpus only; query in E2-2 §6):

| Metric | Value |
|---|---|
| Documents | 3 |
| Pages | 39 |
| Chunks / embeddings | 37 / 37 |
| Image assets with lineage | 182 |
| Quarantined | 0 |
| Skipped (not on disk) | 100 |

**Schema changes:** migration `0004_phase2_tables` (M8 tables, quarantine columns, knowledge publication).

**Data defects:**
- **Fixed:** the registry decoder (literal `"null"` was stored as text); the first `seed` on a fresh database skipped every file; the DSI lineage is now loaded into the database.
- **Open:**
  - `FF-PSI-DSI` has no licence;
  - NTRS licences are unconfirmed;
  - pp. 14–15 of the 2008 report need OCR;
  - the NIST DOI needs re-verifying when connected.

**Documents changed:** E2-1 to E2-10 (new or rewritten); status lines on the MVP data notes; `knowledge/README.md` module map.

**Validation commands run:** `python -m pytest`; `ruff check .`; `validate_registry.py`; `alembic upgrade head` / `downgrade` on PostgreSQL 16; the restore drill (E2-10 §5).

**Known limitations:**
- The restore drill and Alembic up/down were run on PostgreSQL 16 only. They were not re-run after the `Princess` merge.
- The corpus is 3 PDFs (39 pages, 37 chunks); 100 referenced files are not on disk and are reported as skipped.
- Open data defects are listed above.

**Changelog:**
- 2026-10-14: limitations and changelog added to this note.
- 2026-10-13: Week 1 section.
