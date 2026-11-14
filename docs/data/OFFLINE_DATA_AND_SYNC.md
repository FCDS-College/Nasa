# E2-10: Offline data availability and synchronization policy

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Anas (E2) | Draft: availability (W3) done; sync policy (W7) proposed | 0.9.2 | 2026-11-14 | 2H Task 7 | `infrastructure/compose.yaml`, `knowledge_version.py`, `ingest.py`, `vector_index.py` |

Shared with the Lead's [L-8 runbook](../operations/RUNBOOK.md) and [H-6](../hybrid-ai/PHASE_2_OFFLINE_DEPLOYMENT_GUIDE.md).

## 1. Offline inventory

| Data | Location | Size | In git? | Re-acquire |
|---|---|---|---|---|
| Source registry, file manifest, checksums, CV sample manifest | `datasets/registry/`, `datasets/metadata/`, `datasets/checksums/`, `datasets/samples/cv/manifest.jsonl` | small | yes | git |
| NTRS reports (27) | `docs/research/` | 27,622,004 B | yes | git |
| CV samples (185) | `datasets/samples/cv/` | in git (3 MP4 + images) | yes | git |
| PSI experimental tables + ISA-Tab metadata (22 + 24 files from 24 PSI sources) | `datasets/raw/psi_api/*/Experimental table/`, `…/metadata/` | 513,175 B (`git ls-files` + `stat`, 2026-11-14) | **yes** ([ADR-012](../architecture/adr/ADR-012-commit-psi-tables.md)) | git; or `python knowledge/ingestion/install_datasets.py --only tables` |
| PSI mirrors, everything else (BASS-II, FLEX, SAFFIRE-I, SPICE media and documents) | `datasets/raw/psi_api/…` | local only; see `datasets/manifests/psi_pilot_selection.csv` | **no** (git-ignored) | `python knowledge/ingestion/psi_download.py datasets/manifests/psi_pilot_selection.csv` (psi.nasa.gov) |
| DSI subset | `datasets/raw/nasa_psi/DSI/` | local only | **no** | `aws s3 cp --no-sign-request …` (README "Data quick start") |
| Database (metadata, evidence, vectors, audit) | `postgres-data` volume | 226,560 B as `pg_dump -Fc` for the committed corpus (2026-10-13) | no | backup (§5) |
| Uploads and CV artifacts | `minio-data` volume | per use | no | backup (§5) |
| Embedding model | `model-cache` volume | 67,181,750 B | no | H-3 §2 |
| Local LLM | `ollama-models` volume | 1,929,912,432 B | no | H-3 §2 |

**Committed vs local-only.** A fresh clone has the committed data: the 27 NTRS reports, the samples, and the PSI experimental tables and ISA-Tab metadata (ADR-012). Ingesting them gives 1958 table experiments (`apps/api/tests/test_ingestion.py`), of which 1950 are flight tests from 19 PSI investigations (`test_fire_safety_api.py`); the other 8 rows are the Cool-flame transitions ground study (FF-PSI-142). PSI media, raw data files and the DSI subset exist only where `datasets/raw/` was mirrored.

## 2. Unavailable offline, and what answers must say

| Source | Offline | Disclosure |
|---|---|---|
| `psi.nasa.gov` API, `s3://nasa-psi` | no new data | Answers carry `knowledge_version`; the UI shows the last sync time (§3) |
| NTRS record pages | no | The committed PDFs are fully available |
| NIST WebBook | no (reference only) | Never claim WebBook values unless they are stored |
| AURA, HF Space | blocked | See H-1 |

Rule (2H Task 5): never claim the latest NASA or NIST information unless it is stored locally.

## 3. Sync age
- `knowledge_publication.published_at` of the newest row is the time the local knowledge last changed. `current_knowledge_version()` gives its name, and chat and the dashboard return it.
- The last successful acquisition per source is `max(file_record.retrieved_at)` for that source.
- The UI work (Belal, E4-10) should show both: "knowledge version X, last updated T". An API field for the per-source last sync is planned with B1.

## 4. Resumable ingestion and indexing

