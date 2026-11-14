| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Evaluation lead (Ziad, E5) with component owners | Proposed (needs Lead sign-off) | 0.1.1 | 2026-11-14 | M11, C1-C6, P1-6 in [IMPLEMENTATION_ROADMAP](../plan/IMPLEMENTATION_ROADMAP.md) | `run_evaluation.py`, `tests/eval/`, `ai/rag/evaluation/`, `datasets/evaluation/`, `.github/workflows/ci.yml` |

# Evaluation system: production-readiness roadmap

## 1. Where the system stands

Evidence comes from a review of the code and reports, and from a test run on 2026-11-13 in a clean environment: the full suite gives **427 passed, 4 skipped, 0 failed** with the optional dependencies installed (`torch`, `sentence-transformers`, `opentelemetry-sdk`, `pytesseract`, `tesseract`, Redis).

Passing tests mean the *code* is sound. They do not show that the *evaluation measures Flame*. Today the only real-system numbers are the live retrieval benchmark (26 questions, `retrieval-2026-11-12.md`) and the FLEX outcome model card. Everything else in the release gate is either run against a mock or not measured.

| Release-gate row ([release-gate.md](release-gate.md)) | Threshold | Measured on the real system today? |
|---|---|---|
| Recall@5 | 0.80 or more | Partly: document-level recall@5 = 0.88 on 26 AI-authored questions. The harness number (21.05%) is the mock. |
| MRR | 0.70 or more | Partly: MRR@10 = 0.91, same caveat. |
| Unsupported-claim rate | 0.05 or less | **No.** No code computes it. |
| PII masking precision | 1.00 | **No.** Regexes exist, but there is no labelled PII test set and no precision figure. |
| Adversarial holdout defence | 100% | **No.** 3 injection cases, scored against the mock. |
| CV IoU (flame core) | 0.70 or more | **No.** Mean IoU 0.32 [0.13, 0.55] on 8 held-out BASS-II tests (0.47 on the flames it detects); 0.82 on SPICE dev images. The masks are Claude-drafted and not yet validated (`cv_gold_v1`, [docs/cv/evaluation-report.md](../cv/evaluation-report.md)). |
| API contract pass | 100% | **No.** The 4 contract tests in `tests/eval/test_api_contracts.py` are skipped stubs, although the API exists. |

## 2. Defects found while preparing this roadmap

These are small and cheap to fix, and each one makes a result untrustworthy today.

| # | Defect | Evidence | Effect |
|---|---|---|---|
| D1 | **The API connector calls an endpoint shape that does not exist.** | `tests/eval/rag_connector.py` sends `POST /api/search {query, top_k}` and reads `answer`, `citations`. The real `/api/search` is `GET ?q=…` and returns no answer. Answers come from `POST /api/chat`. | `--model api` cannot work. |
| D2 | **A connection failure is reported as an ordinary answer.** | The connector returns `"API Connection Error: …"` as `answer` instead of raising. | A dead API silently scores as a bad model. |
| D3 | **The LLM judge counts "unfaithful" as faithful.** | `master_pipeline.py`: `is_faithful = "true" in text or … or "faithful" in text`. A reply `{"is_faithful": false}` contains "faithful", so it passes. | False negatives in the faithfulness gate when `GEMINI_API_KEY` is set. |
| D4 | **The offline judge fallback is a keyword check.** | Passes any non-empty answer that mentions "flame", "nasa", "iss", etc. | It cannot detect hallucination. It must not count toward the gate. |
| D5 | **`run_evaluation.py` never fails the build.** | It prints a scorecard and exits 0 whatever the metrics. | The thresholds exist only on paper. |
| D6 | **Provenance can be wrong.** | `dataset_sha256` always hashes `rag_gold.jsonl`, even with `--data other.jsonl`. `model_provider` defaults to `gemini-pro` even in mock mode. | A run record can name a dataset and model that were not used. |
| D7 | **Dataset documentation drifts.** | Datasheet says splits are 12/12/11 (35 cases + 3 adversarial). The file has 38 cases split 14/14/10, 31 answerable and 7 not. | The datasheet and the data disagree. |
| D8 | **The Arabic gold set is off-domain and off-schema.** | `rag_gold_arabic_v0.jsonl` (`TC_REAL_*`) asks about electrical panels and blueprints, and uses `split: "test"`, which `gold_schema.json` does not allow. | It cannot be scored against the NASA corpus. |
| D9 | **Two scoring scales.** | `evaluator.py` uses 1-5 (4.0 / 4.5 / 4.0); the gate uses 0-1. | Two verdict conventions for the same system. |
| D10 | **The gold set does not match the corpus.** | Already recorded as P1-6 in IMPLEMENTATION_ROADMAP: the gold set cites documents that are not registered in the corpus. | Harness metrics cannot reflect Flame even once D1 is fixed. |

## 3. Roadmap

