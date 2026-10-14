# E2-8: Admin data operations guide

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Anas (E2) | Draft: CLI procedures today; admin UI endpoints are B2/B3 (sign-off: Belal E4) | 0.5.0 | 2026-10-12 | B2, B3, B4 | `seed.py`, `ingest.py`, `vector_index.py`, `knowledge_version.py`, `ai_runtime.py` |

**Roles.** Until ADR-009 step 2, "admin" means holding database access or the write token. Every procedure below lists the audit record it creates **today**. Where none is created yet, it says so, and the B2/B3 endpoint must add one in `audit_event`.

| # | Procedure | Role | How (today) | Audit record | Rollback |
|---|---|---|---|---|---|
| 1 | Register a source | admin (repo write) | Add the CSV row → `validate_registry.py` → PR (E2-1 §4) → `python -m flame_api.seed` | git history + PR review | revert the commit; the `source` row remains (harmless) unless deleted |
| 2 | Start or retry ingestion | admin | `python -m flame_api.ingest` (idempotent; retries every non-quarantined file) | `ingestion_run` rows; `knowledge_publication` | republish the previous version (`trigger="rollback"`) and restore a backup if data must go |
| 3 | Inspect failed files | admin / read | `select file_id, source_id, original_filename, quarantine_reason from file_record where status = 'quarantined';` and `select * from ingestion_run where transformation_id = 'quarantine';` | — | — |
| 4 | Reprocess an asset | admin | Fix or re-mirror the file. For a checksum mismatch, decide which is right: the new bytes need a new `files.jsonl` line (new file_id). Then `update file_record set status = 'active', quarantine_reason = null where file_id = :id;` and run `ingest`. | **none yet**: B2 endpoint must write `audit_event(action='file.reprocess')` | set the status back to `quarantined` |
| 5 | Correct metadata | admin | Never update originals. Add a `manual` evidence row, or record the metadata change as an `audit_event` with before/after (E2-4 §4) | `audit_event` | apply the `before` values |
| 6 | Link a document to an experiment | admin | Planned: `knowledge_relation(describes)` with `extraction_method='manual'` | `audit_event` + the relation row | set `review_status='rejected'` |
| 7 | Approve records for indexing | admin | Set the evidence `payload.review_status` to `human_verified` or `rejected`. Retrieval exclusion of `rejected` is M2 work. | **none yet**: B3 endpoint | restore the previous status |
| 8 | Merge entities | admin | E2-6 §4 (`merged_into`, re-point edges in one transaction) | `audit_event(action='entity.merge')` | unset `merged_into` and re-point back (from the audit `before`) |
| 9 | Rebuild indexes | admin | `python -m flame_api.vector_index build` (L-5 §4) | `knowledge_publication` (trigger `vector_index_build`) | republish the previous version; restore the backup if vectors were dropped |
| 10 | Change the AI execution mode | write token | `PUT /api/admin/ai/mode` | `audit_event(action='ai.mode.changed')` | PUT the previous mode |

## Known limitations
Procedures 4, 5 and 7 are SQL today. The admin dashboard (Belal, B2/B3/B9) has to wrap them in authenticated, audited endpoints before non-engineers use them.

## Changelog
- 0.5.0 (2026-10-12): first version.
