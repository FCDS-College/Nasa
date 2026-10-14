# Documentation Requirements: Princess (Engineer 3, Computer Vision / PyTorch)

| | |
|---|---|
| **Phase** | Phase 2: Advanced Scientific Intelligence Platform |
| **Issued** | 2026-10-10 by the Lead (Anas) |
| **Your branch** | `Princess` (branch fresh from `main` for each task) |
| **Basis** | [Phase 2 Plan](https://github.com/FCDS-College/Nasa/blob/main/docs/plan/PHASE2_PLAN.md): §2 carry-over items **M10** (CV evaluation) and **M4** (analysis cache reuse), **Workstream A** (video), and **C1** (model registration); **Sub-phase 2H, Task 6** (Phase 2 Plan §7A); MVP Plan §5.7, §10, §18 |
| **Reviewers** | Lead (Anas) for every document. Ziad (E5) for annotation and evaluation documents. Belal (E4) for overlay and artifact formats used by the UI. |

---

## 1. Why this matters

Every number the CV pipeline produces becomes scientific evidence in the UI, so the team must be able to answer, for any measurement, what was measured, how, with which model version, and how wrong it could be. The audit on 2026-10-10 found a solid baseline: `cv/flame_cv.py` v1.1.0 provides labels, quality flags and artifacts. But segmentation accuracy is `NOT_EVALUATED`, because no ground-truth masks exist and the detector is heuristic. Phase 2 adds video and temporal measurements, which are only reproducible if frames, sampling and versions are documented exactly.

## 2. Rules for every document you write

1. **Location and format:** Markdown at the path given in §3, in English (an Arabic summary at the end is optional).
2. **Header block:** start every document with the table below.

   | Owner | Status | Version | Last updated | Plan items | Code paths |
   |---|---|---|---|---|---|
   | Princess | Draft / In review / Approved | 0.1.0 | YYYY-MM-DD | e.g. M10, A2 | e.g. `cv/flame_cv.py` |

3. **Evidence over claims:** every metric (IoU, Dice, precision/recall, latency, GPU memory) is copied from a generated report such as `cv/contracts/evaluation_report.json`. Name the run, commit, dataset manifest checksum and hardware. Never type numbers in by hand.
4. **Docs ship with code:** if a threshold, preprocessing step, feature formula or model changes, update the document and bump the version in the same PR.
5. **Versions:** state `pipelineVersion`, `segmenterVersion`, preprocessing version and `configDigest` wherever results are shown. Each document ends with a **Changelog** section.
6. **Scientific integrity:** label every measurement *observed / measured / estimated / inferred / hypothesized*. State units, and use pixels unless calibration exists. **Never claim temperature from RGB.**
7. **Limitations:** every document ends with **Known limitations and failure modes** (blur, saturation, low light, multiple flames, missing scale, and so on).
8. **Data rules:** no raw large data in git. Reference images and videos by dataset manifest ID and checksum. Use synthetic or sample-set images in examples.
9. **Diagrams:** Mermaid or ASCII. Example overlays go under `docs/cv/img/`, small and git-tracked.

## 3. Required documents

| ID | Document | Path | Covers | Due (Phase 2 week) |
|---|---|---|---|---|
| E3-1 | CV pipeline specification | `docs/cv/pipeline.md` (+ update `cv/README.md`) | MVP §10, M4 | Week 1 |
| E3-2 | Measurement definitions dictionary | `docs/cv/measurement-definitions.md` | §10, A2 | Week 2 (images), Week 4 (temporal) |
| E3-3 | Annotation protocol and ground-truth dataset (with Ziad) | `docs/cv/annotation-protocol.md` | M10, A3 | Week 1 |
| E3-4 | CV evaluation report | `docs/cv/evaluation-report.md` | M10, A3, C1 | Week 2 baseline, Week 8 final |
| E3-5 | Model cards (one per model) | `cv/models/<model-id>/MODEL_CARD.md` | C1 | Week 2, plus one per new model |
| E3-6 | Video ingestion specification | `docs/cv/video-ingestion.md` | A1 | Week 2 |
| E3-7 | Temporal analysis specification | `docs/cv/temporal-analysis.md` | A2 | Week 5 |
| E3-8 | Video analysis result contract (with Lead) | `cv/contracts/video_analysis_result.schema.json` + `docs/cv/video-contract.md` | A4 | Week 3 |
| E3-9 | Performance and GPU profile | `docs/cv/performance.md` | A3, C1 | Week 7 |

## 4. Required contents

### E3-1 CV pipeline specification
- The stage diagram: validation → letterbox preprocessing → detection → segmentation → features → confidence/flags → `AnalysisResult`, naming the function for each stage.
- Validation limits (MIME, size, pixels, decode) and what happens on rejection.
- Every configurable threshold, its default, and how it feeds `configDigest`.
- **Cache reuse (M4):** the cache-key composition (input checksum + pipeline/preprocess/segmenter/config versions), how the worker reuses an earlier result, and what invalidates it.
- Artifacts: mask, overlay and processed mask, with naming, checksum and storage location (MinIO key layout).
- How `apps/api` calls the pipeline (`flame_analysis_api_adapter`), plus the local and HF Space providers.

### E3-2 Measurement definitions dictionary
For **each** measurement (area, centroid, bounding-box aspect ratio, perimeter, circularity, symmetry, colour/intensity stats, and later temporal metrics), give:
- the name in the JSON contract, a formula or algorithm, the unit, the valid range, the label class, and the calibration requirement;
- the quality flags that make it unreliable;
- a synthetic worked example.

### E3-3 Annotation protocol and ground-truth dataset
- Mask annotation rules: what counts as flame, how glow, soot and reflections are handled, and edge policy.
- Tool, file format and naming; who annotates; who reviews; inter-annotator agreement method.
- Dataset manifest: image IDs, source and experiment, checksums, split (dev / validation / holdout), and **leakage control** (no frames from the same video across splits).
- Licensing and provenance of every image.

### E3-4 CV evaluation report
- Detection precision, recall and F1; segmentation IoU and Dice; numbers per quality-flag bucket and per source.
- **Otsu baseline vs PyTorch candidate**, compared on the same test set.
- Confidence calibration: does reported confidence track actual error?
- Failure gallery (small overlay thumbnails) with a cause for each failure.
- Run metadata: commit, manifest checksum, model digest, hardware, scorer version.

### E3-5 Model card (one per model)
All C1 registration fields: model ID, version, task, architecture, training-data provenance, evaluation dataset, configuration, hardware requirements, license, intended use, **out-of-scope uses**, known limitations, and a link to its evaluation report section.

### E3-6 Video ingestion specification (A1)
- Accepted formats, codecs, maximum size and duration, with the reason for each limit.
- Extracted metadata: fps, resolution, frame count, timestamps (source vs derived), and how variable frame rate is handled.
- Video and frame identifier scheme. Frame IDs must be stable and derivable.
- Sampling policies, with parameters and versions.
- Immutability of the original, and where derived frames and masks are stored, with their `parent` lineage.
- Status and error codes.

### E3-7 Temporal analysis specification (A2)
- Tracking method and identity rules; how frames with no detection are treated.
- Each temporal metric (area change, persistence, tracking stability, flicker frequency) with its formula and aggregation window.
- **Validity conditions** for flicker frequency: sampling rate (Nyquist), minimum duration, and signal-quality thresholds. When they are not met, return "not estimable" instead of a number.
- How every temporal result links back to frames, fps, model version and aggregation method (MVP §10, Future CV).

### E3-8 Video analysis result contract (A4)
- JSON Schema for the submission, status, results, frame-level measurements, temporal summary, artifacts and errors.
- A synthetic example payload that **validates against the schema**. Add a test that checks this.
- The versioning and backward-compatibility rule.

### E3-9 Performance and GPU profile
- Latency (p50/p95) and throughput per image and per video minute, plus GPU memory on the L40S and CPU fallback numbers.
- Batch sizes and concurrency limits that are safe next to vLLM on the same GPU (coordinate with the Lead).

## 5. Existing documents to fix

| File | Problem found in the 2026-10-10 audit | Action |
|---|---|---|
| `cv/README.md` | Accurate, but missing links to the new docs | Add links to E3-1 through E3-9 and keep the status line current |
| `cv/contracts/*.json` (examples, reports) | Examples aren't checked against `analysis_result.schema.json` in CI | Validate every example in a test; remove or regenerate stale reports |
| `cv/contracts/evaluation_report.json` | `segmentation: NOT_EVALUATED` | Regenerate once the E3-3 masks exist; summarise in E3-4 |
| `cv/contracts/training_report*.json` | No explanation of the reported numbers | Explain them in E3-4 or a model card, including the singleton-class caveat already noted in `video_training.py` |
| `cv/notebooks/*` | Notebooks are not authoritative | State at the top of each notebook which module and document is authoritative |
| Public functions in `cv/*.py` | Some lack docstrings | Docstrings with inputs, outputs, units and raised errors |

## 6. Recurring documentation

- **Weekly note**, `docs/reports/WEEKLY_Princess.md` (append a section each week): what was done (with commit and PR links), metrics changes (with run IDs), blockers, and which documents changed.
- **PR description:** the documents updated, the tests run and their output, and a before/after metric if the change touches accuracy.

## 7. Acceptance checklist (the Lead checks this before approving)

- [ ] Every document in §3 exists at its path, with the header block and a changelog.
- [ ] Every measurement in the contract has an entry in E3-2.
- [ ] Every metric links a run, commit and dataset checksum.
- [ ] The video contract example validates in a test.
- [ ] Ziad has approved the annotation protocol and evaluation report.
- [ ] Known limitations and failure modes are stated in every document.

---

## 8. Sub-phase 2H: Hybrid AI Execution (added 2026-10-10)

The Phase 2 Plan now includes **Sub-phase 2H (§7A)**: Flame must keep working when the internet or external AI services are unavailable. The Lead owns the job infrastructure, routing and persistence. **You own the CV side of Task 6: offline video and CV analysis** (P1, Week 6). The Hugging Face Space CV provider (`FLAME_CV_PROVIDER=hf_space`) counts as *external*. In Offline-Only mode, only the local pipeline may run.

### 8.1 Additional required document

| ID | Document | Path | Covers | Due (Phase 2 week) |
|---|---|---|---|---|
| E3-10 | Offline CV and video operation | `docs/cv/offline-operation.md` | 2H Task 6 | Week 6 |

**E3-10 must contain:**
- Every CV and video dependency, with how it is installed and verified offline: model weights (source, version, **checksum**, size), OpenCV and PyTorch builds, and video codecs.
- How the local provider is forced in Offline-Only mode, and what the user sees when a CV capability is missing or corrupt.
- **Resumable video jobs:** checkpointing per frame or segment, what happens after an application restart mid-job, and the recoverable states.
- Resource limits (RAM/VRAM per job, maximum resolution and duration offline), and the controlled error when limits are exceeded.
- The rule that a local LLM only interprets documented measurements and never replaces or overrides the CV computation. RGB is never calibrated temperature.
- Optional local audio extraction and transcription, if it is in scope.
- **Local CV results vs any external provider**, on the same test set, feeding the Lead's benchmark report H-7.

### 8.2 Updates to your existing documents

| Document | Add |
|---|---|
| E3-1 Pipeline specification | Provider selection (local vs HF Space) and Offline-Only behaviour |
| E3-5 Model cards | Offline install and verify steps, checksum, CPU-only viability |
| E3-6 Video ingestion | Local storage paths, and resumable ingestion with job state |
| E3-9 Performance | CPU-only and offline numbers next to the L40S numbers |

### 8.3 Contributions to the Lead's handoff package

- **H-1 (dependency audit):** sign off the CV rows.
- **H-3 (local model registry):** supply the entries for every CV model, and sign off the CV section.

### 8.4 Acceptance (added to §7)

- [ ] E3-10 exists.
- [ ] A locally stored video is processed with the network disconnected, after the documented install.
- [ ] A restart mid-job ends in a resumed or clearly recoverable state (Phase 2 Plan §7A.8).
