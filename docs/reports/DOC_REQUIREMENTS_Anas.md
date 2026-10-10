# Documentation Requirements: Anas (Engineer 2, Scientific Data / Knowledge Base)

| | |
|---|---|
| **Phase** | Phase 2: Advanced Scientific Intelligence Platform |
| **Issued** | 2026-10-10 by the Lead (Anas) |
| **Your branch** | `main` (task branches from `main` for larger changes) |
| **Basis** | [Phase 2 Plan](../plan/PHASE2_PLAN.md): §2 carry-over items **M8** (missing §9 tables), **M9** (ingestion completeness) and **M4** (knowledge-version publication event); **B2/B3** (admin data operations), **C4** (source quality, with Ziad) and **D2/D3/D6** (graph entity registry and consistency); MVP Plan §7, §8, §9 |
| **Reviewers** | Lead review covers the API-facing schemas. Eman (E1) reviews everything consumed by retrieval, caching or the graph. Ziad (E5) reviews quality scoring. Belal (E4) reviews admin data operations. |

> The Lead and Engineer 2 roles are held by the same person. To keep the review real, each E2 document needs **at least one peer sign-off** (Eman or Ziad) in addition to the Lead's self-review.

---

## 1. Why this matters

Every answer, measurement and ranking traces back to the corpus. If sources, versions and lineage aren't documented, provenance can't be checked and Phase 2's knowledge ranking has nothing trustworthy to rank. The audit on 2026-10-10 found these gaps:
- No OCR fallback, no HTML/JSON parsers and no quarantine.
- The 3 NTRS PDFs in `docs/research/` are not registered, and NIST WebBook is not registered.
- The §9 tables `KnowledgeEntity`, `KnowledgeRelation`, `Memory`, `CacheEntry`, `Model`, `Dataset` and `ImageAsset` are missing.
- From the 2026-10-06 notes, to re-verify: derived DSI frames have no `parent_file_id`, and the registry CSV doesn't validate against its schema.

## 2. Rules for every document you write

1. **Location and format:** Markdown at the path given in §3, in English.
2. **Header block:** start every document with the table below.

   | Owner | Status | Version | Last updated | Plan items | Code paths |
   |---|---|---|---|---|---|
   | Anas (E2) | Draft / In review / Approved | 0.1.0 | YYYY-MM-DD | e.g. M9, D6 | e.g. `apps/api/flame_api/ingest.py` |

3. **Evidence over claims:** counts (documents, pages, chunks, experiments, evidence rows) come from a command or query, and the document quotes that command. Every source claim links to its registry row and its checksum file.
4. **Docs ship with code:** a schema migration, a parser change or a new source updates the matching document in the same commit, including `DATA_DICTIONARY.md`.
5. **Versions:** parser, OCR, chunker, table-parser and knowledge versions are named wherever data is described. Each document ends with a **Changelog** section.
6. **Licensing and access:** every source records its license or terms, access method and access date. Restricted content is never scraped (MVP §7).
7. **Local-only data:** anything that exists only on a local disk (git-ignored mirrors) is stated as such, with its size and how to re-acquire it.
8. **Safety:** no credentials. Example rows use synthetic or redacted values.
9. **Limitations:** every document ends with **Known limitations**.

## 3. Required documents

| ID | Document | Path | Covers | Due (Phase 2 week) |
|---|---|---|---|---|
| E2-1 | Source registry guide | `docs/data/SOURCE_REGISTRY.md` | M9, B2 | Week 2 |
| E2-2 | Ingestion pipeline specification | `docs/data/INGESTION_PIPELINE.md` | M9, B2, D6 | Week 3 |
| E2-3 | Data dictionary (update) | `docs/data/DATA_DICTIONARY.md` | M8, §9 | Week 3, then on every migration |
| E2-4 | Provenance and lineage | `docs/data/PROVENANCE.md` | M9, B3, D6 | Week 3 |
| E2-5 | Knowledge versioning and publication (with Eman) | `docs/data/KNOWLEDGE_VERSIONING.md` | M4, D6 | Week 3 |
| E2-6 | Knowledge graph schema and entity registry | `docs/data/KNOWLEDGE_GRAPH_SCHEMA.md` | D2, D3, D6 | Week 5 |
| E2-7 | Source and dataset quality scoring (with Ziad) | `docs/data/DATA_QUALITY_SCORING.md` | C4 | Week 5 |
| E2-8 | Admin data operations guide | `docs/data/ADMIN_DATA_OPERATIONS.md` | B2, B3, B4 | Week 7 |
| E2-9 | Per-source dataset reports | `docs/data/<SOURCE>_DATASET_REPORT.md` | M9 | When each new source is added (NTRS, NIST first) |

## 4. Required contents

### E2-1 Source registry guide
- Every field of `datasets/registry/source_registry.csv` and `source_registry.schema.json`: meaning, allowed values and an example.
- How to add a source: the review checklist (license, relevance, duplicates, trust tier, priority P0/P1/P2) and the **schema validation command** (which must pass).
- The current registry table with status per source, including NTRS and NIST once registered.
- Array and null encoding rules, which fixes the `;`-array and literal `"null"` issue.

