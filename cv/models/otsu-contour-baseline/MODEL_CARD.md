| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 1.8.0 | 2026-11-14 | C1, CV audit CV-2 | `cv/flame_cv.py` |

# Model Card: Auto-Adaptive Otsu Contour Segmenter (`otsu-contour-adaptive`)

## 1. Model Overview
- **Model ID:** `otsu-contour-adaptive`
- **Version:** `1.8.0`
- **Task:** Heuristic-based flame detection, binary mask segmentation, and geometric feature extraction.
- **Architecture:** OpenCV-based dimension-scaled Gaussian blurring, Otsu thresholding with configurable offset, morphological filtering, and adaptive minimum-area contour extraction (`_find_main`). The PRESENT / UNCERTAIN / ABSENT rules are in [docs/cv/pipeline.md §4](../../../docs/cv/pipeline.md#4-detection-decision).

## 2. Provenance & Training Data
- **Training Data Provenance:** Rule-based/heuristic baseline model; requires no traditional machine learning training or weights. Relies on algorithmic computer vision rules.
- **Configuration:** Runtime parameters and `configDigest` are recorded in each result's provenance.

## 3. Evaluation & Performance
- **Evaluation set:** `cv_gold_v1`: 150 frames, 56 masks, with a held-out split of 8 unseen BASS-II tests ([docs/cv/evaluation-report.md](../../../docs/cv/evaluation-report.md)). Labels are Claude-drafted and not yet verified by a person.
- **Held-out results (v1.8.0, unchanged from v1.5.0; 95% intervals over tests):**
  - false-positive rate 0.00 (0 of 37 absent frames; 8 tests cannot rule out a few per cent);
  - precision 1.00;
  - localized recall 0.68 [0.28, 1.00];
  - mean mask IoU 0.32 [0.13, 0.55].
- **Before fixes 1–2:** false-positive rate 0.97 and localized recall 0.37.
- **Main failures:** dim blue flames are missed; bright hardware in a dark scene is still called a flame without a camera profile (dev false-positive rate 0.16). With the `flex-colour` profile it is 0.00 (in-sample): the profile removes the FLEX arc, its size floor reports droplet glints UNCERTAIN, and (v1.8.0) straight-edged regions such as the DSI backlit cell are UNCERTAIN. Lit scenery (cabin views, a lit chamber) is UNCERTAIN since v1.5.0.

## 4. Hardware Requirements
- **Hardware:** CPU only (OpenCV and NumPy); there is no GPU path. Measured on a 4-core Xeon @ 2.10 GHz: 63–170 ms per image (512² to 3008 × 2000) and 33.6 video frames per second at 720 × 480 ([docs/cv/performance.md](../../../docs/cv/performance.md)).

## 5. Intended and Out-of-Scope Uses
- **Intended Uses:** Primary automated screening of space experiment flame imagery, geometric projection calculations, and anomaly flagging.
- **Out-of-Scope Uses:** 
  - Absolute physical temperature estimation from RGB pixel intensities.
  - Deployment in safety-critical automated control systems without human review of overlays.

## 6. Known Limitations and Failure Modes
- False positives on static bright hardware (FLEX deployment needle, glovebox floor): stable, contrasting regions that the brightness rules cannot tell from a flame. A camera profile (v1.6.0) can exclude a known camera's hardware zone, and (v1.7.0) report regions smaller than a droplet UNCERTAIN, but only when the client names the profile. A flame inside the zone is not seen, and a FLEX flame near burnout smaller than the floor is UNCERTAIN.
- Sensitivity to overexposed/clipped regions (`saturationClipping`).
- 2D projected spatial measurements without depth correction or scale calibration (`scaleAbsent`).

## Changelog
- **v1.8.0 (2026-11-14):** A straight-edged region (rectangularity > 0.875, at least 20 px across) is UNCERTAIN. Dev false positives 2 → 0; holdout unchanged.
- **v1.7.0 (2026-11-14):** Camera profiles may set a size floor; `flex-colour` sets 0.1% of the frame (droplet physics, measured scale). Dev false positives 5 → 2; holdout unchanged. Results now report segmenter version 1.7.0 (v1.6.0 had left it at 1.5.0).
- **v1.6.0 (2026-11-14):** Per-camera exclusion zones (`cv/configs/camera_profiles.json`, request `cameraProfile` / API `camera_profile`); first profile `flex-colour`. Dev false positives 7 → 5; holdout unchanged (no FLEX frames there).
- **v1.5.0 (2026-11-14):** A detection in a lit scene is UNCERTAIN, never PRESENT (tuned on dev only); held-out false-positive rate 0.30 → 0.00.
- **Docs (2026-11-14):** Hardware line replaced with measured CPU figures; the GPU-acceleration claim is removed.
- **v1.4.0 (2026-11-13):** Small regions are specks unless high-contrast, replacing the 0.05% minimum region that missed small flames (tuned on dev only).
- **v1.3.0 evaluation (2026-11-13):** First evaluation with negatives and a held-out split (`cv_gold_v1`).
- **v1.3.0 (2026-11-13):** 16-bit input scaled instead of clipped (45 FLEX dark frames were reported as flames); no PRESENT without background or with unstable segmentation; 0.05% minimum region; computed ABSENT confidence. Removed the `[cite: 7]` debris.
- **v1.2.0 (2026-10-13):** Updated for the restored auto-adaptive pipeline and versioned configuration provenance.