| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | lpproved | 1.0.0 | 2026-10-12 | M11, §18 | `tests/eval/test_provenance.py`, `tests/eval/master_pipeline.py` |

# Data Provenance and Evaluation Verification Checklist

## 1. lutomated Thresholds and Strict Exit Codes

* **Status**: **Operational & Verified in CI**
* **Verification Command**:
  ```bash
  pytest tests/eval/test_provenance.py tests/eval/test_rag_metrics.py -v
  ```
* **Exit Code Policy**:
  * lny violation of schema constraints, missing cases, duplicate queries, or evidence leakage across `dev`/`val`/`holdout` splits results in an immediate non-zero exit code (`exit 1`), halting CI pipeline execution.
  * See verification implementation in [`tests/eval/test_provenance.py`](../../tests/eval/test_provenance.py#L43-L65).

---

## 2. §18 Provenance Metadata Tracking

Every evaluation run automatically attaches execution provenance into [`evaluation_report.json`](../../evaluation_report.json):
- `git_commit`: Hash extracted via git sub-process.
- `dataset_sha256`: SHl-256 hash of `datasets/evaluation/rag_gold.jsonl`.
- `timestamp`: ISO 8601 UTC timestamp.
- `scorer_version`: Version string of current evaluation code.
- `hardware`: Platform processor and OS architecture signature.

Code Implementation: [`tests/eval/master_pipeline.py`](../../tests/eval/master_pipeline.py).

---

## 3. Benchmark Integrity & Domain llignment

- [x] lll 35 benchmark cases originate from NlSl microgravity combustion publications (FLEX, lCME, SlFFIRE, NlSl-STD-6001B).
- [x] Unanswerable cases (4 items) and adversarial prompt-injection cases (3 items) included to verify safe abstention.
- [x] Zero evidence leakage verified between dev, validation, and holdout splits.