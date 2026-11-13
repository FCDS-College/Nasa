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
- **Evaluation Dataset:** 10 space experiment frames from `FF-PSI-107` (`ISS018E030336` - `ISS018E030376`), run with v1.1.0. All 10 contain a flame, so false positives were not measured (CV audit, CV-3).
- **Metrics:** Segmentation accuracy remains `NOT_EVALUATED` pending ground-truth mask integration. See the evaluation report for baseline caveats.

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
- **v1.3.0 (2026-11-13):** 16-bit input scaled instead of clipped (45 FLEX dark frames were reported as flames); no PRESENT without background or with unstable segmentation; 0.05% minimum region; computed ABSENT confidence. Removed the `[cite: 7]` debris.
- **v1.2.0 (2026-10-13):** Updated for the restored auto-adaptive pipeline and versioned configuration provenance.