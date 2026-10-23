# Citation and provenance

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Eman | Draft | 0.2.0 | 2026-10-14 | M2, M3 (audit fix) | `ai/rag/citations/`, `ai/rag/generation/composer.py`, `ai/rag/evaluation/metrics.py` |

Checked against the code at commit `5888580` (branch `Eman`). **Planned** = not in code.

## 1. Purpose

Every scientific claim in an answer must be traceable to retrieved evidence.

## 2. The provenance chain, as implemented

```text
Claim (text, label)  ->  answer citation C1  ->  chunk_id  ->  document_id + document_version  ->  locator (page / section / row)
```

The link to the **original source file** (path or URL) is missing from the chunk: `PDFDocumentLoader` stores `source` on the document, but `SimpleChunker` copies only `document_id`, `document_version`, `text`, `chunk_index` and `metadata` into each chunk, so the source path does not reach the citation. Resolving it today needs the document id (**Planned**: carry `source`/`source_url` into citation metadata).

## 3. Two kinds of citation

| Kind | Built by | Fields |
|---|---|---|
| Retrieval citation (`EvidenceBundle.citations`) | `CitationManager.create_citations` | `citation_id` (equal to `chunk_id`), `chunk_id`, `document_id`, `document_version`, `metadata`, `locator` (when present) |
| Answer citation (`GroundedAnswer.citations`) | `GroundedAnswerComposer.compose` | `citation_id` (`C1`, `C2`, ...), `chunk_id`, `document_id`, `document_version`, `locator` |

The earlier design listed `source`, `source_url` and a top-level `page`. They do not exist: the page is inside `locator` (`Locator` has `page`, `section`, `row`).

## 4. Claim-to-evidence mapping

Implemented as `Claim` (`ai/rag/generation/models.py`): `text`, `label`, `evidence_ids` (retrieved chunk ids) and `citation_ids` (`C1`...). The earlier `ClaimEvidence` structure with `claim_id` was not implemented.

## 5. Citation validation

| Design check | Status | How |
|---|---|---|
| Cited chunk exists | Implemented | Every cited id is looked up in the retrieved set; unknown ids are removed and listed in `dropped_citation_ids` with the warning `citations_not_in_retrieved_evidence_removed`. |
| Chunk belongs to the referenced document | Implicit | `document_id` and `document_version` are copied from the retrieved chunk, never taken from the model. |
| Document version exists | Implicit | Same reason. |
| Citation metadata valid | Type check only | Pydantic models; no semantic check. |
| Evidence was actually retrieved | Implemented | Same lookup. |
| Not fabricated or unrelated | **Partly** | Fabricated ids are removed. Whether the claim text is really supported by the cited chunk is **not checked** (**Planned**: entailment or NLP check, D1). |

Details and worked examples: `grounded-generation.md`.

## 6. Source versioning

Citations carry `document_version`. Today versions come from ingestion: `create_document` defaults to `"1"` and `PDFDocumentLoader` fixes `"1"`; the API builds chunk ids that include `v1`. Nothing bumps a version when a document changes (**Planned**; owned by the knowledge-versioning work of E2).

## 7. Missing evidence

Implemented policy: remove the unsupported claim. If other claims survive, status is `partially_supported`; if none survive, the answer abstains. The alternative in the earlier design (keep the claim but mark it unsupported) is **not implemented** in the composer.

## 8. Citation coverage

`citation_coverage(citations, relevant_chunks)` in `ai/rag/evaluation/metrics.py` is the fraction of the expected relevant chunks that appear in the citations. This differs from the earlier definition (supported claims / total claims); a claim-level coverage metric does **not** exist. The only dataset is synthetic (`EVALUATION_DATASET`, 4 questions over one repeated paragraph), so no meaningful coverage number exists yet; real numbers come from Ziad's harness (E1-10).

## 9. Evidence

| Claim | Test command | Result |
|---|---|---|
| Citation creation and validation | `python -m pytest -q tests/unit/test_citation_manager.py tests/unit/test_composer.py tests/unit/test_metrics.py` | Part of Eman's full run `python -m pytest -q tests/unit` at `34c9849`: **83 passed** (2026-10-13). |

## 10. Known limitations

- Claim text is not checked against the cited chunk.
- The original source path/URL is not in the citation.
- Two citation shapes exist (retrieval and answer); the API must decide which it exposes.
- Document versions are not bumped automatically.

## 11. Changelog

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-10-14 | Rewritten to match the code at `5888580`. |
| 0.1.0 | Day 1 | Initial design text (not verified against code). |

## 12. ملخص بالعربي

فيه نوعين citations: بتاعة الـ retrieval (id = chunk_id) وبتاعة الإجابة (C1, C2). الـ composer بيمسح أي id مش في الـ evidence المسترجع، لكن مبيتأكدش إن النص فعلاً مدعوم من الـ chunk. ومسار الـ source الأصلي مش بيوصل للـ citation لسه، والـ version مش بيتغيّر أوتوماتيك.
