# Phase 2 Review: Princess (Engineer 3, Computer Vision / PyTorch)

**Reviewed:** branch `Princess` @ `06c26d5` (commits `0a6b053` "Update workspace changes" and `06c26d5` "Add new files and updates pinn cnn", 2026-10-12/13)
**Basis:** [`DOC_REQUIREMENTS_Princess.md`](DOC_REQUIREMENTS_Princess.md) (issued 2026-10-10), including §8 Sub-phase 2H
**Review date:** 2026-10-13 (Phase 2, Week 1)

**Verification (run from the repo root):**

| Check | Before (`e74fa5f`, parent of the update) | After (`06c26d5`) |
|---|---|---|
| `python -m pytest tests/cv` | 22 passed, 1 failed (`test_artifact_paths_are_repo_relative`, known) | **Collection error: 0 tests run.** `ImportError: cannot import name 'AnalysisCache' from 'cv.flame_cv'` |
| `from cv.flame_cv import analyze_image` (used by `apps/api/flame_api/worker.py:46`) | OK | **`ImportError`.** The API worker cannot run a CV job. |
| Video contract example in `docs/CV/video-contract.md` against `video_analysis_result.schema.json` | n/a | Validates. A nonsense payload (`persistenceRate: 5`, `flickerFrequencyHz: "banana"`) also validates. |

## Verdict: 4 / 10. Not mergeable yet.

Princess produced a draft of all nine required documents within three days, and several are good starting points. However, the same update **breaks the CV pipeline that the API depends on**, and the most important rule in the requirements (*evidence over claims*) is not met. The documentation also describes code that the update removed.

| Area (requirements section) | Weight | Score | Why |
|---|---|---|---|
| Coverage: documents exist with header, changelog and limitations (§2.2, §2.5, §2.7, §3) | 20% | 7 / 10 | 9 of 9 drafted, every one has the header block, changelog and limitations. Two are at the wrong path and the folder is `docs/CV` instead of `docs/cv` (see below). |
| Content completeness against §4 | 25% | 4 / 10 | Skeletons cover the headings, but most required specifics are missing (see the per-document table). |
| Evidence and scientific integrity (§2.3, §2.5, §2.6, §2.8) | 25% | 3 / 10 | E3-9 numbers have no run behind them and include GPU memory for a CPU-only OpenCV pipeline. E3-4 has no commit, manifest checksum or hardware, and contains 16 pasted `[cite: 7]` markers. |
| Code and "docs ship with code" (§2.4, §5) | 20% | 1 / 10 | `cv/flame_cv.py` lost 18 public functions and classes, all CV tests fail at import, measurements are no longer computed, and the new TensorFlow CNN/PINN files have no tests, docs or model cards. |
| Process (§5 fixes, §6 weekly note and PR description) | 10% | 2 / 10 | No weekly note, no PR, commits authored as `unknown` with no description, a 1,060-line copy of the old module committed to `cv/oldversion/`. |
| **Weighted total** | | **≈ 4 / 10** | |

## 1. Blocking defects (fix before anything else)

