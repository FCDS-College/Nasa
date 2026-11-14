# Data dictionary

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Anas (E2) | In review (peer sign-off: Eman E1) | 2.1.0 | 2026-11-12 | M8, MVP §9, E2-3 | `apps/api/flame_api/models.py`, `apps/api/migrations/versions/0001`–`0009` |

Every table in the database is listed here. §4 is **generated** from the SQLAlchemy metadata (the generator script is quoted in §4). §5 covers the two raw-SQL tables from migration `0003`. Field definitions for the source registry CSV are in [E2-1](SOURCE_REGISTRY.md).

Verified on 2026-10-11: a fresh `alembic upgrade head` on PostgreSQL 16 + pgvector creates exactly these 21 tables (20 data tables plus `alembic_version`):

```text
alembic_version, analysis_result, audit_event, cache_entry, chunk_embedding, dataset, document, document_chunk, evidence,
experiment, experiment_condition, file_record, image_asset, ingestion_run, knowledge_entity, knowledge_publication,
knowledge_relation, memory, model, source, vector_index_manifest
```

## 1. Migrations

| Migration | Creates / changes |
|---|---|
| `0001_initial` | `CREATE EXTENSION vector`; `Base.metadata.create_all` (all ORM tables *as defined in the running code*, see note); GIN full-text index `ix_document_chunk_full_text` on `document_chunk.text` |
| `0002_file_size_bigint` | `file_record.size_bytes` → BIGINT |
| `0003_vector_index` | `chunk_embedding`, `vector_index_manifest` (PostgreSQL only) |
| `0004_phase2_tables` | `knowledge_entity`, `knowledge_relation`, `memory`, `cache_entry`, `model`, `dataset`, `image_asset`, `audit_event`, `knowledge_publication`; `file_record.status` (default `active`, indexed) and `file_record.quarantine_reason`. Create-if-missing, because on a fresh database `0001` already built them. |
| `0005_api_clients` | `api_client` (per-client API keys: `client_id`, unique `name`, unique sha256 `key_hash`, `scopes`, `created_at`, `last_used_at`, `revoked_at`); keys are created with `python -m flame_api.clients` |
| `0006_experiment_ingested_at` | `experiment.ingested_at` (TIMESTAMPTZ, nullable), create-if-missing; backfilled from the latest non-quarantine `ingestion_run.finished_at` of the experiment's table file, else that file's `retrieved_at`. Rows with neither stay NULL. Chains after `0005_api_clients`. |
| `0007_chunk_search_tsv` | PostgreSQL only: `document_chunk.search_tsv` (TSVECTOR, `GENERATED ALWAYS AS (to_tsvector('english', text)) STORED`) with GIN index `ix_document_chunk_search_tsv`; drops `ix_document_chunk_full_text` from 0001. Not in the ORM model, so SQLite test databases do not have it |
| `0008_api_client_owner` | `api_client.owner` (VARCHAR(128), nullable), add-if-missing: the person accountable for a key; required for `admin` keys (ADR-009 step 2). Existing clients keep their scopes and get no `admin`. |
| `0009_video_checkpoints` | `analysis_result.cancel_requested_at` (TIMESTAMPTZ, nullable) and table `video_checkpoint_frame` (PK `analysis_id` + `frame_index`, FK → `analysis_result` ON DELETE CASCADE; `video_id`, `job_digest`, `row`, `created_at`), each create-if-missing (ADR-008). |
| `0010_nlp_record` | table `nlp_record` (PK `record_id`; `record_type`, `text`, `normalized`, `document_id`, `document_version`, `page`, `char_start`, `char_end`, `chunk_id`, `extractor`, `extractor_version`, `method`, `confidence`, `review_status` (`machine_extracted`, `human_verified`, `rejected`, `superseded`), `payload`, timestamps), create-if-missing (D1). Offsets refer to `document_chunk.text`. Records are candidates: a changed chunk or a new extractor version marks old rows `superseded`, never edits them. |
| `0011_chunk_window_embedding` | PostgreSQL + pgvector only, create-if-missing: table `chunk_window_embedding` (PK `window_id` = `chunk_id#w<ordinal>`; `chunk_id` FK → `document_chunk` ON DELETE CASCADE, `ordinal`, `char_start`, `char_end` (offsets into `document_chunk.text`), `text_sha` (to detect a changed page), `model`, `embedding vector(384)`), btree on `chunk_id`, HNSW cosine on `embedding`. Filled by `python -m flame_api.vector_index build-windows`; used only when `FLAME_DENSE_GRANULARITY=window`. |
| `0012_chunk_search_tsv_keep` | PostgreSQL only, create-if-missing: text search dictionary `flame_stem` (snowball English, no stopwords), configuration `flame_english`, generated column `document_chunk.search_tsv_keep` (`to_tsvector('flame_english', text)`) and a GIN index. Read only by `FLAME_LEXICAL_MODE=or_idf`; it makes `He` (helium) searchable. Downgrade drops all four. |

