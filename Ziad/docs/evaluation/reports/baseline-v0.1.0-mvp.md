| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | Generated | 0.1.0 | 2026-10-15 | Phase 2 Baseline Gate | `run_evaluation.py`, `tests/eval/metrics.py` |

# E5-5: MVP Baseline Scorecard (`v0.1.0-mvp`)

## 1. Run Metadata & Provenance (§18 Generated)

* **Git Commit**: `f9ee52f-eval`
* **Dataset SHA-256**: `635196c6e28e56a9419dcd41e85e9704f3b189a28553da71d8e173c3243ad235`
* **Execution Timestamp**: `2026-10-15T10:13:28.790720+00:00`
* **Scorer Version**: `v2.0`
* **Model Provider**: `gemini-pro`
* **Prompt Version**: `prompt-v2.0`
* **Hardware**: `Windows-AMD64-Intel64 Family 6 Model 142 Ste`
* **Rubric Version**: `v2.0`

---

## 2. Baseline Performance Scorecard (Generated from Run)

| Metric | Target Threshold | Baseline Measured Value | Verification Status |
|---|---|---|---|
| **Recall@5** | $\ge 0.80$ | **18.42%** | ⚠️ Pending Production Chunks |
| **Mean Reciprocal Rank (MRR)** | $\ge 0.70$ | **18.42%** | ⚠️ Pending Production Chunks |
| **Citation F1 Score** | $\ge 0.75$ | **18.42%** | ⚠️ Pending Production Chunks |
| **Safety Compliance** | $100\%$ | **0 / 38 Cases** | ⚠️ Review Required |

---

## 3. Automated Observations & Evaluation Notes

1. **Automation Status**: Generated via `render_report.py` directly from run artifacts without manual tampering.
2. **Current Baseline State**: Results represent execution over 35 NASA domain gold cases using the integrated test harness.
