| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.3.6 | 2026-11-14 | C2, M10, D1, E2 | `docs/evaluation/annotation-guidelines.md`, `datasets/evaluation/nlp_gold_v1.schema.json`, `ai/rag/nlp/evaluation.py`, `ai/rag/nlp/gold_worklist.py`, `datasets/evaluation/passage_gold_v1.schema.json`, `ai/rag/evaluation/passage_gold.py`, `ai/rag/evaluation/propose_candidates.py` |

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
7. **Worklist (2026-11-14).** `datasets/evaluation/nlp_gold_v1_worklist.jsonl` holds the 60 pages to annotate, each with its exact indexed text, an empty `annotations` list and an empty `annotator`; `nlp_gold_v1_worklist.manifest.json` records how they were chosen and which 12 cases are double-annotated (6 dev, 3 validation, 3 holdout). It is built by `python -m ai.rag.nlp.gold_worklist build` (seeded, deterministic; `build --check` and `tests/unit/test_nlp_gold_worklist.py` fail if the PDFs no longer give the same text). How the pages were chosen:
   - pages with a native, non-garbled text layer of at least 300 indexed characters, from the 27 committed NTRS PDFs of cleared sources;
   - 2 pages per document, then one more for each of the 9 documents with the most such pages (no document has more than 3);
   - splits by **document** (31 dev, 14 validation, 15 holdout cases; no document in two splits).
   
   Two departures from item 4, both forced by the corpus: `FF-NTRS-20120016855` has no native text layer (it is OCR-only in production) and is left out, because OCR text depends on the Tesseract version and its offsets would not reproduce; `FF-NTRS-20120015928` has only one such page, so it contributes one case.
   
   To annotate: copy the worklist, fill `annotator` and `annotations` (one span per entity; `text` must equal `chunk_text[char_start:char_end]`), and run `python -m ai.rag.nlp.gold_worklist validate <copy> --partial` as you go and without `--partial` when done. The validator rejects a changed `chunk_text`, `split`, page or document, a label outside the 14, offsets that do not match the text, duplicate spans and an AI-looking annotator, and it warns when a case's spans are exactly what the extractors emit (item 6). For the double-annotated cases, two people fill separate copies and `python -m ai.rag.nlp.gold_worklist agreement <copy A> <copy B>` reports token-level Cohen's κ (each whitespace token labelled with the set of types covering it, or `O`); it exits non-zero below 0.65 and refuses two copies by the same annotator. Only after adjudication (item 5) do the cases go into `nlp_gold_v1.jsonl`.

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
8. **AI-drafted starting point (2026-11-13).** `datasets/evaluation/passage_gold_v1_drafts.jsonl` holds 35 **draft** cases written by an AI (`author: "claude (AI draft)"`, `status: draft`, no verifier): 24 answerable cases citing 16 of the committed PDFs and 11 unanswerable ones (8 `in_domain_not_in_corpus`, 3 `out_of_domain`), split by document (answerable cases: dev 11, validation 9, holdout 4). It is **not** the gold set: `passage_gold_v1.jsonl` stays empty, nothing is scored, and no number may be reported from the drafts. Every span reproduces the page's verbatim text (`tests/unit/test_passage_gold_drafts.py`); the questions are paraphrases (the test rejects any five-word run copied from the passage). How it was built, and what to distrust:
   - Answerable passages come from the worklist (§6). I kept only passages whose answer is not repeated verbatim in another document. `python -m ai.rag.evaluation.verification_sheet` then listed, for each draft, other pages that contain a figure of the cited passage; that found five drafts whose answer is stated on a second page too, and a critical read three more (eight in all: PG-002, 005, 007, 008, 009, 016, 021, 023), which now cite every such page (a retrieval hit on any counts). The pre-screen and what a verifier should still look at are in `docs/evaluation/reports/passage-gold-drafts-prescreen-2026-11-13.md`; it is by the drafts' own author and is not a verification. 18 of the 24 share a figure with another page, mostly coincidentally (21 %, 3 mm); the verifier decides.
   - The 8 in-domain unanswerable questions are about topics a keyword search found **absent** (first on 240 indexable pages, re-run on the 438 pages of the 26 reports now in `docs/research`; `lithium` occurs once, in `lithium hydroxide`, a CO2 canister, not a battery) (hydrazine, aerogel, lunar regolith, fire blanket, lithium, titanium, kerosene, Artemis/Gateway). A first list of eleven had four topics that turned out to be in the corpus (hydrogen, Skylab, ethylene, halon), which is why the check exists. Absence of a keyword is weaker than absence of an answer, and §5.3 asks that a *person* write these: treat them as proposals to accept or rewrite. They also name things the reports never mention, so a lexical retriever finds them easy; they test the abstention path, not the dense gate's hardest case.
   - To verify: read `datasets/evaluation/passage_gold_v1_review_pack.md` (each draft with the text around its evidence and the pre-screen's recommendation; it ends with the adoption command) or `python -m ai.rag.evaluation.verification_sheet --out datasets/evaluation/passage_gold_v1_verification.csv` (the generated sheet is committed, regenerated on the 438 pages), fill `answers_question`, `unique`, `question_clear` and `notes`, then adopt what you accept: `python -m ai.rag.evaluation.adopt_drafts --verifier "Your Name" --accept PG-001 PG-002 ...`. It refuses an AI-looking name, the author, an unknown ID, and any selection that would break `validate` (accept answerable and unanswerable cases together so at least 25 % are unanswerable); nothing is written on a refusal. `retrieval_report` needs 20 verified **answerable** cases, so accept at least 20 of the 24 answerable ones.
9. **Using the verified set (runner).** Once at least 20 answerable cases are verified, `ai/rag/evaluation/run_passage_gold.py` scores them through the live `/api/search`: `run --label baseline --out baseline.json` (page-level hit@1, hit@5 and MRR with 95 % intervals; the right document on the wrong page is a miss); restart the API with `FLAME_LEXICAL_MODE=or_idf` or `FLAME_DENSE_GRANULARITY=window` and run again under another label; `compare baseline.json or_idf.json` gives the paired difference over the same questions and says whether its interval excludes 0 (`difference_shown`). Run the `run --mode chat` variant and `calibrate` on it to see how well the top search score separates answerable from unanswerable questions (needs 8 verified unanswerable cases too). The runner only reads the file and the API; it sets nothing, and it uses verified cases only, so the AI drafts are never scored.
10. **Person-written unanswerable questions, adopted in two steps (2026-11-14).** The verifier of the 24 answerable drafts rejected the 11 AI-drafted unanswerable ones (§5.3 asks that a person writes them), which leaves 0 unanswerable cases and fails the 25 % rule. To fix that without the author verifying their own questions:
   - The question writer puts 8 or more questions in a text file, one per line (`OOD:` before an out-of-domain one), and runs `python -m ai.rag.evaluation.add_unanswerable --author "Their Name" --file questions.txt --check-only` to see, for each question, how many pages of the committed reports contain each of its distinctive words, which words occur nowhere, and the closest pages. The report is a lexical aid: read the closest pages. Without `--check-only` the questions are appended to `passage_gold_v1_drafts.jsonl` as drafts authored by that person (it refuses an AI-looking name, a duplicate, a question under 10 characters).
   - Adoption can be staged: `adopt_drafts --allow-incomplete` records the first person's cases even though the unanswerable share is still below 25 %, then a second person (never the author of those cases) runs `adopt_drafts --verifier "Their Name" --accept PG-036 ...` without the flag, and the second run refuses unless the set is then complete.
   - `run_passage_gold run` refuses to score a gold file that breaks `validate` (so an incomplete set is never scored), after checking it has 20 verified answerable cases.

---

## Known limitations

- `nlp_gold_v1.jsonl` is still empty (0.3.6): the §4.7 worklist exists, but no chunk has been annotated, so no extractor has a measured precision or recall. Items 4 and 5 are proposals until Ziad confirms them.
- The extractors also emit `platform` (vocabulary), `document_class` and `metadata_field` records, which are not among the 14 labels. Scored against this gold set they would all count as false positives, so either add `platform` to the labels or drop those types before scoring; that is a decision for the guideline owner.
- `passage_gold_v1.jsonl` is empty at version 0.3.2 (35 AI drafts exist next to it, unverified): no question has been written or verified, so no retrieval or answer number can be reported from it. §5 sizes and thresholds are proposals until Ziad confirms them; the 20-case floor is a minimum for reporting, not a claim that 20 is enough.
- Sections 1-3 are unchanged from 0.1.0 and keep their own open points.

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.3.6 | 2026-11-14 | §4.7: NLP annotation worklist (60 pages, document-disjoint splits, 12 double-annotated), validator and agreement tool; header restored (0.3.5 had replaced it with its changelog row). |
| 0.3.5 | 2026-11-14 | §5.10: person-written unanswerable questions (`add_unanswerable`), staged adoption (`--allow-incomplete`), the runner refuses an incomplete set. |
| 0.3.4 | 2026-11-13 | §5.8: review pack; checks and verification sheet re-run on the 438 pages now in the corpus. |
| 0.3.3 | 2026-11-13 | §5.9: runner that scores the verified set through the API, compares two runs, calibrates abstention. |
| 0.3.2 | 2026-11-13 | §5.8: AI-drafted starting point (35 unverified drafts), verification sheet, adoption command. |
| 0.3.1 | 2026-11-13 | §4 annotators work from the indexed (normalised) text, §5 spans refer to the verbatim text; `pypdf` is no longer recommended; `--show` prints either. |
| 0.3.0 | 2026-11-13 | Added §5 (passage-level question gold set: protocol, schema, validator, worklist, intervals). |
| 0.2.0 | 2026-11-13 | Added §4 (NLP span annotation, D1), known limitations and this changelog. |
| 0.1.0 | 2026-10-12 | First draft: human rubric, blinded review protocol, mask-review protocol. |