See [E2-2 §4 and §7](INGESTION_PIPELINE.md). In short:
- stable IDs and merges mean a rerun after any interruption converges without duplicates;
- the index build embeds only chunks without a current-model vector, so a restart resumes where it stopped;
- quarantined files stay quarantined across restarts.

## 5. Local backup and restore

**Scripted (P2-11):** `infrastructure/backup/backup.sh` writes `$BACKUP_DIR/<UTC timestamp>/` with a custom-format `pg_dump` of `FLAME_DATABASE_URL`, exact per-table row counts, a mirror of `FLAME_S3_BUCKET` (`aws s3 sync`, or `mc mirror` when only `mc` is installed) and a `MANIFEST` with checksums, then deletes timestamped backups older than `BACKUP_RETENTION_DAYS` (default 14). `infrastructure/backup/restore.sh <dir>` checks the checksums, runs `pg_restore --no-owner --no-privileges` into `RESTORE_DATABASE_URL` (refused when it equals `FLAME_DATABASE_URL` unless `RESTORE_ALLOW_SAME=1`), fails if any table's row count differs from the backup, and syncs the objects into `RESTORE_S3_BUCKET` (default `FLAME_S3_BUCKET`). Credentials come only from the environment (`FLAME_S3_ACCESS_KEY`/`FLAME_S3_SECRET_KEY` or `AWS_*`); the scripts need `pg_dump`/`psql` of the server's major version, `python3`, and `aws` or `mc`. Usage and every variable are in the scripts' headers and [RUNBOOK §3](../operations/RUNBOOK.md#3-backup-and-restore).

The manual equivalents inside Compose:

```bash
# PostgreSQL (metadata, evidence, vectors, audit, publications)
docker compose -f infrastructure/compose.yaml exec -T postgres pg_dump -U flame -Fc flame > flame-$(date -u +%F).dump
# restore into a fresh database
docker compose -f infrastructure/compose.yaml exec -T postgres createdb -U flame flame_restore
docker compose -f infrastructure/compose.yaml exec -T postgres pg_restore -U flame -d flame_restore --no-owner < flame-YYYY-MM-DD.dump
# S3 artifact bucket (the `minio` service is SeaweedFS's S3 gateway; same image as `minio-init`)
docker run --rm --network flame-in-freefall_default -v "$PWD/s3-backup:/backup" \
  -e AWS_ACCESS_KEY_ID="$MINIO_ROOT_USER" -e AWS_SECRET_ACCESS_KEY="$MINIO_ROOT_PASSWORD" -e AWS_DEFAULT_REGION=us-east-1 \
  amazon/aws-cli@sha256:acc32af784911165a8e78b63950625d174ba79b800a66a436c974689c87cd755 \
  --endpoint-url http://minio:9000 s3 sync s3://flame-artifacts /backup
# Model volumes (H-6 §4)
docker run --rm -v flame-in-freefall_model-cache:/m -v "$PWD:/b" alpine tar cf /b/model-cache.tar /m
docker run --rm -v flame-in-freefall_ollama-models:/m -v "$PWD:/b" alpine tar cf /b/ollama-models.tar /m
```

**Schedule (proposed):** PostgreSQL daily and before every migration; MinIO weekly; model volumes after each model change.

**Restore drill record:**

