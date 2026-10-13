| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess & Ziad | Draft | 1.2.0 | 2026-10-12 | M10, A3, C1 | `cv/flame_cv.py` |

# CV Evaluation Report (v1.2.0)

## 1. Dataset & Execution Overview
- **Dataset Source:** Sample images from `FF-PSI-107` (Space Experiment frames)[cite: 4, 7].
- **Total Images Found & Analyzed:** 10 images (`ISS018E030336` through `ISS018E030376`)[cite: 7].
- **Pipeline Version:** `cv-opencv-v1.1.0` (with auto-adaptive updates moving to v1.2.0)[cite: 7].
- **Config Digest:** `5140c618f88cd05b`[cite: 7].

## 2. Detection Performance Metrics
- **Detection Status Counts:** 
  - `PRESENT`: 10 (100%)[cite: 7]
  - `ABSENT`: 0 (0%)[cite: 7]
  - `UNCERTAIN`: 0 (0%)[cite: 7]
- **Note:** The current detector relies on brightness-based heuristics; counts represent successful detection triggers rather than absolute accuracy[cite: 7].

## 3. Quality Flag Rates
- **Saturation Clipping (`saturationClipping`):** 1.0 (100% of analyzed images exhibited overexposed or clipped pixel regions within the flame mask)[cite: 7].
- **Low Light (`lowLight`):** 0.1 (10% of images triggered low overall background brightness flags, e.g., `ISS018E030340`)[cite: 7].
- **Blur (`blur`), Multiple Flames (`multipleFlames`), Occlusion (`occlusion`):** 0.0 (0%)[cite: 7].

## 4. Segmentation & Ground-Truth Evaluation
- **Status:** `NOT_EVALUATED` (Reason: Ground-truth segmentation masks are pending integration with the annotation protocol E3-3)[cite: 7].
- **Acceptance Verdict:** `NOT_EVALUATED` until IoU metrics can be computed against validated masks[cite: 7].

## 5. Failure Gallery & Limitations
- **Known Limitations:**
  - No measurement-error evaluation is available due to the absence of calibrated physical reference values[cite: 7].
  - Frames originating from the same experiment run are highly correlated; data must be split by `groupId` rather than individual frames[cite: 7].
  - Detector confidence scores represent heuristic confidence metrics rather than statistically calibrated probabilities[cite: 7].

## Changelog
- **v1.2.0 (2026-10-12):** Initial formal evaluation report based on sample batch analysis.