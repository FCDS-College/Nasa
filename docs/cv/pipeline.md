| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 1.5.0 | 2026-11-14 | MVP §10, M4, CV audit CV-2, CV-3 | `cv/flame_cv.py` |

# CV Pipeline Specification (v1.5.0, auto-adaptive)

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

## 4. Detection decision

The largest bright component (at least `min_area_ratio` = 0.01% of the image) is the candidate. The following terms are used:

- **Contrast:** the mean of the region minus the mean of the background (content outside a dilated ring around the region).
- **Stability:** the IoU of the full binary masks at the threshold ± 10%, compared inside the region's padded bounding box.
- **Score:** 0.5 × contrast/120 + 0.3 × area/0.2% + 0.2 × stability, each term clipped to [0, 1].

| Condition | Status |
|---|---|
| No candidate (nothing above the threshold, or every component is smaller than 0.01% of the image) | `ABSENT` |
| The region is smaller than 0.05% of the image (`small_region_ratio`) and its contrast is below 83 (`small_region_min_contrast`) | `ABSENT`: a speck, not a flame |
| Less than 5% of the image is left as background (`min_background_fraction`) and the image is nearly uniform (under 15 gray levels between the 0.5th and 99.5th percentiles) | `ABSENT` |
| Less than 5% left as background, otherwise | `UNCERTAIN`: contrast is not estimable (`flameContrast: null`) |
| Score ≥ 0.60, contrast ≥ the minimum, stability ≥ 0.5 (`min_present_stability`) | `PRESENT`, unless the scene is lit (next row) |
| Would be `PRESENT`, but the scene is lit: median gray minus 1st-percentile gray > 11 (`lit_scene_level`) | `UNCERTAIN`: in a lit scene a bright region may be scenery or hardware |
| Score ≥ 0.60 and contrast ≥ the minimum, but stability < 0.5 | `UNCERTAIN` (warning names the IoU) |
| Contrast ≥ half the minimum | `UNCERTAIN` |
| Otherwise | `ABSENT` |

**Confidence** is the score for `PRESENT` and `UNCERTAIN`. For `ABSENT` it is `1 − score`, capped at `absent_confidence_cap` (0.9). With no candidate, the score is the contrast term of the brightest content left in the image (99.5th percentile minus median), so a black frame gives 0.9 and a cluttered one less. No confidence is a fixed constant. None of these values is a calibrated probability (`confidenceBasis: heuristic_uncalibrated`).

**Classification:** `MEASURED` when geometry was measured, otherwise `INFERRED`.

Why these values (measured on every committed sample image and the three BASS-II videos; see `.internal/research/2026-11-13-cv-audit.md`, finding CV-2):

- **Small regions need contrast ≥ 83:** chosen on the dev split of `cv_gold_v1` only. Specks under 0.05% of the frame in dev frames reach contrast 61.6 at most; real dev flames start at 104.9; 83 is the midpoint. v1.3.0 used a 0.05% minimum region instead, which kept the specks out but also missed real small flames: 5 of 9 flame frames of the held-out test T23 (0.019–0.049% of the frame, contrast 100–128). See [evaluation-report.md](evaluation-report.md).
- **0.5 minimum stability:** the lowest real SPICE flame scores 0.86.
- **Stability measured locally:** comparing only the largest component scored a real two-lobed BASS-II flame (`TEST_B1` frame 630) at 0, because the lobes swapped places as the largest.
- **Quality flags do not demote a detection:** `saturationClipping` is set on 100% of the real SPICE flames.
- **Lit scenes are never PRESENT (v1.5.0):** the detector assumes a dark background, because luminous flames are filmed in dark chambers. Lighting is measured as the median gray minus the 1st-percentile gray, so a sensor's constant black level does not count as light (a first version used the median alone, which would have called a 12-bit sensor's pedestal "lit"). Chosen on the dev split of `cv_gold_v1` only: dev flame frames reach 4 at most; lit scenery false positives (the `TEST_T25` cabin view, lit FLEX hardware) start at 19; 11 is the midpoint.

## 5. Cache reuse (M4)

- Cache key: input checksum + `PIPELINE_VERSION` + `PREPROCESS_VERSION` + `SEGMENTER_VERSION` + `configDigest` + options + `mmPerPixel`.
- Results are invalidated automatically when any version or configuration value changes.

## 6. Artifacts

Masks and overlays are written to the artifact directories with SHA-256 checksums (`maskUri`, `overlayArtifactUri`).

## Command-line entry point

`python -m cv.flame_cv [image] [--out-dir cv/output]` runs `analyze_image_safe` on an image (or a generated synthetic flame when omitted), writes `analysis_result.json` and `masks/` under the output directory, prints the result JSON, and exits 1 when the result is an error response. See [offline-operation.md](offline-operation.md) for offline use.

## Known limitations and failure modes

- Detection is brightness-based. **Lit scenery** (cabin views, a lit chamber) is UNCERTAIN since v1.5.0, but **bright hardware in a dark scene is still reported as a flame**: the glowing FLEX igniter arc and point lights (`176F001D`, `195F002D`, `H08M101D` frames) are bright, contrasting and stable on a dark background, like a flame. Separating them needs colour or motion cues.
- A real flame filmed in a lit scene is reported UNCERTAIN, not PRESENT. No such frame is in `cv_gold_v1`, so this recall cost is not measured.
- The thresholds were chosen on the committed samples and the dev split of `cv_gold_v1`. Their held-out performance is in [evaluation-report.md](evaluation-report.md), measured against labels that are not yet verified by a person.
- A small flame with contrast below 83 is treated as a speck. Dev data has no small flames, so the 83 cut-off is set from the specks and from larger flames only.
- 16-bit input from a sensor with fewer real bits appears dark unless `input_bit_depth` is set; dim flames in such data can be missed.
- Spatial measurements are 2D projections unless calibrated with `mmPerPixel`.

## Changelog
- **v1.5.0 (2026-11-14):** In a lit scene a detection is UNCERTAIN, never PRESENT (cut-off tuned on dev only). Held-out false-positive rate 0.30 → 0.00, with no held-out flame lost.
- **v1.4.0 (2026-11-13):** Minimum region back to 0.01%; regions under 0.05% are specks unless their contrast is ≥ 83 (tuned on dev only). Fixes the v1.3.0 regression on small flames. No status changed on any committed sample.

- **v1.3.0 (2026-11-13):** 16-bit input is scaled instead of clipped; a region with no background is never `PRESENT`; `PRESENT` requires region-local stability ≥ 0.5; minimum region 0.05% of the image; `ABSENT` confidence is computed; classification follows what was measured (section 4). Fixed this page's unclosed code block.
- **Unreleased (2026-10-14):** Documented the CLI entry point.
- **v1.2.0 (2026-10-12):** Upgraded to auto-adaptive target sizes, dynamic blur kernels and statistical contrast thresholds.
- **v1.1.0:** Initial Otsu/contour baseline.