### E2-2 Ingestion pipeline specification
- Stages raw → parsed → normalized → indexed (MVP §5.5, §8), with the module or function for each.
- Parser adapters (PDF, HTML, JSON, OCR) with their versions, when OCR triggers, how OCR confidence is recorded, and how low-confidence pages are flagged.
- **Quarantine:** what is rejected, where it goes, and how it is reviewed.
- **Idempotency and retry:** stable IDs (`stable_ulid` inputs), what a retry does and why it creates no duplicates (B2).
- Replay/run manifest: `ingestion_run` fields and how to re-ingest reproducibly.
- How to run it locally and in Compose (`python -m flame_api.ingest`), with sample output counts.

### E2-3 Data dictionary
- Every table: columns, types, nullability, keys, indexes, ID scheme (ULID or content hash), and one synthetic example row.
- New tables from M8 (`KnowledgeEntity`, `KnowledgeRelation`, `Memory`, `CacheEntry`, `Model`, `Dataset`, `ImageAsset`) and the Phase 2 graph tables, each with the migration that created it.
- Reported vs derived value distinction, and units/unit-system fields for experiment conditions.

### E2-4 Provenance and lineage
- The full chain: answer or analysis → evidence → chunk/table row → document version → file checksum → source URL and access date.
- Derived artifacts (frames, masks, page images), the `parent_file_id` lineage, and the fix for DSI frames.
- **Correction and removal impact:** how to find every entity, edge, chunk, vector and cache entry affected when a source is corrected or removed (D6, B3).
- How administrator corrections are stored separately from original values, and how they are audited.

### E2-5 Knowledge versioning and publication
- What `knowledge_version` means, when it changes, and who triggers publication.
- The publication event: its payload schema, its consumers (Eman's CAG invalidation, vector and graph index sync), and its ordering guarantees.
- Rollback to a previous knowledge version.

### E2-6 Knowledge graph schema and entity registry
- Entity and relationship types actually used (a subset of Phase 2 D2), each with a definition, required properties and a synthetic example.
- Edge provenance fields: source evidence, extraction method, confidence semantics and review status.
- Entity resolution and merge rules; ID stability across PostgreSQL, the vector index and the graph.
- Consistency checks (orphans, duplicates, conflicting relations) and how often they run.
- The storage decision, recorded as an ADR with the Lead (D3).

### E2-7 Source and dataset quality scoring
For the C4 dimensions as applied to this corpus, give the signals per dimension, the computation, the inputs, a worked example per source, and the version. Link Ziad's `docs/evaluation/quality-rubrics.md` as the method authority.

### E2-8 Admin data operations guide
Step-by-step procedures for: registering a source, starting or retrying ingestion, inspecting failed files, reprocessing assets, correcting metadata, linking documents to experiments, approving records for indexing, merging entities, and rebuilding indexes. For each procedure, give the role required, the audit record created and how to roll it back.

### E2-9 Per-source dataset reports
Follow the `DSI_DATASET_REPORT.md` pattern for every new source: what the source is, its access method, file inventory with sizes and checksums, what was ingested and what was skipped (and why), and its scientific relevance and limitations.

## 5. Existing documents to fix

| File | Problem | Action |
|---|---|---|
| `docs/data/DATA_DICTIONARY.md` | Doesn't cover migrations `0002`/`0003` or the planned M8 tables | Bring it up to date as E2-3 |
| `docs/data/DAY1_DATA_ACQUISITION.md`, `P0_CANDIDATES.md`, `COMBUSTION_DATASET_ANALYSIS.md` | MVP-era working notes | Add a status line (current / superseded by …) at the top of each |
| `docs/data/CV_IMAGE_SOURCES.md` | Shared with Princess's CV datasets | Link it from E2-1 and from Princess's annotation protocol |
| `datasets/registry/source_registry.csv` | Fails schema validation (`;` arrays, literal `"null"`; per the 2026-10-06 notes, re-verify) | Fix it and document the validation command in E2-1 |
| `docs/research/*.pdf` (3 NTRS PDFs) | Unregistered and not ingested | Register, ingest and report them (E2-9) |
| `knowledge/README.md` | Doesn't describe the scripts' current role | Add a module map: `psi_download.py`, `record_provenance.py`, `make_cv_samples.py` |

## 6. Recurring documentation

- **Weekly note**, `docs/reports/WEEKLY_Anas_E2.md` (append a section each week): sources added, ingestion counts (from a query), schema changes, open data defects, and which documents changed.
- **Commit and PR description:** the documents updated, the migration ID, and the validation commands run.

## 7. Acceptance checklist (peer reviewer checks this before approving)

- [ ] Every document in §3 exists at its path, with the header block and a changelog.
- [ ] The registry validates against its schema, and the command is documented.
- [ ] Every table in the database appears in the data dictionary.
- [ ] Lineage can be followed from any evidence ID to the original source URL and checksum.
- [ ] The knowledge-version publication contract is signed off by Eman.
- [ ] Known limitations are stated in every document.
