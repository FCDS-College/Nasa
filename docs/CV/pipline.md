| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 1.2.0 | 2026-10-12 | MVP §10, M4 | `cv/flame_cv.py` |

# CV Pipeline Specification (v1.2.0 - Auto-Adaptive)

## 1. Stage Diagram
```text
Image -> Validation (validate_image)
      -> Auto-Letterbox Preprocessing (preprocess_image & compute_auto_target_size)
      -> Auto-Adaptive Segmentation & Contour Detection (_find_main with dynamic Otsu offset)
      -> Geometry & Appearance Features (_geometry, _appearance)
      -> Confidence & Quality Flags (ConfidenceAndQualityFlags)
      -> AnalysisResult (+ _write_artifacts)
2. Validation Limits
Max file size: 10 MB (max_file_bytes)

Max pixels: 100,000,000 pixels (max_pixels)

Minimum dimensions: 64x64 pixels (min_dim)

Allowed formats: JPEG, PNG (allowed_formats)

Rejection behavior: Triggers specific RFC 7807-style CVError envelopes (e.g., UnsupportedMediaError, ImageTooSmallError).

3. Auto-Adaptive Parameters & Configuration (CVConfig)
Target Size: Computed automatically via compute_auto_target_size() if not provided.

Blur Kernel: Auto-computed proportionally based on image dimensions via compute_auto_blur_kernel().

Thresholds & Contrast: Dynamic offset on top of Otsu and adaptive minimum contrast based on background standard deviation.

Config Digest: Every hyperparameter contributes to configDigest ensuring traceability.

4. Cache Reuse (M4)
Cache Key Composition: Formulated using input checksum + PIPELINE_VERSION + PREPROCESS_VERSION + SEGMENTER_VERSION + configDigest + options + mmPerPixel.

Invalidation: Stale results are automatically invalidated if any version or configuration changes.

5. Artifacts
Masks & Overlays: Stored in designated artifact directories with computed SHA-256 checksums (maskUri, overlayArtifactUri).

Known limitations and failure modes
Heuristic-based detection; bright artifacts or reflections can occasionally trigger false positives.

Spatial measurements rely on 2D projections unless calibrated with mmPerPixel.

Changelog
v1.2.0 (2026-10-12): Upgraded to auto-adaptive target sizes, dynamic blur kernels, and statistical contrast thresholds.

v1.1.0: Initial Otsu/contour baseline implementation.