| # | Finding | Evidence | Required action |
|---|---|---|---|
| B1 | **The rewrite of `cv/flame_cv.py` deleted the public API.** Removed: `analyze_image`, `analyze_image_safe`, `flame_analysis_api_adapter`, `AnalysisCache`, `make_cache_key`, `IntakeManifest`, `ingest_image`, `run_cv_evaluation`, `segmentation_metrics`, `split_for_group`, `_geometry`, `_appearance`, `_bbox_original`, `_write_artifacts`, `export_schemas`, `make_synthetic_flame`, `JsonlStore`, `SourceInfo`. The file is 513 lines (was 1,086); its last function is the private `_compute`, so there is no public entry point left. | `tests/cv/test_flame_cv.py` fails at import. `apps/api/flame_api/worker.py:46` imports `analyze_image`. | Restore every removed symbol. Add the auto-adaptive changes (`compute_auto_target_size`, `compute_auto_blur_kernel`, dynamic thresholds) **on top of** the v1.1.0 code, not instead of it. All 22 previously passing tests must pass again. |
| B2 | **Measurements are no longer produced.** `_compute` returns `measurements=Measurements()` (all `None`) and an empty `BoundingBox()`. No mask or overlay artifact is written. | `cv/flame_cv.py:497-500` | Restore `_geometry`, `_appearance`, `_bbox_original`, `_write_artifacts`. E3-2 currently documents values the code does not return. |
| B3 | **The cache (M4) was removed while E3-1 documents it.** E3-1 §4 describes the cache key and invalidation, but `AnalysisCache` and `make_cache_key` no longer exist. | `docs/CV/pipline.md` §4 | Restore the cache. Make E3-1 describe the code as it is, naming each function. |
| B4 | **Version bump without evidence.** `PIPELINE_VERSION` is now `cv-opencv-v1.2.0-auto` and `SEGMENTER_VERSION` is `1.2.0`, but the evaluation report, model card (1.1.0) and `configDigest 5140c618f88cd05b` are all from v1.1.0. The new thresholds change the detector's behaviour with no before/after numbers. | `cv/flame_cv.py:26-30`, `cv/contracts/evaluation_report.json` | Re-run `run_cv_evaluation` on v1.2.0 and report v1.1.0 vs v1.2.0 side by side (§6 PR description: "before/after metric if the change touches accuracy"). |

## 2. Per-document review

