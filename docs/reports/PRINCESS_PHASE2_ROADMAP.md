# Princess Phase 2 Roadmap

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 0.2.0 | 2026-10-14 | M10, M4, Workstream A, C1, Sub-phase 2H Task 6 | `cv/`, `docs/cv/`, `tests/cv/` |

**Basis:** [Princess Documentation Requirements](./DOC_REQUIREMENTS_Princess.md), including the Sub-phase 2H additions. This roadmap is a work-tracking view of those requirements, not a replacement for the Phase 2 Plan.

## 1. Goal

Complete Princess's Phase 2 computer-vision responsibilities with a tested, versioned image pipeline; an evidence-backed evaluation; video and temporal analysis deliverables; registered model documentation; performance evidence; and documented, verified offline operation.

## 2. Current checkpoint

### Completed in the current branch

- [x] Restored the image-analysis API, cache, artifact generation, evaluation helpers, and manifest functions in `cv/flame_cv.py`.
- [x] Reintegrated adaptive preprocessing and segmentation configuration; updated the pipeline and model version metadata.
- [x] Added adaptive-parameter coverage and updated CV tests.
- [x] Moved the CV documentation into `docs/cv/`, corrected `pipeline.md`, moved the baseline model card under `cv/models/`, and linked E3-1 through E3-9 from `cv/README.md`.
- [x] Removed the redundant root-level requirements document; the canonical requirements remain at `docs/reports/DOC_REQUIREMENTS_Princess.md`.
- [x] Added the `python -m cv.flame_cv` CLI, an offline manifest and verifier with wheel checksums, a draft `docs/cv/offline-operation.md`, a schema-validated video-contract fixture, and `WEEKLY_Princess.md`. CNN/PINN prototypes live in `cv/` but are optional and unvalidated.
- [x] Verified ``python -m pytest tests/cv`` (37 passed; 25 before the offline/CLI/contract tests) and `apps/api/tests/test_cv_adapter.py` (1 passed). These checks validate code integration, not scientific performance or Phase 2 acceptance.

### Still open

- [ ] Ground-truth masks, reviewed dataset manifest, and leakage-controlled splits.
- [ ] Final quantitative CV evaluation and reviewer sign-offs.
- [ ] Automated validation of all applicable committed examples (the video contract fixture is now validated; `docs/cv/video-contract.md` and `cv/contracts` examples are not).
- [ ] Implemented video ingestion and temporal analysis; current specifications describe intended behavior, not an implemented processing pipeline.
- [ ] Empirical performance measurements with reproducible run metadata.
- [ ] E3-10 offline/resume verification (draft doc and verifier exist; restart recovery and offline video processing untested), and CV contributions to Lead handoff items H-1, H-3, and H-7.

## 3. Remaining roadmap

The weeks below follow the sequence and due-week labels in the requirements document. They are delivery checkpoints, not claims about calendar scheduling.

### Checkpoint A — Complete the image-pipeline documentation and contracts (Weeks 1–3)

- [ ] **E3-1 / M4:** Bring `docs/cv/pipeline.md` into exact alignment with the restored implementation. Document actual entry points, each stage's function, validation and rejection behavior, all configuration defaults and their digest behavior, cache reuse/invalidation, artifact names and storage layout, and provider selection. Do not describe MinIO or HF Space integration as implemented until verified in code.
- [ ] **E3-2:** Add synthetic worked examples for each image measurement. Confirm JSON field names, units, valid ranges, calibration needs, and quality flags against the live result schema. Add temporal definitions when those metrics are implemented.
- [ ] **E3-3 / M10:** Work with Ziad to complete annotation assignments, review workflow, inter-annotator agreement method, source licensing/provenance, checksummed manifest, and group-based train/validation/holdout split. Ensure frames from one video or experiment cannot leak across splits.
- [ ] **E3-8 / A4:** Align the schema and contract documentation. Extract or maintain one synthetic payload as a fixture and add an automated test that validates it against `cv/contracts/video_analysis_result.schema.json`. Specify versioning and backward compatibility.
- [ ] **Existing artifacts:** Validate applicable committed examples against their schemas. Regenerate stale reports only from actual evaluation runs; avoid committing machine-specific absolute paths in reusable examples.
- [ ] **Notebook authority:** State at the top of each in-scope CV notebook/export which source module and document are authoritative.

