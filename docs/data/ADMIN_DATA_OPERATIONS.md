# E2-8: Admin data operations guide

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Anas (E2) | Draft: procedures 3, 4, 7 and the audit log are audited admin endpoints (P2-8); the rest are CLI (sign-off: Belal E4) | 0.7.0 | 2026-11-12 | B2, B3, B4 | `admin.py`, `seed.py`, `ingest.py`, `vector_index.py`, `knowledge_version.py`, `ai_runtime.py` |

**Roles.** "Admin" means holding database access, or an API key with the `admin` scope (ADR-009 step 2; created with `python -m flame_api.clients create NAME --scopes admin --owner PERSON`). The deprecated write token still counts as admin until it is removed. Every procedure below lists the audit record it creates **today**.

**Admin endpoints** (`apps/api/flame_api/admin.py`, tag `Admin` in `docs/api/openapi.json`). Every `/api/admin/` route needs the **`admin` scope, reads included** (a `write` key gets 403): quarantine reasons, ingestion runs and the audit log are operator data, not for the read-only web tier or AURA. All of them are `x-aura-exclude: true` (ADR-004). Each change writes one `audit_event` row (`actor`, `action`, `target_type`, `target_id`, `before`, `after`, `request_id`) in the same transaction as the change, and none deletes scientific source data. An optional `note` is kept in the audit row's `after.note`. Read the log with `GET /api/admin/audit?action=&target_type=&target_id=&page=&page_size=`. The SQL in the table below is the fallback for when the API is down; a change made that way writes no audit row, so add one by hand.

**No admin UI.** The web dashboard deliberately never holds an admin credential: its proxy (`apps/web/app/api/[...path]/route.ts`) only forwards an allow-list of read paths plus `POST /api/chat` (read token) and passcode-gated `POST /api/analyses` uploads (a dedicated `write`-only client key, see `apps/web/README.md`). Call the admin endpoints with your own admin key from a trusted shell, e.g. `curl -H "Authorization: Bearer $FLAME_ADMIN_KEY" …` (the deprecated write token also works).

| # | Procedure | Role | How (today) | Audit record | Rollback |
|---|---|---|---|---|---|
| 1 | Register a source | admin (repo write) | Add the CSV row → `validate_registry.py` → PR (E2-1 §4) → `python -m flame_api.seed` | git history + PR review | revert the commit; the `source` row remains (harmless) unless deleted |
| 2 | Start or retry ingestion | admin | `python -m flame_api.ingest` (idempotent; retries every non-quarantined file) | `ingestion_run` rows; `knowledge_publication` | republish the previous version (`trigger="rollback"`) and restore a backup if data must go |
| 3 | Inspect failed files | admin scope | `GET /api/admin/files?status=quarantined` (file, source, `quarantine_reason`) and `GET /api/admin/ingestion-runs?transformation_id=quarantine`. SQL fallback: `select file_id, source_id, original_filename, quarantine_reason from file_record where status = 'quarantined';` and `select * from ingestion_run where transformation_id = 'quarantine';` | none (read only) | — |
| 4 | Reprocess an asset | admin scope | Fix or re-mirror the file. For a checksum mismatch, decide which is right: the new bytes need a new `files.jsonl` line (new file_id). Then `POST /api/admin/files/{file_id}/reprocess` (body `{"note"?}`; 409 `FILE_NOT_QUARANTINED` if the file is not quarantined) and run `python -m flame_api.ingest`: the endpoint does not ingest. SQL fallback: `update file_record set status = 'active', quarantine_reason = null where file_id = :id;` | `audit_event(action='file.reprocess', target_type='file_record')`, before/after `{status, quarantine_reason}` | set the status and reason back from the audit `before` (ingest re-quarantines a file whose checksum still does not match) |
| 5 | Correct metadata | admin | Never update originals. To withdraw a wrong machine extraction, reject it (procedure 7). To supply the right value, add a `manual` evidence row, or record the metadata change as an `audit_event` with before/after (E2-4 §4). No endpoint creates `manual` evidence yet (SQL only). | `audit_event` (`evidence.review` for a rejection) | apply the `before` values |
| 6 | Link a document to an experiment | admin | Planned: `knowledge_relation(describes)` with `extraction_method='manual'` | `audit_event` + the relation row | set `review_status='rejected'` |
| 7 | Approve records for indexing | admin scope | `PUT /api/admin/evidence/{evidence_id}/review` with `{"review_status": "human_verified" \| "rejected" \| "machine_extracted", "note"?}` (`raw` is refused). `rejected` evidence is excluded from `/api/search` (lexical and vector hits; an experiment cites its first unrejected condition, and drops out when all are rejected), so `/api/chat` never retrieves or cites it. A re-ingest keeps `human_verified` and `rejected`. SQL fallback: update `evidence.payload` (keep every other key). | `audit_event(action='evidence.review', target_type='evidence')`, before/after `{review_status}` | PUT the previous status from the audit `before` |
| 8 | Merge entities | admin | E2-6 §4 (`merged_into`, re-point edges in one transaction) | `audit_event(action='entity.merge')` | unset `merged_into` and re-point back (from the audit `before`) |
| 9 | Rebuild indexes | admin | `python -m flame_api.vector_index build` (L-5 §4) | `knowledge_publication` (trigger `vector_index_build`) | republish the previous version; restore the backup if vectors were dropped |
| 10 | Change the AI execution mode | admin scope | `PUT /api/admin/ai/mode` | `audit_event(action='ai.mode.changed')` | PUT the previous mode |

## Known limitations
- Procedures 4 and 7 are audited endpoints; 5 (manual evidence rows), 6 and 8 are still SQL or planned.
- There is no admin UI on purpose (see above). A UI for non-engineers needs its own service holding an admin key, with its own login in front of it. `actor` is the admin key's client name (each admin key names its owner), or `write-token` for the deprecated token.
- `GET /api/evidence/{id}` and `GET /api/experiments/{id}` still return rejected evidence, labelled `review_status: rejected`, so the review can be seen and undone; the contract says the UI must not render it as support.

## Changelog
- 0.7.0 (2026-11-12): admin routes need the `admin` scope (ADR-009 step 2); admin keys name their owner.
- 0.6.0 (2026-11-02): procedures 3, 4 and 7 point at the audited admin endpoints (P2-8); search and chat exclude rejected evidence; admin reads need the write token.
- 0.5.0 (2026-10-12): first version.