**Note.** `0001` builds from the live models. A brand-new database therefore gets the newest schema at `0001`, and later migrations must be idempotent, as `0004` is. An existing database gets the columns from `0004`. Both paths were verified to produce identical schemas (L-8 §2).

## 2. Conventions

- **IDs.**
  - ULIDs (26 chars, Crockford base32) everywhere. `stable_ulid(text)` is used when the ID must survive re-ingestion (derived from SHA-256 of the input key, `flame_api/ids.py`). `new_ulid()` is used for events.
  - Files are `sha256:<first 16 hex>` of their bytes.
  - Chunks are `<sha256[:16]>:v1:<page>` or `…:v1:s<section>`.
  - Models are `<runtime>:<name>`.

  The full table of ID inputs is in [L-5 §1](../architecture/index-sync-contract.md).
- **Nulls.** `null` means not present or not established. Never use 0 or `""` for missing. The registry CSV's literal `null` is decoded to SQL NULL (E2-1).
- **Times.** `TIMESTAMP WITH TIME ZONE`, UTC, RFC 3339 with `Z` in the API.
- **JSON.** JSONB on PostgreSQL; JSON on SQLite in tests.

## 3. Reported vs derived values; units

`experiment_condition` keeps both the source's value and its normalization:

| Column | Meaning |
|---|---|
| `value_numeric`, `value_text` | the value **as reported**. A number when it parses cleanly; otherwise text such as `"<5"` or `"~20"`, never coerced |
| `unit_original` | the unit as written in the source header |
| `value_si`, `unit_si` | derived SI value (`ingest.convert_to_si`: mmHg→Pa, cm/s→m/s, mg/s→kg/s, mm/cm→m, %O₂→fraction). Null when the unit is unknown, which blocks numeric comparison |
| `origin` | `reported` (from the source) or `derived` |

Evidence rows record `extraction_method`: `verbatim_text`, `ocr`, `table_parse`, `cv_pipeline` or `manual`. Measurements from CV are labelled `measured` (pixel space) or `estimated` (scale-derived). No column anywhere holds a temperature derived from image colour.

## 4. Tables (generated)

Generated with `python docs/tools/render_data_dictionary_tables.py`, which walks `flame_api.models.Base.metadata.sorted_tables` and compiles each type for the PostgreSQL dialect. Tables appear in dependency order.

### `api_client`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `client_id` | VARCHAR(26) | no | PK |
| `name` | VARCHAR(64) | no |  |
| `key_hash` | VARCHAR(64) | no |  |
| `scopes` | JSONB | no |  |
| `owner` | VARCHAR(128) | yes |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `last_used_at` | TIMESTAMP WITH TIME ZONE | yes |  |
| `revoked_at` | TIMESTAMP WITH TIME ZONE | yes |  |
Unique: `None` (name); `None` (key_hash).

