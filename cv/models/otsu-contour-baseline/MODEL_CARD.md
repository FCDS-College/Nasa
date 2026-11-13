| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 1.3.0 | 2026-11-13 | C1, CV audit CV-2 | `cv/flame_cv.py` |

# Model Card: Auto-Adaptive Otsu Contour Segmenter (`otsu-contour-adaptive`)

## 1. Model Overview
- **Model ID:** `otsu-contour-adaptive`
- **Version:** `1.3.0`
- **Task:** Heuristic-based flame detection, binary mask segmentation, and geometric feature extraction.
- **Architecture:** OpenCV-based dimension-scaled Gaussian blurring, Otsu thresholding with configurable offset, morphological filtering, and adaptive minimum-area contour extraction (`_find_main`). The PRESENT / UNCERTAIN / ABSENT rules are in [docs/cv/pipeline.md §4](../../../docs/cv/pipeline.md#4-detection-decision-v130).

## 2. Provenance & Training Data
- **Training Data Provenance:** Rule-based/heuristic baseline model; requires no traditional machine learning training or weights. Relies on algorithmic computer vision rules.
- **Configuration:** Runtime parameters and `configDigest` are recorded in each result's provenance.

## 3. Evaluation & Performance
- **Evaluation set:** `cv_gold_v1`: 150 frames, 56 masks, with a held-out split of 8 unseen BASS-II tests ([docs/cv/evaluation-report.md](../../../docs/cv/evaluation-report.md)). Labels are Claude-drafted and not yet verified by a person.
- **Held-out results (v1.3.0, 95% intervals over tests):**
  - false-positive rate 0.30 [0.00, 0.65];
  - precision 0.68 [0.29, 1.00];
  - localized recall 0.56 [0.22, 0.91];
  - mean mask IoU 0.30 [0.10, 0.55].
- **Before fixes 1–2:** false-positive rate 0.97 and localized recall 0.37.
- **Main failures:** static bright scenery (cabin views, lit chamber) is called a flame; dim blue flames are missed; small flames below 0.05% of the frame are missed (a v1.3.0 regression, see the report).

## 4. Hardware Requirements
- **Hardware:** Runs efficiently on standard CPU architectures; compatible with GPU acceleration environments via OpenCV/NumPy optimizations.

## 5. Intended and Out-of-Scope Uses
- **Intended Uses:** Primary automated screening of space experiment flame imagery, geometric projection calculations, and anomaly flagging.
- **Out-of-Scope Uses:** 
  - Absolute physical temperature estimation from RGB pixel intensities.
  - Deployment in safety-critical automated control systems without human review of overlays.

## 6. Known Limitations and Failure Modes
- False positives on static bright hardware (FLEX deployment needle, glovebox floor): stable, contrasting regions that the brightness rules cannot tell from a flame.
- Sensitivity to overexposed/clipped regions (`saturationClipping`).
- 2D projected spatial measurements without depth correction or scale calibration (`scaleAbsent`).

## Changelog
- **v1.3.0 evaluation (2026-11-13):** First evaluation with negatives and a held-out split (`cv_gold_v1`).
- **v1.3.0 (2026-11-13):** 16-bit input scaled instead of clipped (45 FLEX dark frames were reported as flames); no PRESENT without background or with unstable segmentation; 0.05% minimum region; computed ABSENT confidence. Removed the `[cite: 7]` debris.
- **v1.2.0 (2026-10-13):** Updated for the restored auto-adaptive pipeline and versioned configuration provenance.