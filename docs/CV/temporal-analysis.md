| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 1.0.0 | 2026-10-12 | A2 | `cv/temporal_analysis.py` (planned) |

# Temporal Analysis Specification (A2)

## 1. Tracking Method and Identity Rules
- **Tracking Approach:** Bounding-box and centroid tracking across sequential frames using IoU overlap matching and motion heuristics.
- **Missing Detections:** Frames where detection status is `ABSENT` or `UNCERTAIN` are marked with null measurements while maintaining temporal sequence continuity. Gaps exceeding a defined threshold trigger a new tracking session ID.

## 2. Temporal Metrics & Formulas
- **Area Change Rate ($\Delta A$):** Rate of change of pixel area between consecutive frames: $\frac{A_t - A_{t-1}}{\Delta t}$.
- **Persistence:** Percentage of frames within a sliding temporal window where a valid flame region is continuously detected (`PRESENT`).
- **Tracking Stability:** Variance of centroid coordinates $(C_x, C_y)$ over a rolling aggregation window.
- **Flicker Frequency ($f_{\text{flicker}}$):** Frequency analysis (via Fast Fourier Transform - FFT) of the temporal intensity or area variation signal.

## 3. Validity Conditions for Flicker Frequency
To prevent erroneous scientific conclusions, **Flicker Frequency** calculation is strictly governed by the following validity criteria:
- **Nyquist Rate:** The video sampling rate (fps) must be at least twice the maximum expected flicker frequency.
- **Minimum Duration:** The observation window must encompass a minimum continuous duration (e.g., $\ge 2.0$ seconds).
- **Signal Quality:** Frames heavily impacted by `blur` or `saturationClipping` beyond tolerance limits are excluded from the temporal window.
- **Fallback Rule:** If validity conditions are not met, the metric must return **"not estimable"** rather than a fabricated numeric value.

## 4. Lineage and Traceability
Every temporal result links directly back to source frame IDs, video `fps`, `pipelineVersion`, and the aggregation window configuration.

## Known limitations and failure modes
- Rapid camera motion or abrupt lighting shifts can disrupt multi-frame tracking continuity.
- Low frame-rate videos limit the upper bound of detectable flicker frequencies.

## Changelog
- **v1.0.0 (2026-10-12):** Initial temporal analysis specification draft for Phase 2 Workstream A.