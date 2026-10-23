# Update Report: Ziad (Engineer 5, AI Evaluation / Research Intelligence)

**Reviewed:** `main` @ `f9ee52f` (including the Day 3 drop, PR #12) · **Basis:** MVP plan §15 (Engineer 5), §16 daily table, §18 (Evaluation System), §22
**Verification:** `pytest tests/eval/test_provenance.py` run before and after the restructure (3 of 5 failed before; all pass after).

## Verdict: 4 / 10 against the MVP scope (lots of tooling, but it does not measure this project yet)

## Plan requirements vs. delivered

| Plan item (Engineer 5) | Day | Status | Evidence |
|---|---|---|---|
| Evaluation rubric, JSONL schema, acceptance baseline | 1 | Partial | `datasets/evaluation/gold_schema.json` exists, but it does not match the plan's §18 record shape (`id`, `expected_evidence_ids`, `rubric_version`, `source_scope`) and conflicts with the other gold file (see defects) |
| Source-quality and provenance checklist | 2 | Done (in form) | `docs/evaluation/provenance_checklist.md` (Arabic, 3 sections) |
| Parser / provenance test cases | 3 | Partial | `tests/eval/test_provenance.py` checks the gold file's shape only; it does not check any parsed document or locator |
| Retrieval relevance seed labels | 4 | **Missing** | No relevance labels against ingested chunks |
| Citation correctness test set | 5 | Partial | `citation_guardrail.ipynb` exists; no labelled set of real citations |
| Contract and smoke test suite | 6 | Missing | The API has its own 29 tests (Lead); nothing here exercises `/api/*` contracts |
| Baseline RAG report and defects | 7 | **Missing** | No RAG exists to score (Engineer 1) and no report |
| CV annotation / quality protocol | 8 | Missing | No protocol document |
| Initial IoU / measurement test cases | 9 | **Missing** | No ground-truth masks (blocked on Princess), no IoU code in `tests/eval` |
| API/CV contract tests, cross-modal scenarios | 10-11 | Partial | `cross_modal_consistency.ipynb` is a notebook, not a gate |
| Stale-cache and memory-contamination tests | 12 | Missing | No cache/MAG exists yet; no test design |
| Consolidated scorecard and release gate | 13 | Partial | `master_pipeline.py`, `evaluation_report.json`, `audit_logger.py` exist; the gate has no thresholds tied to real metrics |
| Acceptance report and sign-off matrix | 14 | Not done | |

## What was good
- A decent tool inventory: audit logging, experiment history, drift monitor, PII masking, LLM-judge and report generator notebooks, all with the right instincts (strict exit codes, separation of gold data from run history).
- `test_provenance.py` is the first real pytest gate in `tests/eval`.

## Defects found (and what was done)
| # | Finding | Action |
|---|---|---|
| 1 | **Wrong domain.** The gold cases and test cases are about a ship fire, engine-room electrical panels and blueprints (`scene-12`, `Blueprint A-101`), not microgravity combustion, NASA/NIST sources or flame images. Metrics computed on them say nothing about this system. This was the Day 1 finding and it has recurred. | Not changed. Needs a rewrite (see next steps). |
| 2 | Two incompatible gold schemas: Ziad's records use `case_id` and `expected_evidence[]`; the plan (and Eman's `rag_gold.jsonl`) use `id` and evidence IDs. Both files were named `rag_gold.jsonl` in different places. | **Renamed** Ziad's to `datasets/evaluation/rag_gold_arabic_v0.jsonl` so it no longer shadows the plan-shaped file; schema moved to `datasets/evaluation/gold_schema.json` |
| 3 | The Day 3 drop was nested as `tests/eval/day3_ziad/NASA/…`, with a second copy of the whole project layout (`datasets/`, `docs/`, `tests/`) inside it, an **exact duplicate of the MVP plan PDF**, scratch files (`t.py`, `.txt`/`.text` copies of scripts). | **Flattened**: scripts, notebooks and results now in `tests/eval/`; duplicates in `tests/eval/archive/day3_scratch/`; PDF removed; Day 1-2 in `tests/eval/archive/` |
| 4 | `test_provenance.py` used cwd-relative paths, so 3 of 5 tests failed from the repo root (missing schema path, count < 30 because the root file had 6 lines). It also was two files pasted together (duplicate `test_gold_dataset_exists`, the second silently overriding the first). | **Fixed** paths (anchored to the repo root, pointing at the moved files). The duplicate function name is still there. |
| 5 | `evaluator.py` and `audit_logger.py` read `test_cases.jsonl` / `audit_log.json` relative to cwd; they only work when run from `tests/eval/`. | Documented in `tests/README.md`; not changed |
| 6 | The §18 outputs must record code commit, dataset checksum, corpus index, prompt, model/provider, hardware, scorer version. `evaluation_report.json` records none of these. | Not changed |
| 7 | The notebooks are the primary deliverable, but a release gate must be runnable in CI (`pytest` / a script with exit codes). Only `test_provenance.py` is. | See next steps |

## Next steps (priority order)
1. Rewrite the gold set for the real domain: 30+ questions answerable from the ingested PSI/NTRS documents (include 3+ unanswerable and 3+ adversarial/prompt-injection cases), using the §18 record shape; keep dev/validation/holdout splits with no document leakage. Delete the ship-fire cases.
2. Add `tests/eval/` pytest gates that import `ai.rag` (Recall@k, MRR, nDCG, citation-locator validity) and `cv.flame_cv.segmentation_metrics` (IoU/F1), failing below stated thresholds.
3. Make `master_pipeline.py` write the §18 provenance fields (commit, dataset sha256, model/prompt versions) into every report.
4. Agree the label masks with Princess and the relevance labels with Eman this week; both of your Day 4/9 items are blocked on them.
5. Add contract tests that hit `apps/api` (`/api/health`, `/api/search`, `/api/analyses`) from `tests/eval` or `tests/integration`.
