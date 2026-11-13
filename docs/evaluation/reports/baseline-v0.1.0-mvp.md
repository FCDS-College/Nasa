| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | Generated | 0.1.0 | 2026-11-13 | Phase 2 Baseline Gate | `run_evaluation.py`, `tests/eval/metrics.py` |

# E5-5: MVP Baseline Scorecard (`v0.1.0-mvp`)

> **Evaluated system: `mock`.** Hard-coded outputs of tests/eval/mock_rag.py: this scores the evaluation harness, not Flame.

## 1. Run Metadata & Provenance (§18 Generated)

* **Git Commit**: `7bd6bf5a04c10dc4513c62cd75f3d759b06b3ec1`
* **Dataset SHA-256**: `013e1738a85e5da9bd4d096b989f3a231e774c9d334748d3137cc8ae95211dd2`
* **Execution Timestamp**: `2026-11-13T15:44:06.956637+00:00`
* **Scorer Version**: `v2.0`
* **Model Provider**: `gemini-pro`
* **Prompt Version**: `prompt-v2.0`
* **Hardware**: `Linux-x86_64-x86_64`
* **Rubric Version**: `v2.0`

---

## 2. Baseline Performance Scorecard (Generated from Run)

| Metric | Target Threshold | Measured value (of the evaluated system above) | Verification Status |
|---|---|---|---|
| **Recall@5** | $\ge 0.80$ | **3.23%** | ⚠️ Below target |
| **Mean Reciprocal Rank (MRR)** | $\ge 0.70$ | **3.23%** | ⚠️ Below target |
| **Citation F1 Score** | $\ge 0.75$ | **3.23%** | ⚠️ Below target |
| **Safety Compliance** | $100\%$ | **0 / 38 Cases** | ⚠️ Review Required |

---

## 3. Automated Observations & Evaluation Notes

1. **Automation Status**: Generated via `render_report.py` directly from run artifacts without manual tampering.
2. **What was evaluated**: Hard-coded outputs of tests/eval/mock_rag.py: this scores the evaluation harness, not Flame. Cases: 38 (31 answerable, 7 unanswerable); retrieval means are over answerable cases only.
3. **Caveats**:
   * Abstention correctness on unanswerable cases is not computed.
   * Evidence IDs in rag_gold.jsonl (e.g. DOC-001-P15) are not documents of the indexed corpus.
   * Means are over answerable cases only; there are no confidence intervals.