**Progress 2026-11-14 ([eval-gate.md](eval-gate.md)).** EV-02 (thresholds that fail the build) is met by `ai.rag.evaluation.gate`; EV-17 (baseline and the 2 % rule) by `docs/evaluation/baselines/gate_baseline.json` and `--baseline`; EV-15 and EV-16 by `.github/workflows/eval.yml` (a regression check on every relevant change and nightly; the live part is manual); EV-09 and EV-10 have their exams and scorers (`run_pii_exam.py`, `run_safety_exam.py`) but the exams are AI-drafted and unverified, and the trick-question exam still needs a live run. EV-08 and EV-11 (generated-answer evaluation) remain open.

Estimates are for one engineer unless noted. Phases are ordered by dependency: nothing in Phase 2 is worth automating before Phase 0 makes the numbers real.

### Phase 0: Make the measurements real (about 1 week)

| ID | Task | Owner | Acceptance |
|---|---|---|---|
| EV-01 | Rewrite the API connector for the real contract: retrieval through `GET /api/search`, answer and citations through `POST /api/chat`, bearer token from `FLAME_READ_API_TOKEN`. Raise on any connection or HTTP error (fixes D1, D2). | Ziad | `run_evaluation.py --model api` against the compose stack produces non-mock numbers. A stopped API exits non-zero. |
| EV-02 | Make thresholds enforceable: exit code 1 when any gate row fails or a metric drops more than 2% from the frozen baseline (fixes D5). | Ziad | A unit test feeds a failing report and asserts exit code 1. |
| EV-03 | Fix the judge (fixes D3, D4): request structured JSON, parse it with a real parser, temperature 0. The local fallback must label the case `unverified`, never `faithful`, and a release run fails if any case is `unverified`. | Ziad | Tests with "false", "unfaithful" and malformed replies all fail the case. |
| EV-04 | Correct provenance (fixes D6): hash the file actually used; record the model, prompt version, API commit and corpus version from the run; label mock runs `mock`. | Ziad | `test_provenance.py` covers `--data` with a different file. |
| EV-05 | Replace the 4 skipped contract stubs with real tests against the app, or delete them and rely on `apps/api/tests` contract parity (the gate row "API contract pass"). | Ziad + Anas | No skipped test remains in `tests/eval/`. |
| EV-06 | Reconcile the datasheet with the data (fixes D7) and remove or fix the off-domain Arabic file (fixes D8). | Ziad | The datasheet counts equal `wc`/schema-validated counts, checked by a test. |

### Phase 1: Close the release-gate coverage (2 to 3 weeks)

| ID | Task | Owner | Acceptance |
|---|---|---|---|
| EV-07 | **Re-annotate the gold set against the registered corpus** (D10, P1-6), with human review. Grow from 38 to at least 100 cases, per the evaluation plan. Measure inter-annotator agreement. | Ziad + Eman + domain reviewer | Every label resolves to an ingested document (`--check-labels` equivalent); Cohen's kappa of 0.70 or more on a double-annotated subset. |
| EV-08 | **Unsupported-claim rate**: split answers into atomic claims and check each against the retrieved evidence. Add it to the report. | Ziad | Metric present; validated against a hand-labelled sample of at least 50 answers. |
| EV-09 | **PII precision**: build a labelled PII set (English and Arabic, NASA-style references), then report precision and recall. | Ziad | 1.00 precision on the set; recall reported, not hidden. |
| EV-10 | **Adversarial holdout**: grow injection and jailbreak cases from 3 to at least 30; score refusal and abstention on the real `/api/chat`, not the mock. | Ziad + Anas | 100% refusal on the holdout, with every failure listed by case. |
| EV-11 | **Generated-answer evaluation**: faithfulness, citation precision and recall, and abstention on the unanswerable cases, through `/api/chat`. Human spot-check 20% of the judge's verdicts. | Ziad + Eman | Report generated from a live run; judge-vs-human agreement recorded. |
| EV-12 | **Add missing metrics to the harness report**: nDCG@5, latency p50 and p95, per-split and per-category breakdowns. | Ziad | All gate rows have a number in `evaluation_report.json`. |
| EV-13 | **CV ground truth**: integrate annotated masks (E3-3), split by `groupId`, wire `cv_metrics.py` into a real test and the gate. | Princess + Ziad | IoU and Dice reported on validated masks; `NOT_EVALUATED` status removed. **2026-11-14:** `cv_gold_v1` built (150 frames, 56 drafted masks, split by test, held-out split); IoU is now reported. It awaits human validation of the masks. |
| EV-14 | Retrieval benchmark: expand from 26 to at least 100 reviewed questions; add bootstrap confidence intervals; investigate the persistent miss on RG-22 and the RG-19 regression. | Eman | A hit@1 difference is reported with an interval, so one question cannot flip a decision. |

### Phase 2: Automate it (about 2 weeks)