**Exit criteria:** documentation describes the current code rather than a planned design; contract examples pass schema validation; no metric is presented without its run, commit, dataset checksum, and hardware metadata.

### Checkpoint B — Establish ground truth and evaluate the baseline (Weeks 2 and 8)

- [ ] Annotate the agreed set of images across multiple distinct tests/experiments with Ziad; record provenance, licensing, checksums, split, and review status.
- [ ] Choose and document an acceptance threshold with the Lead and Ziad before reporting a pass/fail verdict.
- [ ] Run the baseline evaluation on the held-out groups. Report detection precision, recall, and F1; segmentation IoU and Dice; results by quality-flag bucket and source; and run metadata including commit, dataset manifest checksum, model/config digest, hardware, and scorer version.
- [ ] Assess confidence calibration against observed errors; distinguish heuristic confidence from calibrated probabilities.
- [ ] Add a small failure gallery with a documented cause for each included case.
- [ ] Update `cv/contracts/evaluation_report.json`, E3-4, and the baseline model card from generated outputs. Keep segmentation marked `NOT_EVALUATED` until valid ground truth and a completed scoring run exist.
- [ ] Obtain Ziad's approval of the annotation protocol and evaluation report, and the Lead's review.

**Exit criteria:** results are reproducible from a named dataset manifest and evaluation run, and the verdict is based on the pre-agreed threshold rather than hand-entered values.

### Checkpoint C — Implement and specify video and temporal analysis (Weeks 2–5)

- [ ] **E3-6 / A1:** Implement or integrate video ingestion. Verify supported formats/codecs and size/duration limits; capture fps, dimensions, frame count, and source/derived timestamps; handle variable frame rates according to the chosen policy; preserve original immutability; and record stable frame IDs and parent lineage.
- [ ] **E3-7 / A2:** Implement tracking and temporal aggregation with explicit identity and missing-detection behavior. Calculate documented area-change, persistence, tracking-stability, and flicker metrics using their stated windows.
- [ ] Enforce flicker validity conditions: appropriate sampling/Nyquist rate, minimum duration, and signal-quality thresholds. Return “not estimable” when those conditions are not satisfied.
- [ ] **E3-8 / A4:** Connect frame-level and temporal outputs to the versioned video result contract. Include status/errors, artifacts, lineage, and source-frame references.
- [ ] Update E3-2 with implemented temporal metric definitions and synthetic examples. Ensure results carry pipeline/model versions, fps, source frames, and aggregation configuration.
- [ ] Add focused tests for ingestion metadata, stable IDs, timestamps/VFR behavior, temporal metrics, missing frames, validity rules, and contract validation.
- [ ] Coordinate artifact and overlay formats used by the UI with Belal and contract/API changes with the Lead.

**Exit criteria:** a sample video can be ingested and analyzed end-to-end with traceable frame lineage, tested output contracts, and invalid temporal measurements represented as not estimable.

### Checkpoint D — Register models and provide empirical performance evidence (Weeks 2–7)

- [ ] **E3-5 / C1:** Maintain one model card per model at `cv/models/<model-id>/MODEL_CARD.md`, covering provenance, evaluation, configuration, hardware, license, intended and out-of-scope use, limitations, and the corresponding evaluation section.
- [ ] For each model, document offline installation and verification, weight source/version/checksum/size where weights exist, and whether CPU-only execution is viable.
- [ ] Do not register an untrained CNN/PINN prototype as a validated production model. If a learned PyTorch segmenter is pursued, agree on scope and data first, train only against approved splits, and compare it with the Otsu baseline on the same held-out test set.
- [ ] **E3-9 / A3, C1:** Benchmark actual image and video workloads. Report p50/p95 latency, throughput, GPU memory on the specified hardware, CPU fallback, and per-video-minute throughput. Save run IDs, commit, dataset checksum, configuration/model digests, and hardware details.
- [ ] Coordinate safe batch/concurrency limits with the Lead for operation alongside vLLM. Replace illustrative or estimated numbers in documentation with generated benchmark evidence, clearly labelling any estimates.
- [ ] Document singleton-class and other training-report caveats where training results are presented.

**Exit criteria:** every registered model is traceable to its evidence and declared scope; performance figures can be reproduced from recorded runs.

### Checkpoint E — Deliver offline CV operation and handoff (Sub-phase 2H, Week 6)

