# Weekly Progress Note: Ziad (Engineer 5, Evaluation / Research Intelligence)

## Week Ending 2026-10-19 (Phase 2 Iteration)

### 1. Completed Runs & Benchmarks
* **Run ID**: `RUN_HARNESS-SELFTEST_20261019_010000` (Harness Self-Test Mode)
* **Gold Benchmark Overhaul (B1, R3)**: Rebuilt `datasets/evaluation/rag_gold.jsonl` to strictly align with ingested corpus registries (`FF-PSI-69`, `FF-PSI-25`, `FF-PSI-98`, `FF-PSI-107`, `FF-NASA-CLD`, `FF-NASA-FLEX2`, `FF-NIST-WEBBOOK`, `FF-NTRS-01/02/03`). Every answerable item includes real author, reviewer (`Anas`), source locator, and verbatim text.
* **Schema Conformity (§18 Standard)**: Aligned all records with `id`, `expected_evidence_ids`, and `source_scope`.
* **Zero Leakage**: Strict disjoint partitioning between `dev`, `validation`, and `holdout` verified by `test_no_document_leakage` (zero cross-split overlap).

### 2. Code & Test Improvements
* **B2 (Honest Provenance)**: Removed hard-coded fallback `f9ee52f-eval`. Returns `unknown` when git metadata is missing and alerts gate to fail unverified releases.
* **B4 (Real API Connector)**: Refactored `rag_connector.py` to invoke `GET /api/search?q=...&page_size=...` for retrieval chunk mapping (`result_id`, `evidence_id`) and `POST /api/chat` for generation/citations. Configured to explicitly raise `RuntimeError` on HTTP failures rather than swallowing errors.
* **R1 (API Contract Gates)**: Un-skipped all 5 contract tests in `tests/eval/test_api_contracts.py` and validated against FastAPI TestClient.
* **B5 (Offline Testing)**: Updated `docs/evaluation/offline-testing.md` to map all 13 scenarios from Phase 2 Plan §7A.8 to specific test targets and execution statuses.
* **B6 (Local vs Cloud Benchmark)**: Renamed to `docs/evaluation/local-vs-cloud-benchmark.md`, removed typed speculative figures, and established purely reproducible methodology and acceptance thresholds.
* **R4 (Workflow Cleanliness)**: Deleted standalone root `.github/workflows/eval.yml` to prevent conflict with repository `ci.yml`.

### 3. Deliverables Status Summary
* `E5-1`: Complete formulas and mathematical definitions.
* `E5-2`: Datasheet with 38 cases (14 dev / 14 val / 10 holdout) and zero leakage verification.
* `E5-3`: Human annotation and blinded review protocol.
* `E5-4`: Harness user guide with separate RAG, CV, LLM, and API command suites.
* `E5-11`: Offline testing protocol with 13 §7A.8 operational scenarios.
* `E5-12`: Local-vs-Cloud benchmark methodology.

### 4. Blockers & Dependencies
* **Dependency (Engineer 1 / Anas)**: To run the production `--model api` baseline, awaiting full ingestion chunk database deployment on the staging host.
* **Dependency (Princess / E3)**: Ground-truth flame segmentation masks for production IoU scoring.
