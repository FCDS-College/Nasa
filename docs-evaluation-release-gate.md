| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.1.0 | 2026-10-12 | Acceptance criteria §11 | `tests/eval/master_pipeline.py`, `tests/eval/test_rag_metrics.py` |

# E5-9: Release Gate and Regression Policy

## 1. Release Gate Criteria

A candidate version cannot be promoted to release or merged to `main` unless it satisfies all gate criteria:

| Area | Mandatory Metric | Threshold | Blocking Level |
|---|---|---|---|
| **Retrieval** | Recall@5 | $\ge 0.80$ | Blocker |
| **Retrieval** | MRR | $\ge 0.70$ | Blocker |
| **Faithfulness** | Unsupported-Claim Rate | $\le 0.05$ | Critical Scientific Failure |
| **Safety** | PII Masking Precision | $1.00$ | Critical Compliance Failure |
| **Safety** | Adversarial Holdout Defense | $100\%$ refusal/abstention | Critical Compliance Failure |
| **CV Segmentation**| IoU (Flame core) | $\ge 0.70$ | Blocker |
| **API Backend** | 200 OK on core endpoints | $100\%$ contract pass | Blocker |

---

## 2. Regression Policy and Tolerances

* **Performance Regression**: A drop of more than $2\%$ on any retrieval or generation metric compared to the frozen baseline triggers a build failure.
* **Component Owner Responsibility**:
  * Retrieval drop $\to$ Engineer 1 (Eman)
  * Extraction/data quality drop $\to$ Engineer 2 (Anas)
  * CV / Segmentation drop $\to$ Engineer 3 (Princess)
  * Evaluation harness / gate defect $\to$ Engineer 5 (Ziad)

---

## 3. Sign-off Matrix

Every release requires formal sign-off from component leads:
* **Lead / Platform Architect**: Anas
* **RAG & Model Intelligence**: Eman
* **Computer Vision Lead**: Princess
* **Evaluation & Benchmark Lead**: Ziad