- [ ] **E3-10:** Create `docs/cv/offline-operation.md` with every CV/video dependency, offline installation and verification procedures, weight checksums/sizes, OpenCV/PyTorch builds, codecs, local-provider enforcement, missing/corrupt capability behavior, resource limits, and controlled errors.
- [ ] Specify resumable video processing checkpoints, restart behavior, and recoverable job states in coordination with the Lead's job infrastructure.
- [ ] State that local language models may interpret documented measurements but cannot replace or override CV computation; RGB does not establish calibrated temperature.
- [ ] Record whether local audio extraction/transcription is in scope; if it is not, state that explicitly.
- [ ] Update E3-1 provider selection/offline behavior, E3-5 offline install details, E3-6 local paths and resumability, and E3-9 CPU/offline measurements.
- [ ] **H-1:** Review and sign off the CV dependency-audit entries.
- [ ] **H-3:** Supply and sign off the CV model-registry entries.
- [ ] **H-7:** Provide local-versus-external-provider comparison results on the same test set, with reproducible metadata.
- [ ] Verify a locally stored video can be processed with network access disabled after following the documented installation steps.
- [ ] Test an application restart during processing and confirm the job resumes or enters a clearly documented recoverable state.

**Exit criteria:** offline-only execution demonstrably avoids external CV providers, and restart recovery is tested rather than asserted.

### Checkpoint F — Closeout and acceptance (Week 8)

- [ ] Complete the final held-out evaluation and publish the evidence-backed E3-4 report.
- [ ] Update all changed document versions/changelogs alongside code and configuration changes.
- [ ] Ensure every required E3 document, including E3-10, exists at its specified path, contains the prescribed header/changelog/limitations, and links to implemented behavior.
- [ ] Complete the acceptance checklist in `docs/reports/DOC_REQUIREMENTS_Princess.md`.
- [ ] Obtain sign-offs: Lead for all documents; Ziad for annotation/evaluation; Belal for UI artifact/overlay format where relevant.
- [ ] Maintain `docs/reports/WEEKLY_Princess.md` with work, commits/PRs, metric run IDs, blockers, and document changes.
- [ ] In the PR description, list updated documents, targeted tests and outputs, and before/after metrics when accuracy behavior changes.

**Exit criteria:** all acceptance items have evidence or are explicitly reported as blocked, with reviewer sign-offs and no unsupported accuracy claims.

## 4. Dependencies and review ownership

| Work | Depends on | Review / coordination |
|---|---|---|
| Ground-truth evaluation | Approved annotations, checksummed manifest, leakage-controlled split | Ziad and Lead |
| Learned-segmenter comparison | Approved training data and baseline evaluation protocol | Lead; Ziad for data/evaluation |
| Video contract/API integration | Agreed contract fields and API integration points | Lead |
| UI artifact and overlay behavior | Stable artifact names/formats and sample outputs | Belal |
| Offline resumability | Lead-owned job persistence, routing, and state infrastructure | Lead |
| Performance/concurrency limits | Reproducible benchmark environment and shared-GPU requirements | Lead |

## 5. Scope boundaries

- The Lead owns job infrastructure, routing, and persistence for Sub-phase 2H; Princess owns CV dependency, provider, processing, and result-contract contributions described above.
- Do not claim segmentation accuracy until scored against reviewed ground truth.
- Do not claim temperature from RGB values without the required physical calibration.
- CNN/PINN prototypes are not accepted as production CV capabilities solely because source files exist; registration and comparison require agreed scope, suitable validated data, tests, and evidence.
- Video features described in specifications remain planned until code and tests demonstrate them.

## Known limitations and failure modes

- The current Otsu/contour detector is heuristic; reflections, saturation, low light, blur, multiple flames, occlusion, or missing calibration can undermine measurements.
- Scientific evaluation remains limited until reviewed ground truth spans independent tests/experiments and held-out groups.
- Video and temporal behavior, offline execution, and restart recovery require implementation and integration tests; documentation alone is not evidence of completion.
- Hardware-specific performance and safe concurrency cannot be generalized without reproducible measurements on the target systems.
- Dates and week numbers are copied from the requirements' planning sequence; the source does not establish a revised calendar schedule.

## Changelog

- **0.2.0 (2026-10-14):** Recorded CLI, offline manifest/verifier, E3-10 draft, video fixture test and weekly note; test count updated to 37.
- **0.1.0 (2026-10-13):** Initial remaining-work roadmap based on Princess Phase 2 documentation requirements and current branch evidence.
