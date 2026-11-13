| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.3.1 | 2026-11-13 | C2, M10, D1, E2 | `docs/evaluation/annotation-guidelines.md`, `datasets/evaluation/nlp_gold_v1.schema.json`, `ai/rag/nlp/evaluation.py`, `datasets/evaluation/passage_gold_v1.schema.json`, `ai/rag/evaluation/passage_gold.py`, `ai/rag/evaluation/propose_candidates.py` |

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

1. **What is annotated.** One *chunk* is one page of a committed NTRS PDF in `docs/research/`, as the pipeline indexes it: PyMuPDF `get_text("text")`, then normalised (`ai/rag/ingestion/normalize.py`: ligatures folded, hyphen splits rejoined, repeated headers and page numbers removed, stacked words joined). Print exactly that text with `python -m ai.rag.evaluation.propose_candidates --show docs/research/<file>.pdf --page <n>` (add `--verbatim` for the text as extracted). Do not use `pypdf`: it is not what production reads. `char_start`/`char_end` are offsets into the printed string, and `chunk_text[char_start:char_end]` must equal the annotation's `text` (the schema test checks this).
2. **Labels.** The 14 entity types of `nlp-pipeline.md` §2 (`experiment`, `investigation`, `publication`, `dataset`, `phenomenon`, `fuel`, `oxidizer`, `environmental_condition`, `measurement`, `instrument`, `physical_quantity`, `material`, plus `research_finding` and `hypothesis` for claim chunks). One span, one label; the *longest* span that is still the entity (`3.2 cm/s`, not `3.2`). Spans of different types may overlap (`PMMA` is both `material` and `fuel`).
3. **What is not an experiment.** NASA-STD-6001 test methods (`Test 1`), shuttle missions (`STS-94`), aircraft (`KC-135`) and conference or report numbers are not experiments. An experiment is a named run of a study (a FLEX test, a sample).
4. **Size and splits (proposal, owner: Ziad).** 60 chunks, at least 2 per document, split dev 50% / validation 25% / holdout 25%. The holdout split is not opened by extractor authors and is scored once.
5. **Agreement.** 20% of chunks are annotated twice, independently. Token-level Cohen's κ must reach 0.65 (the §2 threshold) before ground truth freezes; discrepancies are adjudicated with the Lead (Anas).
6. **Provenance.** Every case records its `annotator`. Spans proposed by an extractor are not gold: do not pre-fill annotations from the pipeline's output.

---

## 5. Passage-level question gold set (retrieval and answers)

Why: `retrieval_gold_v1` is 26 AI-authored, document-level questions with no unanswerable case, and `rag_gold` cites documents that are not in the corpus.
A difference of a few points on 26 questions is noise (`python -m ai.rag.evaluation.stats` shows the reranker's gain is within it). This set is what a
retrieval or answer claim can be checked against. Format: `datasets/evaluation/passage_gold_v1.schema.json`; file: `passage_gold_v1.jsonl`; rules and
scoring: `ai/rag/evaluation/passage_gold.py` (`validate`, `retrieval_report`). The file is empty until annotators fill it.

1. **A case** is a question, whether it is answerable, and (if so) the evidence: document, page, and the character span of the passage on that page, with its
   text. The span is an offset into the page's **verbatim** text (PyMuPDF `get_text("text")`, stripped: the evidence excerpt a citation points at; `--show ... --verbatim`), not into the
   rendered page and not into the normalised index text; `validate(..., page_texts=...)` checks that the text equals the page text at that span.
2. **Write the question from the passage, then hide the passage.** Paraphrase: a question that quotes the passage rewards lexical matching and says nothing about
   semantic retrieval. Types: `value_lookup`, `condition` ("what happened at 0.1 atm?"), `comparison`, `definition`, `procedure`, `other`.
3. **Unanswerable questions are written by a person**, at least 25% of the set, and each has a kind: `out_of_domain` (chocolate cake) or `in_domain_not_in_corpus`
   (a combustion question the committed reports do not answer). The second kind matters most: the dense similarity gate cannot catch it (on the committed PDFs the
   best irrelevant page scores a median 0.756 against 0.794 for the best relevant one). Do not generate it from a passage.
4. **Split by document, never by question.** No document appears in two splits; `validate` reports every document that does. The holdout is scored once.
5. **Two people.** An author writes a case as `draft`; a different person checks the evidence and the question and adds themselves to `verified_by`, which makes it
   `verified`. Only verified cases are scored, and `retrieval_report` refuses to report with fewer than 20 verified answerable cases. Token-level or label agreement is
   measured on a double-annotated 20% (κ ≥ 0.65, as in §2).
6. **A worklist exists, a gold set does not.** `python -m ai.rag.evaluation.propose_candidates --out worklist.jsonl --per-document 5` proposes sentences that contain a
   measurement, with exact offsets (checked on the committed PDFs: all 102 proposals reproduce the stored page text). Proposals are not cases. The tool needs PyMuPDF.
7. **Report intervals, not points.** Every number from this set carries a 95% bootstrap interval, and a claimed improvement carries a paired one
   (`ai.rag.evaluation.stats.compare_reports`). If it contains 0, the difference is not shown.

---

## Known limitations

- `nlp_gold_v1.jsonl` is empty at version 0.2.0: no chunk has been annotated yet, so no extractor has a measured precision or recall. Items 4 and 5 are proposals until Ziad confirms them.
- `passage_gold_v1.jsonl` is empty at version 0.3.0: no question has been written or verified, so no retrieval or answer number can be reported from it. §5 sizes and thresholds are proposals until Ziad confirms them; the 20-case floor is a minimum for reporting, not a claim that 20 is enough.
- Sections 1-3 are unchanged from 0.1.0 and keep their own open points.

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.3.1 | 2026-11-13 | §4 annotators work from the indexed (normalised) text, §5 spans refer to the verbatim text; `pypdf` is no longer recommended; `--show` prints either. |
| 0.3.0 | 2026-11-13 | Added §5 (passage-level question gold set: protocol, schema, validator, worklist, intervals). |
| 0.2.0 | 2026-11-13 | Added §4 (NLP span annotation, D1), known limitations and this changelog. |
| 0.1.0 | 2026-10-12 | First draft: human rubric, blinded review protocol, mask-review protocol. |
