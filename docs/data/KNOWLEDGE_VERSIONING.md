# E2-5: Knowledge versioning and publication

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Anas (E2), with Eman (E1) | In review: **needs Eman's sign-off** on the consumer contract | 1.0.0 | 2026-10-12 | M4, D6, 2H Task 7 | `apps/api/flame_api/knowledge_version.py`, `ingest.py`, `vector_index.py`, table `knowledge_publication` |

## 1. What a knowledge version is

A name for one consistent state of the searchable knowledge:

| Kind | Format | Changes when | Trigger |
|---|---|---|---|
| Corpus | `corpus-<12 hex>` = sha256 of the sorted `(file_id, input_sha256, transformation_id)` of every non-quarantine `ingestion_run` | a file is added, changed or removed, or a parser is upgraded | `ingestion` (end of `python -m flame_api.ingest`) |
| Index | `bge-small-en-v1.5-<rows>-<YYYYMMDD>` | a vector build completes | `vector_index_build` |
| Manual / rollback | any | an operator republishes | `manual`, `rollback` |
| Sync | any | reconnection sync completed (E2-10) | `sync` |

The **current** knowledge version is the newest row of `knowledge_publication` (`current_knowledge_version()`). Chat, the dashboard counts and `/api/health` report it. Search reports the index version it searched.

## 2. The publication event

1. `knowledge_version.publish(session, version, trigger=…, counts=…)` writes one `knowledge_publication` row: `publication_id`, `knowledge_version` (unique), `previous_version`, `trigger`, `published_at`, `payload.counts`. It commits.
2. Then, best effort, it sends JSON on the Redis channel `flame:knowledge.published`:

```json
{
  "type": "knowledge_version.published",
  "schema_version": "1.0.0",
  "publication_id": "…",
  "knowledge_version": "bge-small-en-v1.5-37-20261011",
  "previous_version": "corpus-12a92c60110f",
  "trigger": "vector_index_build",
  "published_at": "2026-10-11T22:46:12Z",
  "counts": {"chunk_embeddings": 37, "embedded": 37}
}
```

(The values are from the 2026-10-11 run; `published_at` is illustrative.)

**Ordering and delivery guarantees:**
- the row is committed **before** the message is sent;
- there is **at most one** message per row;
- delivery to Redis is **not** guaranteed (Redis down or offline). The row is.
- Ordering is by `published_at`.

Consumers must treat the table as the truth and catch up on start-up: compare their own version with `current_knowledge_version()`. Republishing an existing version is a no-op, except for `rollback`.

## 3. Consumers

| Consumer | Owner | On event | Status |
|---|---|---|---|
| CAG invalidation | Eman (E1, M4) | invalidate `cache_entry` rows (and their Redis values) whose `knowledge_version` ≠ the new version | **Not built.** Contract defined here. |
| Vector index | Lead | on `ingestion`, run `vector_index build` | Manual / CLI today (L-5) |
| Graph sync | Anas + Eman (D6) | re-extract for changed documents | Not built |
| UI | Belal | show the version and sync age | `knowledge_version` is in chat and dashboard responses |

## 4. Who triggers publication
- Automatically: the ingest CLI and the index build.
- Manually: an operator with database access (`publish(..., trigger="manual")`). An admin endpoint is planned with B2, under ADR-009 RBAC.

## 5. Rollback

`publish(session, "<older version>", trigger="rollback")` moves that version to the newest row, with `previous_version` = the version it replaces. Consumers then invalidate as for any publication. This only restores *what is reported*. If the data or vectors for the old version are gone, restore the PostgreSQL backup (E2-10 §5).

## 6. Sync events (2H)

A completed reconnection sync (E2-10 §6) publishes with trigger `sync`. Its effect on caches is the same as any publication. Local answers made while offline keep the version they were made with, so a user can see they predate the sync.

## Known limitations
- The corpus and index versions share one sequence. The current version is whichever came last; the two kinds are told apart by prefix and trigger.
- No consumer subscribes yet.

## Changelog
- 1.0.0 (2026-10-12): the publication event is implemented; the contract is drafted for Eman's sign-off.