| ID | Document | Path required / delivered | Score | What is good | What is missing or wrong |
|---|---|---|---|---|---|
| E3-1 | CV pipeline specification | `docs/cv/pipeline.md` / **`docs/CV/pipline.md`** (wrong folder case and misspelled) | 4 / 10 | ASCII stage diagram naming functions; validation limits listed. | The code fence is never closed, so everything after §1 renders as broken text. Thresholds are not listed with their defaults. No MinIO key layout. No section on `flame_analysis_api_adapter` or the local / HF Space providers. Describes the cache and artifacts that B1 removed. The §8.2 Offline-Only provider rule is missing. `cv/README.md` links to `docs/cv/pipeline.md`, which does not exist (broken on GitHub and Linux). |
| E3-2 | Measurement definitions | `docs/cv/measurement-definitions.md` / `docs/CV/...` | 6 / 10 | **The strongest document.** Formulas match the v1.1.0 code exactly (area ÷ scale², moments centroid, `minAreaRect` elongation, flip-IoU symmetry). Units, ranges, label classes and flags are given, and it says RGB is not temperature. | **No synthetic worked example for any measurement** (required for each). Missing contract fields: `boundingBox`, `intensityP5/P50/P95`, `equivalentDiameterMm`, and the quality metrics (`boundaryGradient`, `flameContrast`, `clippedFraction`, `brightnessP995`). |
| E3-3 | Annotation protocol | `docs/cv/annotation-protocol.md` / `docs/CV/...` | 4 / 10 | Sensible flame / glow / reflection rules; split by `groupId` to stop leakage; `_mask.png` naming. | The tool is not named ("standardized polygon/brush tool"). Annotators are not named. No inter-annotator IoU threshold value. No manifest example, image IDs or checksums. Licensing is one sentence with no per-source licence. **Not yet approved by Ziad** (§7). |
| E3-4 | CV evaluation report | `docs/cv/evaluation-report.md` / `docs/CV/...` | 3 / 10 | Numbers match `evaluation_report.json` (10 images, 100% PRESENT, saturation 1.0, low light 0.1) and are honestly reported as `NOT_EVALUATED`. | **16 `[cite: 7]` markers pasted from a chat tool.** Run metadata is missing: commit, manifest checksum, hardware, scorer version. The numbers are for v1.1.0, but the code is now v1.2.0. No precision/recall/F1 plan, no Otsu vs PyTorch section, no calibration analysis, no failure gallery. `training_report*.json` is not explained (§5). |
| E3-5 | Model card | `cv/models/<model-id>/MODEL_CARD.md` / **`cv/MODEL_CARD.md`** (wrong path) | 5 / 10 | Good out-of-scope uses (no temperature from RGB, no safety-critical use without review) and limitations. | Wrong path. Card version 1.1.0 vs code `SEGMENTER_VERSION = "1.2.0"`. No licence, no configuration listing, no link to the E3-4 section, 3 `[cite: 7]` markers. **No model cards for the new CNN and PINN** (§3: "one per new model"). |
| E3-6 | Video ingestion | `docs/cv/video-ingestion.md` / `docs/CV/...` | 4.5 / 10 | Stable derivable frame IDs (`{videoId}_frame_{index:06d}`), content-hash `videoId`, immutable original. | **Scientific-integrity issue:** "VFR streams are normalized to CFR via temporal interpolation". Interpolated frames are synthetic, not observed, and would corrupt temporal metrics. Keep source timestamps and resample measurements instead, labelling them *derived*. Limits (500 MB, 10 min) have no stated reason. The sampling policy has no parameters or version. No status or error code list. No storage paths (§8.2). |
| E3-7 | Temporal analysis | `docs/cv/temporal-analysis.md` / `docs/CV/...` | 5.5 / 10 | Correct "not estimable" fallback, Nyquist condition and exclusion of blurred or clipped frames. | Thresholds are examples, not specified values ("e.g. ≥ 2.0 s"; "a defined threshold" for track gaps). No aggregation window sizes. No formula for persistence or stability windows. No minimum SNR for flicker. |
| E3-8 | Video result contract | schema + `docs/cv/video-contract.md` / schema + `docs/CV/...` | 3.5 / 10 | Schema exists; example validates. | **No test** (§4 and §7 require one). The code fence is not closed. The schema is too loose: no `additionalProperties: false`, no ranges (`persistenceRate` ≤ 1), and `flickerFrequencyHz` accepts any string rather than only `"not estimable"`. Missing: submission and status states (`QUEUED/RUNNING`), an `errors` block, per-frame artifacts, `segmenterVersion`, `configDigest` and sampling policy. The example uses a Windows absolute path (`C:/FCDS/...`) and a fake checksum, contrary to §2.8 and the MVP review finding #4. |
| E3-9 | Performance and GPU profile | `docs/cv/performance.md` / `docs/CV/...` | 1 / 10 | Has the right headings. | **Every number lacks a run ID, commit or hardware log, so this violates §2.3.** The pipeline is pure OpenCV/NumPy on the CPU, so "1.2–2.1 GB VRAM on L40S" and "3.5x slower on CPU" cannot have been measured. The vLLM co-existence section has no actual limits. Replace it with numbers from a committed benchmark script, or mark it *TBD — not measured*. |
| E3-10 | Offline CV operation (2H) | `docs/cv/offline-operation.md` | n/a | Not due until Week 6. | Not started (expected). |

## 3. New code in `06c26d5` (`cv/CNN.py`, `cv/PINN.py`) and `cv/videoCNN/models.ipynb`

| # | Finding |
|---|---|
| C1 | **Wrong framework.** The role and the plan are PyTorch. Both files use TensorFlow/Keras, which is not in any requirements file, so they cannot be imported in CI or the API image. The notebook uses PyTorch, so the branch now mixes both. |
| C2 | **`run_cnn_pipeline` does not train or evaluate anything.** It lists files, splits them, and returns `"status": "SUCCESS"` with counts. `build_dynamic_cnn` and `load_cnn_dataset_from_directory` are never called. |
| C3 | **Bug:** with the default `num_classes=2`, the output layer is `Dense(2, activation='sigmoid')` with `binary_crossentropy`, but `image_dataset_from_directory` yields integer labels of shape `(n,)`. That is a shape mismatch at `fit`. Use `Dense(1)` for binary, or softmax with sparse categorical cross-entropy. |
| C4 | **Leakage:** `dynamic_train_test_split` shuffles individual files at random. This is exactly what §4 E3-3 forbids ("no frames from the same video across splits"). Reuse `split_for_group`. |
| C5 | **PINN scientific scope.** `PINN.py` fits the 1-D heat equation with an arbitrary `thermal_diffusivity = 0.01` and is described as "Flame/Thermal Physics". There is no stated data source for `u`. If `u` comes from image intensity, this is a temperature claim from RGB (§2.6). It needs a design note, a model card and the Lead's approval before it goes further. |
| C6 | No tests, no docstrings with units or raised errors (§5), and no model card for either model (§2.4, E3-5). |
| C7 | The notebook hard-codes `C:\Program Files\Tesseract-OCR\tesseract.exe`, contains `pip install` output with local `c:\users\princess\...` paths, and has no "not authoritative" header (§5). Its whisper/OCR telemetry work is unrelated to the documents above and is not mentioned in any of them. |
| C8 | `cv/oldversion/cv-opencv-v1.1.0.py` is byte-identical to the previous `flame_cv.py`. Git history already keeps it. Delete it once B1 is fixed. |

