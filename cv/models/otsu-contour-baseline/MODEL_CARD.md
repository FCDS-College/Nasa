| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 1.2.0 | 2026-10-13 | C1 | `cv/flame_cv.py` |

# Model Card: Auto-Adaptive Otsu Contour Segmenter (`otsu-contour-adaptive`)

## 1. Model Overview
- **Model ID:** `otsu-contour-adaptive`
- **Version:** `1.2.0`
- **Task:** Heuristic-based flame detection, binary mask segmentation, and geometric feature extraction.
- **Architecture:** OpenCV-based dimension-scaled Gaussian blurring, Otsu thresholding with configurable offset, morphological filtering, and adaptive minimum-area contour extraction (`_find_main`).

## 2. Provenance & Training Data
- **Training Data Provenance:** Rule-based/heuristic baseline model; requires no traditional machine learning training or weights. Relies on algorithmic computer vision rules.
- **Configuration:** Runtime parameters and `configDigest` are recorded in each result's provenance.

## 3. Evaluation & Performance
- **Evaluation Dataset:** 10 space experiment frames from `FF-PSI-107` (`ISS018E030336` - `ISS018E030376`)[cite: 7].
- **Metrics:** Segmentation accuracy remains `NOT_EVALUATED` pending ground-truth mask integration. See the evaluation report for baseline caveats.

## 4. Hardware Requirements
- **Hardware:** Runs efficiently on standard CPU architectures; compatible with GPU acceleration environments via OpenCV/NumPy optimizations.

## 5. Intended and Out-of-Scope Uses
- **Intended Uses:** Primary automated screening of space experiment flame imagery, geometric projection calculations, and anomaly flagging.
- **Out-of-Scope Uses:** 
  - Absolute physical temperature estimation from RGB pixel intensities.
  - Deployment in safety-critical automated control systems without human review of overlays.

## 6. Known Limitations and Failure Modes
- False positives triggered by bright hardware reflections or hot background spots due to brightness heuristic.
- Sensitivity to overexposed/clipped regions (`saturationClipping`).
- 2D projected spatial measurements without depth correction or scale calibration (`scaleAbsent`).

## Changelog
- **v1.2.0 (2026-10-13):** Updated for the restored auto-adaptive pipeline and versioned configuration provenance.