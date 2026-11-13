| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.2.0 | 2026-11-13 | C2, M10, D1 | `docs/evaluation/annotation-guidelines.md`, `datasets/evaluation/nlp_gold_v1.schema.json`, `ai/rag/nlp/evaluation.py` |

# E5-3: Annotation and Human-Review Guidelines

## 1. Human Evaluation Rubric

Human reviewers score model responses across three primary dimensions using a standardized 1–5 Likert scale.

| Score | Factual Correctness | Evidence Support (Faithfulness) | Completeness |
|---|---|---|---|
| **5 (Flawless)** | Fully accurate scientific statement; no inaccuracies. | Every sentence is directly attributed to provided context. | Directly and fully answers the prompt with all key nuances. |
| **4 (Minor defect)** | Factually sound; minor phrasing ambiguity. | Supported, but contains 1 minor extrapolative inference. | Answers primary question, omits 1 minor detail. |
| **3 (Borderline)** | Partially accurate; 1 non-critical scientific error. | Partial grounding; some statements lack citations. | Incomplete; leaves key secondary questions unanswered. |
| **2 (Poor)** | Contains significant factual errors or fabrications. | Noticeable hallucination; cites incorrect section. | Fails to answer core question. |
| **1 (Critical fail)** | Dangerous scientific misinformation or unsafe instruction. | Completely fabricated / ungrounded response. | Refuses incorrectly or produces gibberish. |

---

## 2. Blinded Review Protocol for Model Comparison (C2)

To evaluate candidate LLM / RAG variants without cognitive bias:
1. **Model Identity Masking**: Outputs are stripped of headers, token counters, or style signatures and assigned random identifiers (`Model-Alpha`, `Model-Beta`).
2. **Order Randomization**: Sequence of models presented to reviewers is shuffled uniformly.
3. **Inter-Annotator Agreement (IAA)**:
   * Assessed using **Cohen's Kappa ($\kappa$)** for pairwise ratings and **Fleiss' Kappa** for $\ge 3$ reviewers.
   * Target acceptance threshold: $\kappa \ge 0.65$ (substantial agreement).
   * Discrepancies ($|\Delta| \ge 2$) undergo adjudication with the Lead (Anas).

---

## 3. Computer Vision Mask-Review Protocol (with Princess / E3)

Co-owned with `docs/cv/annotation-protocol.md`:
* **Flame Core vs. Plume Separation**: Reviewers verify that segmentation masks strictly delineate the inner reaction zone from diffuse outer soot radiation.
* **Polygon Precision**: Minimum 12-vertex boundary requirement for non-spherical turbulent microgravity flame regimes.
* **Acceptance Gate**: Inter-annotator mask IoU must exceed 0.85 before ground truth freezing.

---

## 4. NLP span annotation (D1)

Gold set for the scientific NLP extractors of `docs/ai/nlp-pipeline.md`. Format: `datasets/evaluation/nlp_gold_v1.schema.json`; file: `datasets/evaluation/nlp_gold_v1.jsonl`; scorer: `ai/rag/nlp/evaluation.py` (`score`, strict and relaxed).

1. **What is annotated.** One *chunk* is one page of a committed NTRS PDF in `docs/research/`, exactly as the pipeline sees it. Annotate the text the extractor will read, not the rendered page: `python -c "from pypdf import PdfReader; print(PdfReader('docs/research/<file>.pdf').pages[<n>].extract_text())"`. `char_start`/`char_end` are offsets into that string, and `chunk_text[char_start:char_end]` must equal the annotation's `text` (the schema test checks this).
2. **Labels.** The 14 entity types of `nlp-pipeline.md` §2 (`experiment`, `investigation`, `publication`, `dataset`, `phenomenon`, `fuel`, `oxidizer`, `environmental_condition`, `measurement`, `instrument`, `physical_quantity`, `material`, plus `research_finding` and `hypothesis` for claim chunks). One span, one label; the *longest* span that is still the entity (`3.2 cm/s`, not `3.2`). Spans of different types may overlap (`PMMA` is both `material` and `fuel`).
3. **What is not an experiment.** NASA-STD-6001 test methods (`Test 1`), shuttle missions (`STS-94`), aircraft (`KC-135`) and conference or report numbers are not experiments. An experiment is a named run of a study (a FLEX test, a sample).
4. **Size and splits (proposal, owner: Ziad).** 60 chunks, at least 2 per document, split dev 50% / validation 25% / holdout 25%. The holdout split is not opened by extractor authors and is scored once.
5. **Agreement.** 20% of chunks are annotated twice, independently. Token-level Cohen's κ must reach 0.65 (the §2 threshold) before ground truth freezes; discrepancies are adjudicated with the Lead (Anas).
6. **Provenance.** Every case records its `annotator`. Spans proposed by an extractor are not gold: do not pre-fill annotations from the pipeline's output.

---

## Known limitations

- `nlp_gold_v1.jsonl` is empty at version 0.2.0: no chunk has been annotated yet, so no extractor has a measured precision or recall. Items 4 and 5 are proposals until Ziad confirms them.
- Sections 1-3 are unchanged from 0.1.0 and keep their own open points.

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-11-13 | Added §4 (NLP span annotation, D1), known limitations and this changelog. |
| 0.1.0 | 2026-10-12 | First draft: human rubric, blinded review protocol, mask-review protocol. |
