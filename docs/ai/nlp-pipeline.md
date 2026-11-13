# Scientific NLP pipeline (E1-7)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Eman | Draft; rule-based extractors run at ingest and are stored, everything else **Planned** | 0.3.2 | 2026-11-13 | D1 | `ai/rag/nlp/`, `apps/api/flame_api/nlp_extract.py`, `nlp_graph.py`, migration `0010`, `tests/unit/test_nlp_*.py`, `apps/api/tests/test_nlp_*.py` |

**Status (2026-11-13):** six rule-based extractors exist in `ai/rag/nlp/` (identifiers, measurements and units, vocabulary lookup, document class, first-page metadata, table/figure association). `python -m flame_api.ingest` runs them over the indexed chunk text after the knowledge-graph build and stores the records in `nlp_record` (migration `0010`); `python -m flame_api.nlp_extract run|status` does the same on demand, and `python -m flame_api.nlp_graph build` turns co-occurrences into unreviewed graph edges (`docs/data/KNOWLEDGE_GRAPH_SCHEMA.md`). The API does not serve the records yet. Re-running creates nothing new; a human `human_verified` / `rejected` decision survives a re-run; a changed chunk, a new extractor version or a deleted chunk marks old rows `superseded`. The vocabulary is the seed files plus the graph's own fuels, phenomena and investigation names (an investigation name is matched in its own case only, because `SAME` is also a word). **The seed vocabularies are still unreviewed by a domain expert and no extractor has a measured precision or recall**; treat every record as a candidate. To make the review quick, `python -m ai.rag.nlp.review_sheet docs/research --out docs/data/vocabulary-review-2026-11-13.csv` writes one row per vocabulary entry (46 entries): hits, documents, the surface forms actually matched and three matches in context, from the 240 indexable pages of the 24 committed NTRS PDFs, with empty `decision`, `correction` and `notes` columns for the expert. Two entries have no hit in this corpus (`high-speed camera`, `flame speed`); that flags them for a look, it does not make them wrong. Nothing in the sheet is a precision figure: it only counts matches. Model NER, relation, claim and contradiction extraction, query classification and expansion, and summarisation remain **Planned**. Examples are synthetic.

## 1. Scope and ground rules

The pipeline turns a validated document into source-linked records. The D1 task list is: document classification, scientific entity recognition, experiment identifier extraction, relation extraction, metadata extraction, table and figure association, terminology normalisation, unit and quantity extraction, claim extraction, contradiction detection, query classification, query expansion and evidence-aware summarisation.

Rules for every extractor:

1. Every record carries `document_id`, `document_version`, `page`, `char_start`, `char_end` and the `chunk_id` it came from (stable ids shared with PostgreSQL and the vector index). A record with no location is rejected, not stored.
2. Every record carries `extractor` (name), `extractor_version`, `method` (`rule`, `model` or `llm`) and `confidence`.
3. Extraction output is a **candidate**. Nothing is shown as scientific fact until it is reviewed (see `graph-memory.md`).
4. An LLM extractor never invents a source span: the span must be found verbatim in the chunk text, or the record is dropped and counted.

## 2. Entity types (D1 list) with synthetic examples

| Entity type | Definition | Synthetic example | Method (Planned) |
|---|---|---|---|
| Experiment | A named run with an identifier | "run FX-0042" | rule (id pattern) + model |
| Investigation | A named research programme grouping experiments | "Investigation ALPHA" | model |
| Scientific publication | A cited paper or report | "Report XR-17, 2019" | rule (citation pattern) |
| Dataset | A named collection of measurements | "dataset DS-flame-07" | rule + model |
| Combustion phenomenon | A named flame behaviour | "flame extinction" | model, controlled vocabulary |
| Fuel | A combusting material | "methane" | vocabulary lookup |
| Oxidizer | The oxidising gas | "oxygen-nitrogen mix" | vocabulary lookup |
| Environmental condition | A stated ambient condition | "0.1 atm, microgravity" | rule (quantity) + model |
| Measurement | A value with a quantity and unit | "flame speed 3.2 cm/s" | rule (quantity grammar) |
| Instrument | A device that produced data | "high-speed camera" | vocabulary + model |
| Physical quantity | A kind of measurable property | "flame speed" | vocabulary |
| Material | A solid or fluid sample | "polymer sheet" | vocabulary + model |
| Research finding | A statement of result | "flame spread was slower at 0.1 atm" | LLM, reviewed |
| Hypothesis | A stated, untested explanation | "buoyancy may explain the difference" | LLM, reviewed |

