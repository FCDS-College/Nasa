# E2-4: Provenance and lineage

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Anas (E2) | In review (peer sign-off: Eman E1) | 1.0.0 | 2026-10-12 | M9, B3, D6, 2H Task 7 | `models.py`, `ingest.py`, `seed.py`, `knowledge_version.py`, `generation.py` |

## 1. The chain

```text
answer / analysis
  └─ evidence_id                  (chat sources[], interpretation statements[].evidence_ids)
      └─ evidence row             kind, origin, locator {page | section | table_row | frame}, excerpt,
                                  payload.extraction_method, extraction_confidence, transformation_id
          ├─ document_chunk / experiment_condition   (same evidence_id)
          └─ document  ── parser_version, knowledge_version
              └─ file_record      sha256, original_filename, retrieved_at, canonical_source_url, parent_file_id
                  └─ source       access_url, persistent_identifier (DOI), license, last_verified (registry)
```

Every hop is a column, so a SQL join follows the chain from any evidence ID to the source URL and checksum:

```sql
select e.evidence_id, e.locator, d.title, d.parser_version, f.sha256, f.original_filename, f.retrieved_at,
       f.canonical_source_url, s.access_url, s.persistent_identifier
from evidence e
join file_record f on f.file_id = e.file_id
join source s on s.source_id = e.source_id
left join document d on d.document_id = e.document_id
where e.evidence_id = :id;
```

The same chain is served by `GET /api/evidence/{id}` (`source`, `file` blocks) and `GET /api/documents/{id}`. The checksum files are `datasets/checksums/sha256.txt` (`sha256sum -c` format) and `datasets/metadata/files.jsonl`.

Chat keeps only citations that were in its retrieved set, whichever model answers (`generation.answer_question`), so every cited `evidence_id` resolves through this chain.

## 2. Derived artifacts and `parent_file_id`

| Artifact | Lineage |
|---|---|
| CV samples, incl. DSI frames | `image_asset.parent_file_id` → the raw archive's `file_record`. `payload.member` names the zip member path, and `payload.parent_file_id_declared` keeps the manifest value. |
| Analysis masks / overlays / preprocessed images | `analysis_result.artifacts[]` with sha256, linked by `analysis_id`; the original upload is stored with its sha256 |
| Measurement evidence | `evidence.kind = image_measurement`, `analysis_id` |

**DSI frames: fixed.** This was re-verified on 2026-10-12. `datasets/samples/cv/manifest.jsonl` already gave all 185 samples a `parent_file_id`, including the 12 DSI frames (parent `sha256:0473cfa2f03e287e`, `raw/nasa_psi/DSI/Data/S1 activity 4.zip`). What was missing was the database: derived frames were never loaded. `seed_image_assets` now loads the 182 image samples with their parent. Asserted by `test_ingestion_adapters.py::test_derived_frames_keep_their_parent_and_models_are_registered`; no `image_asset` row has a null parent.

## 3. Correction and removal impact (D6, B3)

To find everything affected when file `F` (or source `S`) is corrected or removed:

| Object | Query |
|---|---|
| documents | `select document_id from document where file_id = :F` |
| chunks | `… from document_chunk where file_id = :F` |
| vectors | `… from chunk_embedding where chunk_id in (chunks)`. They cascade on chunk delete. |
| evidence | `… from evidence where file_id = :F` |
| experiments / conditions | `… from experiment where table_file_id = :F` (+ `experiment_condition` by `experiment_id`) |
| graph edges | `… from knowledge_relation where evidence_id in (evidence)` |
| graph entities | entities whose `evidence_ids` intersect that set |
| derived images | `… from image_asset where parent_file_id = :F` |
| cache entries | everything with `knowledge_version` older than the publication that removes `F`. CAG invalidation is by version, not per row. |
| analyses citing it | `analysis_result` payloads whose interpretation cites one of those evidence IDs |

After the change, run `ingest` → a new `corpus-<hash>` is published → consumers invalidate by version (E2-5).

## 4. Administrator corrections

Corrections never overwrite originals:
- the original stays in the source row (e.g. `value_numeric`, `unit_original`, `excerpt`);
- the correction is a separate record:
  - a `manual` evidence row (`extraction_method = manual`, `review_status = human_verified`) that supersedes the machine one, or
  - for metadata, an `audit_event` with before/after.

`review_status` moves from `machine_extracted` to `human_verified` or `rejected`. Every change writes `audit_event` (actor, action, before, after, request_id). The admin endpoints that perform corrections are B3 (Belal and Anas); this is the storage contract they must follow.

## 5. Data acquired or changed while offline, and after sync (2H)

- **Uploads while offline** (images, future videos) are normal local records. Their provenance chain is complete, because nothing in it needs the network.
- **Ingestion while offline** can only use files already mirrored. The resulting `corpus-<hash>` is published locally, and answers show it.
- **On reconnection,** new remote data comes in through the normal Acquire stage, so it gets new files, new hashes and a new corpus version. No local record is rewritten by sync. The sync outcome is recorded per [E2-10 §6](OFFLINE_DATA_AND_SYNC.md).

## Known limitations
- The admin correction endpoints don't exist yet (B3). The storage rules are defined; their enforcement starts with that work.
- Graph lineage applies only once D2 writes edges.

## Changelog
- 1.0.0 (2026-10-12): first version; DSI lineage re-verified and loaded.
