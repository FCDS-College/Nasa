| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | Generated | 0.1.0 | 2026-10-12 | Phase 2 Baseline Gate | `run_evaluation.py`, `tests/eval/metrics.py` |

# E5-5: MVP Baseline Scorecard (`v0.1.0-mvp`)

## 1. Run Metadata & Provenance (§18 Generated)

* **Git Commit**: `git-not-available`
* **Dataset SHA-256**: `013e1738a85e5da9bd4d096b989f3a231e774c9d334748d3137cc8ae95211dd2`
* **Execution Timestamp**: `2026-10-12T20:54:24.191263+00:00`
* **Scorer Version**: `v2.0`
* **Model Provider**: `gemini-pro`
* **Prompt Version**: `prompt-v2.0`
* **Hardware**: `Windows-AMD64-Intel64 Family 6 Model 142 Ste`
* **Rubric Version**: `v2.0`

---

## 2. Baseline Performance Scorecard (Generated from Run)

| Metric | Target Threshold | Baseline Measured Value | Verification Status |
|---|---|---|---|
| **Recall@5** | $\ge 0.80$ | **21.05%** | ⚠️ Pending Production Chunks |
| **Mean Reciprocal Rank (MRR)** | $\ge 0.70$ | **21.05%** | ⚠️ Pending Production Chunks |
| **Citation F1 Score** | $\ge 0.75$ | **21.05%** | ⚠️ Pending Production Chunks |
| **Safety Compliance** | $100\%$ | **0 / 38 Cases** | ⚠️ Review Required |

---

## 3. Automated Observations & Evaluation Notes

1. **Automation Status**: Generated via `render_report.py` directly from run artifacts without manual tampering.
2. **Current Baseline State**: Results represent execution over 35 NASA domain gold cases using the integrated test harness.
