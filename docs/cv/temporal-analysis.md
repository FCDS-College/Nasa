| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 1.1.0 | 2026-10-14 | A2, E3-7 | `cv/temporal_analysis.py`, `cv/video_analysis.py` |

# Temporal Analysis Specification (A2)

Implemented in `cv/temporal_analysis.py` (`summarize`). Inputs are the per-frame records produced by `cv/video_analysis.py`. All thresholds live in `TemporalConfig` and are echoed in the result as `temporalSummary.aggregationConfig`, together with `fps` and `sampleEvery`.

## 1. Tracking Method and Identity Rules
- **Approach:** a single-flame tracker over bounding boxes (original-image pixels). A frame joins the current session when it is `PRESENT` and its box overlaps the previous `PRESENT` box with IoU >= `min_iou` (0.1).
- **Missing detections:** `ABSENT`/`UNCERTAIN` frames keep their place in the sequence with `pixelArea: null`. A new session starts after a gap longer than `max_gap_s` (0.5 s) or when the IoU test fails. `trackSessions` counts sessions. With coarse sampling (frames further apart than `max_gap_s`) every frame is its own session; tracking is only meaningful at sampling intervals below the gap threshold.
- There is no multi-object tracking; multiple flames are not separated.

## 2. Temporal Metrics
- **Area change rate:** `(A_t - A_{t-1}) / dt` in pixels^2 per second between consecutive sampled frames that both have an area; summarized as `meanAbs`, `maxAbs` and the number of pairs.
- **Persistence:** `persistenceRate` is the fraction of sampled frames that are `PRESENT`. `persistenceWindow` reports the mean and minimum of that fraction over a sliding window of `window_s` (1.0 s) worth of samples (at least 2).
- **Tracking stability:** the mean over sliding windows (`window_s`) of `var(x) + var(y)` of the flame centroid (pixels^2); `null` when no window holds two centroids. Lower is more stable.
- **Flicker frequency:** the dominant frequency of the `pixelArea` signal (FFT of the linearly detrended, Hann-windowed longest valid run).

## 3. Validity Conditions for Flicker Frequency
The value is `"not estimable"` (with `flickerStatus: "NOT_ESTIMABLE"` and the reason in `flickerNote`) unless all of the following hold:
- **Nyquist:** sampling rate `fps / sample_every` >= 2 x `max_expected_flicker_hz` (10 Hz), so at 29.97 fps only `sample_every = 1` qualifies.
- **Continuity and quality:** frames that are not `PRESENT`, lack an area, or carry the `blur` or `saturationClipping` flag break the run; the analysis uses the longest unbroken run.
- **Duration and size:** the run spans >= 2.0 s and has >= 32 samples.
- **Signal:** the area signal is not constant and the peak between 0.5 Hz and the maximum has at least 15 times the median in-band power (a guard against reporting noise as a frequency).

## 4. Lineage and Traceability
Every frame measurement carries its `frameId` and source frame index; the result carries `pipelineVersion`, `videoMetadata.fps`, the sampling policy and the aggregation configuration.

## Known limitations and failure modes
- Pixel area from an RGB Otsu mask is a proxy; flicker of the mask area is not combustion-oscillation frequency without validation against reference data. No temporal metric has been evaluated against ground truth.
- Rapid camera motion or abrupt lighting shifts break tracking and the flicker run.
- Low frame rates cap the detectable flicker frequency.

## Changelog
- **v1.1.0 (2026-10-14):** Implemented; documented the actual algorithms, defaults and validity rules.
- **v1.0.0 (2026-10-12):** Initial specification draft.