### `audit_event`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `event_id` | VARCHAR(26) | no | PK |
| `occurred_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `actor` | VARCHAR(128) | no |  |
| `action` | VARCHAR(64) | no |  |
| `target_type` | VARCHAR(48) | no |  |
| `target_id` | TEXT | yes |  |
| `before` | JSONB | yes |  |
| `after` | JSONB | yes |  |
| `request_id` | VARCHAR(64) | yes |  |

Indexes: `ix_audit_event_action` (action); `ix_audit_event_occurred_at` (occurred_at).

### `cache_entry`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `cache_key` | VARCHAR(128) | no | PK |
| `kind` | VARCHAR(32) | no |  |
| `knowledge_version` | TEXT | yes |  |
| `dependencies` | JSONB | no |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `expires_at` | TIMESTAMP WITH TIME ZONE | yes |  |
| `invalidated_at` | TIMESTAMP WITH TIME ZONE | yes |  |
| `hit_count` | INTEGER | no | default `0` |

Indexes: `ix_cache_entry_kind` (kind); `ix_cache_entry_knowledge_version` (knowledge_version).

### `knowledge_publication`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `publication_id` | VARCHAR(26) | no | PK |
| `knowledge_version` | TEXT | no |  |
| `previous_version` | TEXT | yes |  |
| `trigger` | VARCHAR(32) | no |  |
| `published_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `payload` | JSONB | no |  |

Indexes: `ix_knowledge_publication_published_at` (published_at).
Unique: `None` (knowledge_version).

### `memory`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `memory_id` | VARCHAR(26) | no | PK |
| `scope` | VARCHAR(16) | no |  |
| `actor` | VARCHAR(128) | no |  |
| `conversation_id` | VARCHAR(128) | yes |  |
| `content` | TEXT | no |  |
| `origin` | VARCHAR(32) | no |  |
| `confidence` | FLOAT | yes |  |
| `provenance` | JSONB | no |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `expires_at` | TIMESTAMP WITH TIME ZONE | yes |  |
| `superseded_by` | VARCHAR(26) | yes | FK → `memory.memory_id` |

Indexes: `ix_memory_conversation_id` (conversation_id); `ix_memory_expires_at` (expires_at); `ix_memory_scope` (scope).

### `model`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `model_id` | VARCHAR(128) | no | PK |
| `capability` | VARCHAR(32) | no |  |
| `provider` | VARCHAR(48) | no |  |
| `runtime` | VARCHAR(48) | no |  |
| `name` | TEXT | no |  |
| `version` | TEXT | yes |  |
| `quantization` | TEXT | yes |  |
| `license` | TEXT | yes |  |
| `source_url` | TEXT | yes |  |
| `sha256` | VARCHAR(64) | yes |  |
| `size_bytes` | BIGINT | yes |  |
| `locality` | VARCHAR(16) | no |  |
| `context_window` | INTEGER | yes |  |
| `status` | VARCHAR(16) | no | default `candidate` |
| `model_card` | TEXT | yes |  |
| `payload` | JSONB | no |  |
| `registered_at` | TIMESTAMP WITH TIME ZONE | no |  |

Indexes: `ix_model_capability` (capability).

### `source`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `source_id` | VARCHAR(64) | no | PK |
| `title` | TEXT | no |  |
| `short_name` | TEXT | yes |  |
| `repository` | TEXT | no |  |
| `persistent_identifier` | TEXT | yes |  |
| `license` | TEXT | yes |  |
| `access_url` | TEXT | no |  |
| `domain` | VARCHAR(32) | no | default `combustion` |

Indexes: `ix_source_domain` (domain).

### `dataset`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `dataset_id` | VARCHAR(26) | no | PK |
| `name` | TEXT | no |  |
| `version` | VARCHAR(32) | no |  |
| `kind` | VARCHAR(32) | no |  |
| `source_id` | VARCHAR(64) | yes | FK → `source.source_id` |
| `split` | VARCHAR(16) | yes |  |
| `sha256` | VARCHAR(64) | yes |  |
| `item_count` | INTEGER | yes |  |
| `license` | TEXT | yes |  |
| `path` | TEXT | yes |  |
| `payload` | JSONB | no |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

