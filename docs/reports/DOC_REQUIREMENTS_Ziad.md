# Documentation Requirements: Ziad (Engineer 5, Evaluation / Research Intelligence)

| | |
|---|---|
| **Phase** | Phase 2: Advanced Scientific Intelligence Platform |
| **Issued** | 2026-10-10 by the Lead (Anas) |
| **Your branch** | `Ziad` (branch fresh from `main` for each task) |
| **Basis** | [Phase 2 Plan](https://github.com/FCDS-College/Nasa/blob/main/docs/plan/PHASE2_PLAN.md): §2 carry-over items **M11** (benchmark and harness) and **M10** (CV evaluation design), and **Workstream C** (C1–C6); MVP Plan §18 |
| **Reviewers** | Lead (Anas) for every document. Eman (E1) for RAG/LLM benchmarks. Princess (E3) for CV evaluation. Anas (E2) for data and knowledge quality rubrics. |

---

## 1. Why this matters

In Phase 2, every decision (which model to promote, which retrieval variant to keep, whether to release) depends on your evaluation. A decision is only defensible if the benchmark, the scoring rules and the run that produced each number are documented. The audit on 2026-10-10 found:
- `datasets/evaluation/rag_gold.jsonl` has **only 6 items**.
- The harness is mostly notebooks in `tests/eval/`.
- The CV report reads `NOT_EVALUATED`.
- No consolidated scorecard or release gate exists.

`docs/evaluation/provenance_checklist.md` claims automated thresholds and exit codes that need to be shown working.

## 2. Rules for every document you write

1. **Location and format:** Markdown at the path given in §3, **in English** (an Arabic summary at the end is optional).
2. **Header block:** start every document with the table below.

   | Owner | Status | Version | Last updated | Plan items | Code paths |
   |---|---|---|---|---|---|
   | Ziad | Draft / In review / Approved | 0.1.0 | YYYY-MM-DD | e.g. M11, C2 | e.g. `tests/eval/` |

3. **Numbers are generated, never typed:** every result in a report is produced by code. The report states the **run ID, commit, benchmark version and checksum, model/provider and version, prompt version, hardware, scorer version, and timestamp** (MVP §18). Reports are generated from run output (e.g. a script that renders JSON to Markdown), not edited by hand.
4. **Keep the four quality types separate:** data, knowledge, model and answer quality get separate metrics and separate sections. Never merge them into one score without stating the method (Phase 2 §1).
5. **Gold data is reviewed:** every benchmark item records who wrote it, who reviewed it, and the source evidence it relies on. No fictional or unverifiable cases.
6. **Docs ship with code:** a change to a metric, threshold or scorer bumps the scorer version and updates the matching document in the same PR.
7. **Limitations:** every report ends with **Known limitations and threats to validity** (sample size, label noise, leakage, judge bias).
8. **Safety:** no tokens or real user data. Prompt-injection test strings are fine, but label them clearly as adversarial.

## 3. Required documents

| ID | Document | Path | Covers | Due (Phase 2 week) |
|---|---|---|---|---|
| E5-1 | Evaluation plan and metric definitions | `docs/evaluation/evaluation-plan.md` | C1–C3, M11 | Week 1 |
| E5-2 | Benchmark datasheet | `docs/evaluation/benchmark-datasheet.md` | M11, D7 | Week 1 (size agreed), Week 2 (v1.0 frozen) |
| E5-3 | Annotation and human-review guidelines | `docs/evaluation/annotation-guidelines.md` | C2, M10 (with Princess) | Week 1 |
| E5-4 | Harness user guide | `docs/evaluation/harness.md` | M11 | Week 2 |
| E5-5 | MVP baseline scorecard | `docs/evaluation/reports/baseline-v0.1.0-mvp.md` | Phase 2 baseline gate | Week 2 |
| E5-6 | Data and knowledge quality rubrics (with Anas, E2) | `docs/evaluation/quality-rubrics.md` | C4, C5 | Week 4 |
| E5-7 | Ranking methodology | `docs/evaluation/ranking-methodology.md` | C6, B5 | Week 5 |
| E5-8 | LLM comparison report | `docs/evaluation/reports/llm-comparison-<date>.md` | C2 | Week 5 (first), Week 8 (final) |
| E5-9 | Release gate and regression policy | `docs/evaluation/release-gate.md` | Acceptance criteria §11 | Week 7 |
| E5-10 | Phase 2 final evaluation report | `docs/evaluation/reports/phase2-final.md` | Week 8 release | Week 8 |

## 4. Required contents

### E5-1 Evaluation plan and metric definitions
- What is evaluated, grouped under data quality, knowledge quality, model quality and answer quality.
- For **each metric** (Recall@K, Precision@K, nDCG@K, MRR, citation validity, unsupported-claim rate, abstention correctness, IoU, Dice, P/R/F1, latency, tokens, GPU memory): the exact formula, its inputs, K values, how ties are handled, and the code function that computes it.
- Which metrics are deterministic and which need human review, and why.
- Initial thresholds, marked *provisional* until the baseline exists.

### E5-2 Benchmark datasheet
- Version, size, checksum, file paths (`datasets/evaluation/*.jsonl`) and the JSON schema (`gold_schema.json`).
- Splits (dev / validation / holdout), with counts and **leakage control** (no shared documents or chunks across splits).
- Question categories with counts: single-document, cross-document, entity-resolution, multi-hop, cross-experiment comparison, **missing-evidence** (answer not in the corpus), contradiction, and **prompt-injection**.
- Source coverage: which sources and experiments appear, and how many items each has.
- Authoring and review process, the reviewers, and the changelog of every version.

### E5-3 Annotation and human-review guidelines
- Rubric for answer correctness, evidence support and completeness, with a scale definition and anchored examples.
- **Blinded review protocol** for LLM comparisons: hidden model identity, randomised order, and the agreement measure (e.g. Cohen's kappa) with an acceptance level.
- CV mask-review rules, co-owned with Princess's `docs/cv/annotation-protocol.md` and linked from it.

### E5-4 Harness user guide
- Installation and the single command to run each suite (RAG, LLM, CV, API).
- Inputs (benchmark version, config file) and outputs (run JSON plus a rendered Markdown report), with a synthetic example of the run-record fields.
- How to compare two runs and detect regressions.
- How the harness runs in CI (with the Lead).

### E5-5 MVP baseline scorecard
- Generated from the harness on `v0.1.0-mvp`, once Phase 2 items M1, M2, M3, M6, M10 and M12 have landed.
- One section per area (retrieval, generation, citations, CV, API), each with metrics, sample sizes and confidence intervals where feasible.
- A list of failures with links to the failing items.

### E5-6 Data and knowledge quality rubrics (C4, C5)
- The C4 dimensions (provenance, completeness, integrity, consistency, scientific relevance, temporal relevance, label quality, suitability): signals, scoring rule and the data each signal needs.
- The C5 dimensions for claims, entities and relations, plus the record types (source-reported, machine-extracted, derived, model-generated, hypothesis).
- **Independent corroboration rule:** copies of the same original source don't count twice. Explain how this is detected.

### E5-7 Ranking methodology (C6)
For each of `rank_models()`, `rank_datasets()`, `rank_documents()`, `rank_evidence()` and `rank_knowledge_records()`, document:
- inputs, outputs and their schema;
- filters, minimum thresholds, weights or decision rules, and the version;
- how the ranking itself was validated.

Also document the model-promotion flow (task filter → thresholds → scientific evaluation → performance → ranking → **human approval**), and state explicitly that no single aggregate score promotes a model.

### E5-8 LLM comparison report (C2)
- All candidate LLMs, run through the M1 model router on the same benchmark and the same evidence.
- Every C2 metric per model, including abstention on missing-evidence items and output stability across repeated runs.
- Blinded human-review results, with the agreement level achieved.

### E5-9 Release gate and regression policy
- Gate metrics with thresholds, and which failures block a release (*critical scientific failures*).
- What counts as a regression, the tolerance, and who must fix it (the component owner).
- The sign-off matrix: which owner signs which area.

### E5-10 Phase 2 final evaluation report
The baseline vs final comparison for every workstream (A video, C rankings, D Graph RAG vs hybrid vs standard), the release-gate verdict, and known limitations.

## 5. Existing documents to fix

| File | Problem found in the 2026-10-10 audit | Action |
|---|---|---|
| `docs/evaluation/provenance_checklist.md` | Arabic only; claims automated thresholds and non-zero exit codes without linking code or a run | Rewrite in English with links to the code and a CI run that demonstrates each claim, or mark the claim *planned* |
| `datasets/evaluation/rag_gold.jsonl` | 6 items (2/2/2) | Expand to the size agreed in E5-2 and version it |
| `tests/eval/*.ipynb` | Notebooks act as the harness | Move the logic into importable Python modules with tests; notebooks may stay as thin drivers |
| `tests/eval/evaluation_report.json`, `tests/eval/experiment_history.json` | No run metadata (commit, checksum, model) | Regenerate with the full run record, or archive under `tests/eval/archive/` |
| `tests/eval/test_cases.jsonl` | Schema not documented | Document it in E5-2, or merge it into the versioned benchmark |

## 6. Recurring documentation

- **Weekly note**, `docs/reports/WEEKLY_Ziad.md` (append a section each week): runs executed (with run IDs), benchmark changes, regressions found and their owners, blockers, and which documents changed.
- **PR description:** the documents updated, the harness command run, and links to the generated reports.

## 7. Acceptance checklist (the Lead checks this before approving)

- [ ] Every document in §3 exists at its path, in English, with the header block and a changelog.
- [ ] Every number in every report traces to a run record with a commit and a benchmark checksum.
- [ ] The benchmark includes missing-evidence and prompt-injection items, and its splits have no leakage.
- [ ] Each ranking function has documented rules and a validation method.
- [ ] The release gate defines which failures block a release.
- [ ] Threats to validity are stated in every report.