| Date | Who | What | Result |
|---|---|---|---|
| 2026-10-13 20:15 UTC | Anas (Lead/E2), dev container, PostgreSQL 16 + pgvector 0.6.0 (apt), not Compose | `pg_dump -Fc` of `flame` (226,560 B, 1.1 s) → `pg_restore` into a new database `flame_restore` (0.4 s) | **Pass.** Counts identical before and after: 11 sources, 124 files, 37 chunks, 37 embeddings, 37 evidence, 182 image assets, 2 publications, manifest `bge-small-en-v1.5-37-20261011`. An HNSW nearest-neighbour query works on the restored copy. |
| 2026-11-02 19:34 UTC | P2-11 (agent session, worktree branch), dev container: PostgreSQL 16.15 + pgvector 0.6.0 (apt), Redis 7 db 2, `moto_server` as the S3 stand-in (no MinIO), not Compose | Fresh `flame_ops`: `alembic upgrade head` (to `0004_phase2_tables`), `python -m flame_api.seed`, `python -m flame_api.ingest`; uvicorn + `rq worker --burst` produced 2 completed image analyses (8 objects) and 2 `ai.mode.changed` audit rows. `BACKUP_DIR=… infrastructure/backup/backup.sh` (2.1 s: 173,688 B dump, 8 objects) → `su postgres -c "createdb -O flame flame_ops_restore"` → `RESTORE_DATABASE_URL=…/flame_ops_restore RESTORE_S3_BUCKET=flame-artifacts-restore infrastructure/backup/restore.sh <dir>` (2.3 s) | **Pass.** Row counts identical for all 21 tables: alembic_version 1, analysis_result 2, audit_event 2, cache_entry 0, chunk_embedding 0, dataset 0, document 3, document_chunk 37, evidence 39, experiment 0, experiment_condition 0, file_record 124, image_asset 182, ingestion_run 3, knowledge_entity 0, knowledge_publication 1, knowledge_relation 0, memory 0, model 8, source 11, vector_index_manifest 0. Restored copy at `0004_phase2_tables` with pgvector 0.6.0; the S3 listing (key and size) of the restored bucket matches the source, 8 of 8. Retention pruned a 2-month-old timestamped directory and left a non-backup directory alone; restoring onto `FLAME_DATABASE_URL` was refused. No embeddings were built (no model download in the container), so pgvector data was not exercised this time; the 2026-10-13 drill covered it. |
| Pending | another engineer | the full Compose stack incl. MinIO (`mc mirror` path, untested) and model volumes | — |

## 5a. What never syncs automatically

Local videos, uploaded images, documents, prompts, chat content and research data are **never uploaded** on reconnection (2H Task 7). Moving anything out requires an explicit operator action.

## 6. Synchronization policy on reconnection (proposed for Week 7)

1. **Detect.** `/api/ai/providers` shows external providers healthy again, and an operator switches the mode (`PUT /api/admin/ai/mode`, audited).
2. **What may sync, inbound only:**
   - new or changed source files from the registry's access URLs (the Acquire stage);
   - registry metadata updates through a reviewed PR.
3. **Conflicts.**
   - A remote file whose sha256 differs from the local one is a **new file**: a new file_id, with the old one kept and quarantined if it is withdrawn. Originals are never overwritten.
   - A registry field changed both locally and upstream: the reviewed PR wins, and the loser goes into the PR discussion.
   - Corrections made offline (`manual` evidence, `audit_event`) always win over machine extraction.
4. **Outcome record.** The sync run publishes a knowledge version with trigger `sync` and `counts` (files added, changed, quarantined). Each fetched file gets an `ingestion_run`.
5. **Resume cloud operations.** The circuit breakers half-open on their own, and the mode change re-enables external providers.

## Known limitations
- The sync steps are manual today; no sync job exists.
- Both drills ran on a dev host, not the Compose stack; the 2026-11-02 drill covered S3 through `aws s3 sync` against `moto_server`, not MinIO, and nothing schedules `backup.sh` yet (a host cron or Railway cron job is still to be set up).
- The per-source last-sync API field is not built.

## Changelog
- 0.9.0 (2026-11-07): the PSI experimental tables and ISA-Tab metadata are committed (ADR-012); NTRS corpus is 24 reports.
- 0.9.1 (2026-11-13): NTRS corpus is 27 reports (Apollo 1 scenario, ADR-013).
- 0.9.2 (2026-11-14): the committed PSI tables and metadata are 22 + 24 files (513,175 B) and ingest to 1958 experiments (1950 flight tests, 19 investigations). The "committed vs local-only" paragraph no longer says the tables are local-only.
- Unreleased (P2-11): `infrastructure/backup/backup.sh` and `restore.sh`; second restore drill (database and object storage) recorded.
- 0.8.0 (2026-10-13): inventory, disclosure rules, backup commands, first restore drill, proposed sync policy.