Indexes: `ix_dataset_source_id` (source_id).
Unique: `uq_dataset_name_version` (name, version).

### `file_record`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `file_id` | VARCHAR(80) | no | PK |
| `source_id` | VARCHAR(64) | no | FK → `source.source_id` |
| `sha256` | VARCHAR(64) | no |  |
| `original_filename` | TEXT | no |  |
| `media_type` | TEXT | no |  |
| `size_bytes` | BIGINT | no |  |
| `retrieved_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `canonical_source_url` | TEXT | yes |  |
| `is_original` | BOOLEAN | no | default `True` |
| `parent_file_id` | VARCHAR(80) | yes | FK → `file_record.file_id` |
| `local_path` | TEXT | yes |  |
| `status` | VARCHAR(16) | no | server default `active` |
| `quarantine_reason` | TEXT | yes |  |

Indexes: `ix_file_record_sha256` (sha256); `ix_file_record_source_id` (source_id); `ix_file_record_status` (status).

### `knowledge_entity`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `entity_id` | VARCHAR(26) | no | PK |
| `entity_type` | VARCHAR(48) | no |  |
| `canonical_name` | TEXT | no |  |
| `aliases` | JSONB | no |  |
| `properties` | JSONB | no |  |
| `source_id` | VARCHAR(64) | yes | FK → `source.source_id` |
| `evidence_ids` | JSONB | no |  |
| `review_status` | VARCHAR(16) | no | default `unreviewed` |
| `merged_into` | VARCHAR(26) | yes | FK → `knowledge_entity.entity_id` |
| `knowledge_version` | TEXT | yes |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | no |  |

Indexes: `ix_knowledge_entity_entity_type` (entity_type); `ix_knowledge_entity_source_id` (source_id).
Unique: `uq_knowledge_entity_type_name` (entity_type, canonical_name).

### `document`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `document_id` | VARCHAR(26) | no | PK |
| `source_id` | VARCHAR(64) | no | FK → `source.source_id` |
| `file_id` | VARCHAR(80) | no | FK → `file_record.file_id` |
| `title` | TEXT | no |  |
| `document_type` | VARCHAR(48) | no | default `other` |
| `identifier` | TEXT | yes |  |
| `persistent_identifier` | TEXT | yes |  |
| `page_count` | INTEGER | yes |  |
| `text_layer` | VARCHAR(24) | no | default `unknown` |
| `pages_without_text` | JSONB | no |  |
| `parser_version` | TEXT | yes |  |
| `ingested_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `knowledge_version` | TEXT | yes |  |
| `payload` | JSONB | no |  |

Indexes: `ix_document_file_id` (file_id); `ix_document_source_id` (source_id).

### `experiment`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `experiment_id` | VARCHAR(26) | no | PK |
| `source_id` | VARCHAR(64) | no | FK → `source.source_id` |
| `test_id` | TEXT | no |  |
| `investigation` | TEXT | yes |  |
| `gravity_regime` | VARCHAR(32) | no | default `unknown` |
| `fuel_or_material` | TEXT | yes |  |
| `table_file_id` | VARCHAR(80) | yes | FK → `file_record.file_id` |
| `searchable_text` | TEXT | no | default `` |
| `payload` | JSONB | no |  |
| `ingested_at` | TIMESTAMP WITH TIME ZONE | yes |  |

Indexes: `ix_experiment_source_id` (source_id).

### `image_asset`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `image_id` | VARCHAR(26) | no | PK |
| `file_id` | VARCHAR(80) | yes | FK → `file_record.file_id` |
| `parent_file_id` | VARCHAR(80) | yes | FK → `file_record.file_id` |
| `source_id` | VARCHAR(64) | yes | FK → `source.source_id` |
| `analysis_id` | VARCHAR(26) | yes |  |
| `sha256` | VARCHAR(64) | no |  |
| `media_type` | TEXT | no |  |
| `width` | INTEGER | yes |  |
| `height` | INTEGER | yes |  |
| `frame_index` | INTEGER | yes |  |
| `derivation` | TEXT | yes |  |
| `payload` | JSONB | no |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