| ID | Task | Owner | Acceptance |
|---|---|---|---|
| EV-15 | **CI `eval` job** on every PR: deterministic, offline, fixed small corpus and cached embedding model. Uploads the report as an artifact and posts the metric deltas. | Anas + Ziad | A deliberate retrieval regression turns the job red. |
| EV-16 | **Nightly full evaluation** against staging with the live API and the full gold set; results appended to a history file. | Anas | A failed gate raises a notification to the component owner named in [release-gate.md](release-gate.md). |
| EV-17 | **Frozen baselines per release tag**, stored under `docs/evaluation/baselines/`, with a script that compares a candidate run with the baseline (2% rule). | Ziad | `compare_runs.py baseline.json candidate.json` exits non-zero on regression. |
| EV-18 | **Reproducible environment**: an `eval` requirements file with pinned versions; the setup script installs `tesseract-ocr`; Redis in CI so no test skips. The current `requirements.txt` pulls TensorFlow, which the evaluation does not need. | Anas | A clean container runs `python -m pytest` with 0 skips, from documented steps. |
| EV-19 | **Branch protection or equivalent**: CI is advisory today (the private repository is on the free plan). Until upgraded, add a merge checklist that requires a green `eval` job. | Lead | Decision recorded; checklist in the PR template. |

### Phase 3: Production monitoring and governance (1 to 2 weeks, partly parallel)

| ID | Task | Owner | Acceptance |
|---|---|---|---|
| EV-20 | **Drift monitoring on live traffic**: sample real queries (PII-masked), re-score weekly, alert on retrieval-score and abstention-rate shifts. Productionise `drift_monitor.ipynb` as a script. | Ziad + Anas | Weekly report generated automatically; thresholds documented in [OBSERVABILITY.md](../operations/OBSERVABILITY.md). |
| EV-21 | **Model comparison from recorded runs** (Gemini, GPT-4o, local): Pareto ranking, then human sign-off. Fills the placeholder `llm-comparison-2026-10-12.md`. | Eman + Ziad | The report is generated from stored runs, not typed. |
| EV-22 | **Human evaluation protocol**: blind expert review of a sample per release, using `annotation-guidelines.md`. | Ziad + domain reviewers | Review sheet, agreement score, and the unresolved disagreements recorded. |
| EV-23 | **Clean up**: archive `tests/eval/Ziad____10/`, `NASA____10.zip` and the Day 1-3 archive; fold `evaluator.py` into one 0-1 scale (D9); convert or delete notebooks that are not run. | Ziad | One evaluation code path; no duplicate harness copies. |
| EV-24 | **Phase 2 final report and sign-off matrix**, generated by `render_report.py` from stored runs; all four component leads sign. | Ziad + leads | `phase2-final.md` filled; each gate row links to its run. |
| EV-25 | **Eval hygiene**: keep API keys out of reports and logs; confirm `audit_log.json` holds no PII or secrets; record dataset licences. | Ziad + Anas | Secret scan covers the evaluation artifacts. |

## 4. Definition of "production-ready" for evaluation

The evaluation system is ready when all of the following hold:

1. Every row of the release gate has a number produced by a **live** run, with a provenance block that names the real dataset, model, prompt and commit.
2. `run_evaluation.py` and the CI `eval` job **fail the build** on a gate failure or a regression of more than 2%.
3. The gold sets are re-annotated against the corpus, human-reviewed, and large enough that one question cannot change a verdict (100 or more cases).
4. No judge result without a real model counts as a pass.
5. The full test suite runs with **0 skipped** from documented steps in a clean container.
6. A weekly drift report runs on sampled production traffic.
7. All four component leads have signed the Phase 2 report.

## 5. Dependencies and risks

| Risk | Mitigation |
|---|---|
| Human annotators and domain reviewers are the critical path (EV-07, EV-13, EV-22). | Start annotation on day 1 of Phase 0; everything else can proceed in parallel. |
| The judge model needs an API key and network access; the offline deployment has neither. | Keep the local judge only as a smoke check (`unverified`); do release runs where a real judge is reachable. |
| Live evaluation needs a deployed stack (a Docker host: P1-7). | Use the compose stack for EV-01; track P1-7 separately. |
| A larger gold set raises annotation cost. | Grow in stages (38, then 60, then 100); each stage must stay human-reviewed. |
| CI is advisory on the current plan (EV-19). | Record the decision; rely on the merge checklist until the plan changes. |

## Known limitations
- The owners and the time estimates are proposals; none has been confirmed by the people named.
- The defects in §2 were found by reading the code and by running the suite once on 2026-11-13. D1 (the connector's endpoint shape) was not exercised against a running API in this review; confirm it with EV-01.
- The status table in §1 uses the 2026-11-12 retrieval report and the committed baseline; it has not been refreshed with a new live run.
- Phase 3 effort depends on EV-07 (annotation) finishing, which this roadmap cannot schedule.

## Changelog
- 0.1.1 (2026-11-14): CV IoU row and EV-13 updated with the `cv_gold_v1` results.
- 0.1.0 (2026-11-13): first draft from the full-suite run and a code review of the harness.
