| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 1.3.0 | 2026-11-13 | MVP §10, M4, CV audit CV-2 | `cv/flame_cv.py` |

# CV Pipeline Specification (v1.3.0, auto-adaptive)

## 1. Stage diagram

```text
Image -> Validation (validate_image)
      -> Bit-depth conversion + auto-letterbox preprocessing (_to_rgb8, preprocess_image, compute_auto_target_size)
      -> Auto-adaptive segmentation and contour detection (_find_main, Otsu with an optional offset)
      -> Detection decision (PRESENT / UNCERTAIN / ABSENT, section 4)
      -> Geometry and appearance features (_geometry, _appearance)
      -> Confidence and quality flags (ConfidenceAndQualityFlags)
      -> AnalysisResult (+ _write_artifacts)
```

## 2. Validation limits

- Max file size: 10 MB (`max_file_bytes`).
- Max pixels: 100,000,000 (`max_pixels`).
- Minimum dimensions: 64 × 64 pixels (`min_dim`).
- Allowed formats: JPEG, PNG (`allowed_formats`).
- Rejections raise RFC 7807-style `CVError` envelopes (for example `UnsupportedMediaError`, `ImageTooSmallError`).

## 3. Preprocessing and auto-adaptive parameters (`CVConfig`)

- **Bit depth (v1.3.0).** 16-bit greyscale input (Pillow modes `I;16*` and `I`) is scaled linearly to 8 bits over `0 … 2**input_bit_depth − 1`, by default the full 16-bit range. Before v1.3.0, `convert("RGB")` clipped every value above 255 to 255, so a 16-bit frame became a white rectangle: all 45 16-bit FLEX sample frames (`C021H03C`, `C024M06C`, `H14H101C`) were reported as flames at confidence 0.80, although they are sensor dark frames. Set `input_bit_depth` when a sensor's real depth is known (for example 12). Frames are never stretched to their own maximum, because that would turn a dark frame's readout noise into contrast. The result records `preprocessing.sourceBitDepth`.
- **Target size:** computed by `compute_auto_target_size()` unless given.
- **Blur kernel:** proportional to the image size (`compute_auto_blur_kernel()`).
- **Thresholds and contrast:** Otsu with an optional offset; minimum contrast adapts to the background's standard deviation.
- **Config digest:** every parameter contributes to `configDigest`.

## 4. Detection decision (v1.3.0)

The largest bright component (at least `min_area_ratio` = 0.05% of the image) is the candidate. The following terms are used:

- **Contrast:** the mean of the region minus the mean of the background (content outside a dilated ring around the region).
- **Stability:** the IoU of the full binary masks at the threshold ± 10%, compared inside the region's padded bounding box.
- **Score:** 0.5 × contrast/120 + 0.3 × area/0.2% + 0.2 × stability, each term clipped to [0, 1].

| Condition | Status |
|---|---|
| No candidate (nothing above the threshold, or every component is smaller than 0.05% of the image) | `ABSENT` |
| Less than 5% of the image is left as background (`min_background_fraction`) and the image is nearly uniform (under 15 gray levels between the 0.5th and 99.5th percentiles) | `ABSENT` |
| Less than 5% left as background, otherwise | `UNCERTAIN`: contrast is not estimable (`flameContrast: null`) |
| Score ≥ 0.60, contrast ≥ the minimum, stability ≥ 0.5 (`min_present_stability`) | `PRESENT` |
| Score ≥ 0.60 and contrast ≥ the minimum, but stability < 0.5 | `UNCERTAIN` (warning names the IoU) |
| Contrast ≥ half the minimum | `UNCERTAIN` |
| Otherwise | `ABSENT` |

**Confidence** is the score for `PRESENT` and `UNCERTAIN`. For `ABSENT` it is `1 − score`, capped at `absent_confidence_cap` (0.9). With no candidate, the score is the contrast term of the brightest content left in the image (99.5th percentile minus median), so a black frame gives 0.9 and a cluttered one less. No confidence is a fixed constant. None of these values is a calibrated probability (`confidenceBasis: heuristic_uncalibrated`).

**Classification:** `MEASURED` when geometry was measured, otherwise `INFERRED`.

Why these values (measured on every committed sample image and the three BASS-II videos; see `.internal/research/2026-11-13-cv-audit.md`, finding CV-2):

- **0.05% minimum area:** edge specks in empty BASS-II frames are at most 0.031% of the frame; the smallest real flame in the samples (the `TEST_B1` ignition kernel) is 0.094%.
- **0.5 minimum stability:** the lowest real SPICE flame scores 0.86.
- **Stability measured locally:** comparing only the largest component scored a real two-lobed BASS-II flame (`TEST_B1` frame 630) at 0, because the lobes swapped places as the largest.
- **Quality flags do not demote a detection:** `saturationClipping` is set on 100% of the real SPICE flames.

## 5. Cache reuse (M4)

- Cache key: input checksum + `PIPELINE_VERSION` + `PREPROCESS_VERSION` + `SEGMENTER_VERSION` + `configDigest` + options + `mmPerPixel`.
- Results are invalidated automatically when any version or configuration value changes.

## 6. Artifacts

Masks and overlays are written to the artifact directories with SHA-256 checksums (`maskUri`, `overlayArtifactUri`).

## Command-line entry point

`python -m cv.flame_cv [image] [--out-dir cv/output]` runs `analyze_image_safe` on an image (or a generated synthetic flame when omitted), writes `analysis_result.json` and `masks/` under the output directory, prints the result JSON, and exits 1 when the result is an error response. See [offline-operation.md](offline-operation.md) for offline use.

## Known limitations and failure modes

- Detection is brightness-based. **Static bright hardware is still reported as a flame**: the FLEX deployment needle and wall (`176F001D`, `195F002D` pre-ignition frames) and the glovebox floor in BASS-II `TEST_T25_2ND_VIEW` are bright, contrasting and stable, so no rule above separates them from a flame. Separating them needs colour or motion cues.
- The thresholds were chosen on the committed samples, with no labelled evaluation set (audit CV-3). They are documented choices, not validated operating points.
- 16-bit input from a sensor with fewer real bits appears dark unless `input_bit_depth` is set; dim flames in such data can be missed.
- Spatial measurements are 2D projections unless calibrated with `mmPerPixel`.

## Changelog

- **v1.3.0 (2026-11-13):** 16-bit input is scaled instead of clipped; a region with no background is never `PRESENT`; `PRESENT` requires region-local stability ≥ 0.5; minimum region 0.05% of the image; `ABSENT` confidence is computed; classification follows what was measured (section 4). Fixed this page's unclosed code block.
- **Unreleased (2026-10-14):** Documented the CLI entry point.
- **v1.2.0 (2026-10-12):** Upgraded to auto-adaptive target sizes, dynamic blur kernels and statistical contrast thresholds.
- **v1.1.0:** Initial Otsu/contour baseline.