Indexes: `ix_image_asset_analysis_id` (analysis_id); `ix_image_asset_file_id` (file_id); `ix_image_asset_parent_file_id` (parent_file_id); `ix_image_asset_sha256` (sha256); `ix_image_asset_source_id` (source_id).

### `ingestion_run`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `run_id` | VARCHAR(26) | no | PK |
| `source_id` | VARCHAR(64) | no | FK → `source.source_id` |
| `file_id` | VARCHAR(80) | no | FK → `file_record.file_id` |
| `transformation_id` | VARCHAR(80) | no |  |
| `input_sha256` | VARCHAR(64) | no |  |
| `started_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `finished_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `counts` | JSONB | no |  |

Indexes: `ix_ingestion_run_file_id` (file_id); `ix_ingestion_run_source_id` (source_id).
Unique: `uq_ingestion_file_transform` (file_id, transformation_id, input_sha256).

### `knowledge_relation`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `relation_id` | VARCHAR(26) | no | PK |
| `subject_id` | VARCHAR(26) | no | FK → `knowledge_entity.entity_id` ON DELETE CASCADE |
| `predicate` | VARCHAR(64) | no |  |
| `object_id` | VARCHAR(26) | no | FK → `knowledge_entity.entity_id` ON DELETE CASCADE |
| `evidence_id` | VARCHAR(26) | yes |  |
| `extraction_method` | VARCHAR(48) | no |  |
| `extractor_version` | TEXT | yes |  |
| `confidence` | FLOAT | yes |  |
| `review_status` | VARCHAR(16) | no | default `unreviewed` |
| `properties` | JSONB | no |  |
| `knowledge_version` | TEXT | yes |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

Indexes: `ix_knowledge_relation_evidence_id` (evidence_id); `ix_knowledge_relation_object_id` (object_id); `ix_knowledge_relation_predicate` (predicate); `ix_knowledge_relation_subject_id` (subject_id).
Unique: `uq_knowledge_relation_edge` (subject_id, predicate, object_id, evidence_id).

### `analysis_result`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `analysis_id` | VARCHAR(26) | no | PK |
| `status` | VARCHAR(16) | no |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `completed_at` | TIMESTAMP WITH TIME ZONE | yes |  |
| `experiment_id` | VARCHAR(26) | yes | FK → `experiment.experiment_id` |
| `image_sha256` | VARCHAR(64) | no |  |
| `original_filename` | TEXT | no |  |
| `pipeline_version` | TEXT | yes |  |
| `idempotency_key` | VARCHAR(128) | yes |  |
| `cancel_requested_at` | TIMESTAMP WITH TIME ZONE | yes |  |
| `payload` | JSONB | no |  |
| `artifacts` | JSONB | no |  |

Indexes: `ix_analysis_result_created_at` (created_at); `ix_analysis_result_experiment_id` (experiment_id); `ix_analysis_result_image_sha256` (image_sha256); `ix_analysis_result_status` (status).
Unique: `uq_analysis_idempotency_key` (idempotency_key).

### `document_chunk`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `chunk_id` | VARCHAR(80) | no | PK |
| `document_id` | VARCHAR(26) | no | FK → `document.document_id` ON DELETE CASCADE |
| `source_id` | VARCHAR(64) | no | FK → `source.source_id` |
| `file_id` | VARCHAR(80) | no | FK → `file_record.file_id` |
| `evidence_id` | VARCHAR(26) | no |  |
| `page` | INTEGER | yes |  |
| `section` | TEXT | yes |  |
| `text` | TEXT | no |  |
| `ingested_at` | TIMESTAMP WITH TIME ZONE | no |  |

