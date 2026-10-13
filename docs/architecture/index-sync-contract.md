# L-5: Index synchronization contract

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | In review (sign-off: Anas E2, Eman E1) | 1.0.0 | 2026-10-12 | D3, D6, §11 | `flame_api/ids.py`, `ingest.py`, `vector_index.py`, `knowledge_version.py`, migration `0004` |

PostgreSQL is the system of record. Everything else is a derived index rebuilt from it:
- the pgvector table `chunk_embedding` (ADR-002);
- the graph tables `knowledge_entity` and `knowledge_relation` (ADR-007);
- Redis CAG entries (M4, Eman).

## 1. Stable IDs (same rule in every store)

| Object | ID | Inputs | Stable across re-ingest? |
|---|---|---|---|
| file | `sha256:<first 16 hex>` | file bytes | yes |
| document | `stable_ulid("document:" + file_id)` | file | yes |
| chunk (page) | `<sha256[:16]>:v1:<page>` | file + page | yes |
| chunk (section, HTML/JSON) | `<sha256[:16]>:v1:s<n>` | file + section ordinal | yes, while the file is unchanged |
| evidence (page) | `stable_ulid("evidence:<sha256>:page:<n>")` | file + page | yes |
| evidence (section) | `stable_ulid("evidence:<sha256>:section:s<n>")` | file + section | yes |
| experiment / condition | `stable_ulid(...)` of source, table file, row (`ingest.py`) | table row | yes |
| embedding row | `chunk_id` (PK) + `model` | chunk + model | yes; replaced when `model` changes |
| graph entity (rule; no writer yet, D2) | `stable_ulid(entity_type + ":" + canonical_name)` | type + name | yes |
| graph relation (rule; no writer yet, D2) | `stable_ulid(subject_id + predicate + object_id + evidence_id)`, unique on those four | edge + evidence | yes |
| image asset | `stable_ulid("image-asset:" + sha256)` | image bytes | yes |

A parser upgrade (`pymupdf-pages-0.1.0` → `0.2.0`) keeps every ID: IDs never include a parser version, and `parser_version` is stored alongside.

## 2. Publication drives synchronization

A knowledge version is published (E2-5) when:
- `ingest` finishes with a changed file set (`corpus-<hash>`);
- `vector_index build` finishes (`bge-small-en-v1.5-<rows>-<date>`);
- an operator publishes manually, or rolls back.

Each publication writes one `knowledge_publication` row, then sends `{type: "knowledge_version.published", knowledge_version, previous_version, trigger, counts, …}` on Redis channel `flame:knowledge.published`.

| Consumer | On event | Catch-up (missed event, restart) |
|---|---|---|
| Vector index | the `ingestion` trigger means chunks may be missing vectors → run `vector_index build`, which embeds only chunks without a current-model vector and deletes vectors of other models | compare `vector_index_manifest.row_count` with `count(document_chunk)` |
| CAG (Eman, M4) | invalidate entries whose `cache_entry.knowledge_version` ≠ the new version | on startup, invalidate where the version ≠ `current_knowledge_version()` |
| Graph (D6) | re-extract entities and edges for documents whose evidence changed | compare the extraction's `knowledge_version` per relation |

## 3. Detecting partial failure

| Check | Query | Healthy |
|---|---|---|
| Chunks without vectors | `select count(*) from document_chunk c left join chunk_embedding e using (chunk_id) where e.chunk_id is null` | 0 after a build |
| Vectors of a stale model | `select count(*) from chunk_embedding where model <> 'BAAI/bge-small-en-v1.5'` | 0 |
| Index vs publication | `vector_index_manifest.knowledge_version` = newest `knowledge_publication` with trigger `vector_index_build` | equal |
| Orphan relations | `knowledge_relation` whose `evidence_id` has no `evidence` row | 0 |

`/api/health` → `vector_index` reports `up`, `stale` (chunks without vectors) or `missing`.

## 4. Observable rebuild procedure (§11)
1. **Status.** Check `GET /api/health` (`vector_index`) and the §3 queries.
2. **Rebuild.** `python -m flame_api.vector_index build`. Progress is logged as `vector_index embedded=<n>/<total>` per batch of 64. It is resumable: a rerun skips chunks that already have current vectors.
3. **Full re-embed (model change).** Change `MODEL_NAME`, then run `build`. Vectors of the old model are deleted and every chunk is re-embedded. Search falls back to lexical until the build completes.
4. **Rollback.** Re-publish the previous version with `knowledge_version.publish(session, "<old>", trigger="rollback")`. This only works if the old vectors still exist. Otherwise restore the PostgreSQL backup (E2-10 §5).

## Known limitations
- The vector consumer is a CLI step, not a subscriber. The publication event is emitted, but nothing listens yet (CAG is M4/Eman, graph is D6).
- Section chunk IDs are ordinal, so editing an HTML or JSON source changes its later section IDs. The changed file is a new file (new sha256), so this is consistent, but its evidence IDs change.

## Changelog
- 1.0.0 (2026-10-12): contract as built in PR #14.
