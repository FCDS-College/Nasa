# knowledge/

Source registry, ingestion, parsing, provenance and the knowledge graph. **Owner:** Engineer 2.

| Folder | Status | What goes here |
|---|---|---|
| `ingestion/` | **active** | Scripts that mirror NASA sources into `datasets/raw/` and record checksums and provenance |
| `parsing/`, `chunking/`, `embeddings/`, `provenance/`, `graph/` | planned | MVP plan §8 pipeline stages |

Ingestion rules come from `docs/data/DAY1_DATA_ACQUISITION.md`: originals are immutable, every file gets a SHA-256, and every derived artefact keeps a `parent_file_id`.
