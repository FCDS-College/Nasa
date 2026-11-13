| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | Approved | 1.0.0 | 2026-10-12 | M11, §18 | `tests/eval/test_provenance.py`, `tests/eval/master_pipeline.py` |

# Data Provenance and Evaluation Verification Checklist

## 1. Automated Thresholds and Strict Exit Codes

* **Status**: **Partly operational.** `pytest` runs the schema, coverage and (page-level) leakage tests in CI. `run_evaluation.py` is not run in CI and has no exit-code policy (its only `sys.exit(1)` is for a missing dataset file).
* **Verification Command**:
  ```bash
  pytest tests/eval/test_provenance.py tests/eval/test_rag_metrics.py -v
  ```
* **Exit Code Policy**:
  * A failing `pytest` test in `tests/eval/test_provenance.py` fails the CI job. Duplicate-query detection is not implemented there, and document-level leakage is a known strict expected failure.
  * See verification implementation in [`tests/eval/test_provenance.py`](../../tests/eval/test_provenance.py#L43-L65).

---

## 2. §18 Provenance Metadata Tracking

Every evaluation run automatically attaches execution provenance into [`evaluation_report.json`](../../evaluation_report.json):
- `git_commit`: Hash extracted via git sub-process.
- `dataset_sha256`: SHA-256 hash of `datasets/evaluation/rag_gold.jsonl`.
- `timestamp`: ISO 8601 UTC timestamp.
- `scorer_version`: Version string of current evaluation code.
- `hardware`: Platform processor and OS architecture signature.

Code Implementation: [`tests/eval/master_pipeline.py`](../../tests/eval/master_pipeline.py).

---

## 3. Benchmark Integrity & Domain Alignment

- [ ] The 38 benchmark cases originate from NASA microgravity combustion publications (FLEX, ACME, SAFFIRE, NASA-STD-6001B). Not verifiable from this repository: the evidence IDs are not documents of the indexed corpus.
- [x] Unanswerable cases (4 items) and adversarial prompt-injection cases (3 items) included to verify safe abstention.
- [ ] No document leakage between splits. **Known issue:** the splits share documents (dev and holdout share `DOC-001`, `DOC-004`, `DOC-007`); only page-level IDs are disjoint. See `test_no_document_leakage_between_splits` (strict xfail).