PostgreSQL also has the generated column `search_tsv` (TSVECTOR, migration 0007), not mapped in the ORM.

`text` is the **indexed** text. For text-layer PDF pages (parser `pymupdf-pages-0.4.0` and later) it is normalised (`ai/rag/ingestion/normalize.py`, version in `document.payload.text_normalization`); the verbatim page text is `evidence.excerpt`, which is what a citation points at. After upgrading, re-run `python -m flame_api.ingest` and `python -m flame_api.vector_index build` so chunks are re-indexed and re-embedded.

Indexes: `ix_document_chunk_document_id` (document_id); `ix_document_chunk_evidence_id` (evidence_id); `ix_document_chunk_file_id` (file_id); `ix_document_chunk_source_id` (source_id); `ix_document_chunk_source_page` (source_id, page).

### `evidence`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `evidence_id` | VARCHAR(26) | no | PK |
| `source_id` | VARCHAR(64) | yes | FK → `source.source_id` |
| `file_id` | VARCHAR(80) | yes | FK → `file_record.file_id` |
| `document_id` | VARCHAR(26) | yes | FK → `document.document_id` |
| `experiment_id` | VARCHAR(26) | yes | FK → `experiment.experiment_id` |
| `analysis_id` | VARCHAR(26) | yes |  |
| `kind` | VARCHAR(32) | no |  |
| `origin` | VARCHAR(32) | no |  |
| `excerpt` | TEXT | yes |  |
| `locator` | JSONB | yes |  |
| `payload` | JSONB | no |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

Indexes: `ix_evidence_analysis_id` (analysis_id); `ix_evidence_document_id` (document_id); `ix_evidence_experiment_id` (experiment_id); `ix_evidence_file_id` (file_id); `ix_evidence_source_id` (source_id).

### `experiment_condition`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `condition_id` | VARCHAR(26) | no | PK |
| `experiment_id` | VARCHAR(26) | no | FK → `experiment.experiment_id` ON DELETE CASCADE |
| `variable` | TEXT | no |  |
| `value_numeric` | FLOAT | yes |  |
| `value_text` | TEXT | yes |  |
| `unit_original` | TEXT | yes |  |
| `value_si` | FLOAT | yes |  |
| `unit_si` | TEXT | yes |  |
| `origin` | VARCHAR(32) | no |  |
| `evidence_id` | VARCHAR(26) | no |  |

Indexes: `ix_experiment_condition_evidence_id` (evidence_id); `ix_experiment_condition_experiment_id` (experiment_id).

### `video_checkpoint_frame`

| Column | Type (PostgreSQL) | Null | Key / default |
|---|---|---|---|
| `analysis_id` | VARCHAR(26) | no | PK, FK → `analysis_result.analysis_id` ON DELETE CASCADE |
| `frame_index` | INTEGER | no | PK |
| `video_id` | VARCHAR(64) | no |  |
| `job_digest` | VARCHAR(64) | no |  |
| `row` | JSONB | no |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

## 5. Raw-SQL tables (migration `0003`, PostgreSQL only)

### `chunk_embedding`

| Column | Type | Null | Key |
|---|---|---|---|
| `chunk_id` | VARCHAR(80) | no | PK, FK → `document_chunk.chunk_id` ON DELETE CASCADE |
| `model` | TEXT | no | embedding model name (`BAAI/bge-small-en-v1.5`) |
| `embedding` | vector(384) | no | HNSW index `ix_chunk_embedding_hnsw` (cosine) |

### `vector_index_manifest`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK, CHECK (id = 1): single row |
| `model` | TEXT | no | |
| `dim` | INTEGER | no | |
| `row_count` | INTEGER | no | |
| `knowledge_version` | TEXT | no | e.g. `bge-small-en-v1.5-37-20261011` |
| `built_at` | TIMESTAMPTZ | no | |

