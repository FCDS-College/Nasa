# Document and context schema

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Eman | Draft | 0.2.0 | 2026-10-14 | M2 (audit fix) | `ai/rag/ingestion/`, `ai/rag/dto.py`, `ai/rag/context/` |

Checked against the code at commit `5888580` (branch `Eman`). All structures are plain Python dicts unless a Pydantic model is named. **Planned** = not in code.

## 1. Document (`create_document`)

| Field | Status |
|---|---|
| `document_id`, `title`, `source`, `source_type`, `text`, `metadata` | Implemented |
| `version` | Implemented as a string, default `"1"` |
| `publication_date`, `retrieval_date`, `license`, `scientific_domain` | **Not fields.** They can be put in `metadata`; nothing does today. `PDFDocumentLoader` sets `metadata.domain = "combustion"` (hard-coded), `page` and `locator`. |

`PDFDocumentLoader` creates **one document per PDF page**: id `<stem>_page_<n>`, version `"1"`.

## 2. Chunk (`SimpleChunker.chunk`)

| Field | Status |
|---|---|
| `chunk_id` = `<document_id>_chunk_<n>`, `document_id`, `document_version`, `text`, `chunk_index`, `metadata` | Implemented. `metadata` is the document's dict, shared by reference. |
| `embedding_id` | **Not a field.** Embeddings live in a parallel list inside `VectorSearchService` (`add_documents(chunks, embeddings)`). |
| `citation_metadata` | **Not a field.** Citations are built later by `CitationManager`. |

Relationships: `chunk_id -> document_id -> document_version` is implemented. Previous/next chunk links are **not** implemented. Page, section or row positions are carried by an optional `locator` in `metadata` (`Locator`: `page`, `section`, `row`).

## 3. Retrieved evidence (`ai/rag/dto.py`)

`RetrievedChunk`: `chunk_id`, `document_id`, `document_version`, `text`, `score`, `locator`, `metadata`. `EvidenceBundle`: `query`, `evidence`, `context`, `citations`, `results`, `status`. These Pydantic models are the evidence schema used by the composer.

## 4. Embedding metadata

Not stored per chunk. The default model is `sentence-transformers/all-MiniLM-L6-v2` (`SentenceTransformerEmbeddingService`). `FlameRAGService.versions()` records the embedding model **name** per request; model version and vector dimension are not recorded (**Planned**).

## 5. Citation metadata and context item

- Citation fields: see `citation-provenance.md`.
- Context item (`ContextBuilder` `sources` entries): `chunk_id`, `document_id`, `document_version`, `text`, `metadata`, optional `locator`. The relevance score is not in the item; it is `RetrievedChunk.score` in the bundle.

## 6. Relation to the API's stored chunks

The earlier text assumed the NASA data format was unknown. The API now ingests real files into Postgres (`apps/api/flame_api/ingest.py`, `models.py`). Its `DocumentChunk` rows differ from the library chunks:

| Library chunk | API `DocumentChunk` |
|---|---|
| `chunk_id = <document_id>_chunk_<n>` | `chunk_id = <sha256[:16]>:v1:<page>` (page-level) |
| `document_id`, `document_version` | `source_id`, document relation; version embedded in the id |
| `locator` in metadata (`page`, `section`, `row`) | `page`, `section`, `evidence_id`; API locator also has `type`, `frame_index`, `label` |

A mapping layer between the two is **Planned** (see the ADR in `retrieval-pipeline.md`). Until it exists, citations from the library cannot be resolved to API `evidence_id` values.

## 7. Evidence

| Claim | Test command | Result |
|---|---|---|
| Document, chunking and ingestion behaviour | `python -m pytest -q tests/unit/test_ingestion.py tests/unit/test_chunker.py tests/unit/test_ingestion_pipeline.py tests/unit/test_dto.py` | Part of Eman's full run `python -m pytest -q tests/unit` at `34c9849`: **83 passed** (2026-10-13). |

## 8. Known limitations

- The `"combustion"` domain is hard-coded in the PDF loader.
- Chunks share their metadata dict by reference; editing one changes all.
- No source path/URL, license or dates reach chunks.
- Library chunk ids and API chunk ids are different schemes.

## 9. Changelog

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-10-14 | Rewritten to match the code at `5888580`; real-data mapping noted. |
| 0.1.0 | Day 1 | Initial logical schema (not verified against code). |

## 10. ملخص بالعربي

الـ document والـ chunk في الكود dicts بسيطة. حقول زي license وpublication_date مش موجودة كـ fields، والـ embedding بيتخزّن لوحده مش مع الـ chunk. وـ chunk_id في الـ API (`sha256:v1:page`) مختلف عن بتاعنا (`doc_chunk_n`)، فمحتاجين mapping layer (Planned).