## 4. §5 "Existing documents to fix"

| Item | Status |
|---|---|
| `cv/README.md` links to E3-1 … E3-9 | Partial. One link added (E3-1), and it points to a path that does not exist. The status line is unchanged. |
| Validate every `cv/contracts/*.json` example in a test | Not done |
| Regenerate `evaluation_report.json` once masks exist | Not applicable yet (no masks) |
| Explain `training_report*.json` | Not done |
| Notebook "authoritative module" headers | Not done (and a new notebook was added without one) |
| Docstrings on public functions in `cv/*.py` | Partial. The new helpers in `flame_cv.py` have one-line docstrings; CNN/PINN have no units or errors. |

## 5. §7 and §8.4 acceptance checklist (as of `06c26d5`)

- [ ] Every document in §3 exists at its path, with the header block and a changelog. *Headers and changelogs are present; E3-1 and E3-5 are at the wrong paths; the folder is `docs/CV`.*
- [ ] Every measurement in the contract has an entry in E3-2. *7 fields are missing (see E3-2).*
- [ ] Every metric links a run, commit and dataset checksum. *None do.*
- [ ] The video contract example validates in a test. *It validates manually; there is no test.*
- [ ] Ziad has approved the annotation protocol and evaluation report.
- [x] Known limitations and failure modes are stated in every document.
- [ ] E3-10 exists. *(Due Week 6.)*

## 6. Next steps (priority order)

1. **Restore `cv/flame_cv.py` (B1–B3).** Start from `cv/oldversion/cv-opencv-v1.1.0.py`, re-apply only the auto-adaptive changes, and get `python -m pytest tests/cv` back to 22 passed. Then delete `cv/oldversion/`.
2. **Re-run the evaluation for v1.2.0** and put v1.1.0 vs v1.2.0 numbers, with commit, `configDigest` and hardware, into E3-4. Remove every `[cite: …]` marker.
3. **Rename `docs/CV/` to `docs/cv/` and `pipline.md` to `pipeline.md`.** Move the model card to `cv/models/otsu-contour-baseline/MODEL_CARD.md`, fix the `cv/README.md` links, and close the code fences in E3-1 and E3-8.
4. **Rewrite E3-9 from a real benchmark**, or mark every number "not measured". Do not publish GPU numbers for a CPU pipeline.
5. **Tighten the video schema and add `tests/cv/test_video_contract.py`** that validates the example and rejects an invalid one.
6. **Add synthetic worked examples and the missing fields to E3-2.** Replace VFR interpolation in E3-6 with timestamp-preserving resampling.
7. **Move CNN/PINN to a separate PR in PyTorch**, with a group-aware split, tests and a model card each. Agree the PINN's physical scope with the Lead first.
8. **Process:** set `git config user.name`, write descriptive commit messages, open a PR for each task from a fresh branch off `main`, and start `docs/reports/WEEKLY_Princess.md`.

## Changelog
- **2026-10-13:** Initial Phase 2 review of `0a6b053` and `06c26d5`.