`knowledge_publication.knowledge_version` is also unique (a column-level `unique=True`, which the §4 generator doesn't list).

## 6. Synthetic example rows

All values are illustrative. Where real hashes and IDs appear, they are from the committed NTRS PDF `20000034017.pdf`.

| Table | Example (JSON, abbreviated) |
|---|---|
| `source` | `{"source_id":"FF-NTRS-20000034017","title":"Testing and Selection of Fire-Resistant Materials for Spacecraft Use","short_name":"NASA/TM-2000-209773","repository":"NASA NTRS","persistent_identifier":null,"license":null,"access_url":"https://ntrs.nasa.gov/citations/20000034017","domain":"combustion"}` |
| `file_record` | `{"file_id":"sha256:dc531270ffb646b2","source_id":"FF-NTRS-20000034017","sha256":"dc531270…520d","original_filename":"20000034017.pdf","media_type":"application/pdf","size_bytes":1297410,"retrieved_at":"2026-10-03T21:28:17Z","is_original":true,"parent_file_id":null,"local_path":"…/docs/research/20000034017.pdf","status":"active","quarantine_reason":null}` |
| `document` | `{"document_id":"1720K40PE3PPD1AM5ZFFV1P1CT","title":"Testing and Selection of Fire-Resistant Materials for Spacecraft Use","document_type":"technical_report","identifier":"NASA/TM-2000-209773","page_count":20,"text_layer":"full","pages_without_text":[],"parser_version":"pymupdf-pages-0.2.0","payload":{"ocr":{"status":"not_needed","page_confidence":{}}}}` |
| `document_chunk` | `{"chunk_id":"dc531270ffb646b2:v1:17","document_id":"1720K…","evidence_id":"2S9T0Z9K8NWWR8Y94TVQ9MKDGV","page":17,"section":null,"text":"…"}` |
| `evidence` | `{"evidence_id":"2S9T0Z9K8NWWR8Y94TVQ9MKDGV","kind":"document_passage","origin":"source_evidence","locator":{"type":"page","page":17,"label":"p. 17"},"payload":{"extraction_method":"verbatim_text","review_status":"machine_extracted","transformation_id":"pymupdf-pages-0.2.0"}}` |
| `experiment` | `{"experiment_id":"01J9Z3N1W8X2Y4Z6A8C0E2G4J6","source_id":"FF-PSI-69","test_id":"FLEX-001","investigation":"FLEX","gravity_regime":"microgravity","fuel_or_material":"n-heptane"}` |
| `experiment_condition` | `{"variable":"pressure","value_numeric":760,"unit_original":"mmHg","value_si":101325.0,"unit_si":"Pa","origin":"reported","evidence_id":"…"}` |
| `analysis_result` | `{"analysis_id":"01J9Z3Q9D3F5H7K9N1R3T5W7Y9","status":"completed","image_sha256":"4f1c…","pipeline_version":"cv-opencv-v1.2.0-auto","idempotency_key":"upload-42"}` |
| `ingestion_run` | `{"run_id":"…","file_id":"sha256:dc531270ffb646b2","transformation_id":"pymupdf-pages-0.2.0","input_sha256":"dc531270…","counts":{"pages":20,"chunks":20,"ocr_pages":0,"ocr_low_confidence":0,"skipped":0}}` |
| `knowledge_entity` | `{"entity_id":"stable_ulid('fuel:n-heptane')","entity_type":"fuel","canonical_name":"n-heptane","aliases":["heptane","C7H16"],"evidence_ids":["…"],"review_status":"unreviewed"}` |
| `knowledge_relation` | `{"subject_id":"<experiment entity>","predicate":"uses_fuel","object_id":"<n-heptane>","evidence_id":"…","extraction_method":"table_parse","extractor_version":"psi-tables-0.2.0","confidence":1.0,"review_status":"unreviewed"}` |
| `memory` | `{"scope":"session","actor":"web","conversation_id":"c-1","content":"User is comparing FLEX droplets at 1 atm","origin":"user_statement","confidence":null,"expires_at":"2026-10-13T00:00:00Z","superseded_by":null}` |
| `cache_entry` | `{"cache_key":"resp:sha256(q+filters+prompt_v)","kind":"response","knowledge_version":"bge-small-en-v1.5-37-20261011","dependencies":{"prompt_version":"chat-v1","model":"ollama:qwen2.5:3b-instruct-q4_K_M"}}` |
| `model` | `{"model_id":"fastembed:BAAI/bge-small-en-v1.5","capability":"embeddings","runtime":"fastembed","sha256":"51f1bd0a…2431","size_bytes":66465124,"locality":"local","status":"approved"}` |
| `dataset` | `{"name":"rag_gold","version":"1.0.0","kind":"evaluation","split":"holdout","sha256":"…","item_count":120,"path":"datasets/evaluation/rag_gold.jsonl"}` |
| `image_asset` | `{"image_id":"stable_ulid('image-asset:00a9fbef…')","parent_file_id":"sha256:0473cfa2f03e287e","source_id":"FF-PSI-DSI","sha256":"00a9fbef…e5c1","media_type":"image/png","width":1024,"height":1024,"frame_index":0,"derivation":"lossless-png","payload":{"member":"S1 activity 4/DA_TC_DSI_SEQ2_ACTIVITE04_HR1.zip!/DSI_SEQ2_ACTIVITE04_HR1_1018759522_1.bmp"}}` |
| `audit_event` | `{"actor":"write-token","action":"ai.mode.changed","target_type":"ai_execution_mode","before":{"mode":"local_first"},"after":{"mode":"offline_only"},"request_id":"req_…"}` |
| `knowledge_publication` | `{"knowledge_version":"bge-small-en-v1.5-37-20261011","previous_version":"corpus-12a92c60110f","trigger":"vector_index_build","payload":{"counts":{"chunk_embeddings":37,"embedded":37}}}` |
| `chunk_embedding` | `{"chunk_id":"dc531270ffb646b2:v1:17","model":"BAAI/bge-small-en-v1.5","embedding":"[0.0123,…] (384)"}` |
| `vector_index_manifest` | `{"id":1,"model":"BAAI/bge-small-en-v1.5","dim":384,"row_count":37,"knowledge_version":"bge-small-en-v1.5-37-20261011"}` |

## 7. Registry and manifest files (not tables)

- `datasets/registry/source_registry.csv`: see [E2-1](SOURCE_REGISTRY.md).
- `datasets/metadata/files.jsonl`: one line per original file. Fields: `file_id`, `source_id`, `original_filename`, `remote_object_key`, `canonical_source_url`, `local_path` (relative to `datasets/`), `content_type`, `size_bytes`, `listing_size_bytes`, `sha256`, `retrieval_timestamp_utc`, `remote_last_modified_utc`, `is_original`, `parent_file_id`. 124 lines (`wc -l`, 2026-10-12).
- `datasets/checksums/sha256.txt`: `sha256sum -c` format, 124 lines.
- `datasets/samples/cv/manifest.jsonl`: derived CV samples with `parent_file_id`. 185 lines, of which 182 are images.
- `ai/routing/model_manifest.json`: the H-3 source for the `model` table.

## Known limitations
- `memory`, `cache_entry` and `dataset` have **no writer yet**. Their owners' work (M4/M5 Eman, M11 Ziad) fills them. The graph tables are written by `flame_api.knowledge_graph` (ADR-007, E2-6 §0).
- §6 rows are synthetic, apart from the IDs and hashes quoted from committed files.

## Changelog
- 2.1.0 (2026-11-12): §1 adds `0005`–`0009`; §4 regenerated (adds `api_client`, `api_client.owner`, `analysis_result.cancel_requested_at`, `video_checkpoint_frame`).
- 2.0.0 (2026-10-12): rewritten for E2-3. Covers migrations `0002`–`0004`, every table, and generated listings. The Day 1 field lists moved to E2-1 (registry) and to §7.
- 1.0.0 (Day 1): canonical field lists.