The schema is extended only when real research needs justify it (D1).

## 3. Methods and confidence semantics

| Task | Method | Model/version | Confidence means |
|---|---|---|---|
| Identifier extraction | rule (regular expression) | n/a, rule set version | 1.0 for an exact pattern match, else not produced |
| Unit and quantity extraction | rule + unit table | unit table version | 1.0 when the number and unit parse; otherwise dropped |

Unit table `units-1.1.0` (measurement-rules 1.1.0): `g` is both grams and gravity in this corpus, so it is resolved from context. "700 g of fuel" is mass; "1g" written against the number is standard gravity (9.80665 m/s²); any other bare `g` keeps the dimension `gravity_or_mass` and is never converted. The grammar also reads `mm Hg`, `°F`, `m/s^2`, `5 × 10^-3` and `1,000`; it skips areas (`cm^2`), OCR'd clock times (`23:30:3g.5`) and descending hyphen "ranges" such as `10-6 g`, which are flattened superscript exponents.
| Entity recognition | model | not chosen yet | model probability for the span; **not calibrated** until measured |
| Relation, claim, contradiction | LLM with schema output | not chosen yet (local first, see 2H) | self-reported plus a check that the cited span exists; **not calibrated** |
| Query classification, query expansion | rule first, model second | not chosen yet | label probability |

Confidence is only comparable inside one extractor version. It is never used as a probability of truth.

## 4. Source-location preservation

Record shape (stored in `nlp_record`): `{record_id, type, text, normalized, document_id, document_version, page, char_start, char_end, chunk_id, extractor, extractor_version, method, confidence, review_status}`. A re-ingestion with a new document version creates new records and marks the old ones `superseded`; it never edits them in place.

Synthetic example: chunk `c-demo-001` (page 3) reads "In run FX-0042 the flame speed was 3.2 cm/s at 0.1 atm." Records: Experiment `FX-0042` (chars 7-14), Measurement `3.2 cm/s` (chars 35-43, quantity `flame speed`), Environmental condition `0.1 atm` (chars 47-54). All three point to `c-demo-001`.

## 5. Evaluation

Precision, recall and F1 per extractor will be copied from Ziad's harness output with run ID, commit and benchmark checksum. **No run exists**, so no number appears here. Sign-off: Ziad pending.

## Known limitations

- Only the rule-based extractors are implemented. No model has been chosen or tested, and no extractor has a measured precision or recall: the gold set (`datasets/evaluation/nlp_gold_v1.jsonl`) is empty.
- No model has been chosen or tested, and no confidence is calibrated.
- Arabic and mixed-language text handling is not designed yet.
- Contradiction detection today exists only as the `conflicts_with` metadata flag read by the composer (`docs/ai/grounded-generation.md`).

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.3.2 | 2026-11-13 | Unit table `units-1.1.0`: `g` resolved from context (grams, standard gravity or `gravity_or_mass`); `mm Hg`, `°F`, `m/s^2`, `× 10^n`, thousands separators; areas, OCR clock times and flattened exponents skipped (KB audit). |
| 0.3.1 | 2026-11-13 | Vocabulary review sheet generator and its first output. |
| 0.3.0 | 2026-11-13 | Ingest runs the extractors and stores `nlp_record` rows (migration `0010`); graph edges from co-occurrence; vocabulary draws on the graph. |
| 0.2.0 | 2026-11-13 | Status updated: rule-based extractors implemented as an unwired library; example character offsets corrected (they did not match the sentence). |
| 0.1.0 | 2026-10-14 | First design draft for E1-7 (D1); all behaviour Planned. |