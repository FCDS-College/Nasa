| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 1.2.0 | 2026-10-12 | §10, A2 | `cv/flame_cv.py` |

# Measurement Definitions Dictionary (v1.2.0)

This document provides the definitive mathematical definitions, units, valid ranges, calibration requirements, and failure flags for every measurement produced by the CV pipeline.

---

## 1. Geometry Measurements (`Geometry`)
All spatial measurements are reported in **original-image pixels** (adjusted via letterbox scale) unless explicitly calibrated.

### 1.1 Pixel Area (`pixelArea`)
- **JSON Field:** `measurements.geometry.pixelArea`
- **Formula / Algorithm:** $\frac{\text{cv2.countNonZero(main)}}{\text{scale}^2}$ (count of non-zero mask pixels divided by the squared scaling factor).
- **Unit:** $\text{pixels}^2$ (original image coordinate space).
- **Valid Range:** $[0, \infty)$
- **Label Class:** `MEASURED`
- **Calibration Requirement:** None for pixel units; requires `mmPerPixel` for physical conversion.
- **Unreliable Quality Flags:** `blur`, `occlusion`.

### 1.2 Centroid (`centroid`)
- **JSON Field:** `measurements.geometry.centroid`
- **Formula / Algorithm:** Center of mass calculated via image moments: $C_x = \frac{M_{10}}{M_{00}}, C_y = \frac{M_{01}}{M_{00}}$, mapped back to original coordinates by subtracting padding and dividing by scale.
- **Unit:** Pixels $(x, y)$ relative to top-left of the original image.
- **Valid Range:** $[0, \text{width}] \times [0, \text{height}]$
- **Label Class:** `MEASURED`
- **Calibration Requirement:** None.
- **Unreliable Quality Flags:** `occlusion`.

### 1.3 Perimeter (`perimeter`)
- **JSON Field:** `measurements.geometry.perimeter`
- **Formula / Algorithm:** Contour arc length calculated using `cv2.arcLength(cnt, True)` divided by scale `s`.
- **Unit:** Pixels.
- **Valid Range:** $[0, \infty)$
- **Label Class:** `MEASURED`
- **Calibration Requirement:** None.
- **Unreliable Quality Flags:** `blur`, `occlusion`.

### 1.4 Aspect Ratio (`aspectRatio`)
- **JSON Field:** `measurements.geometry.aspectRatio`
- **Formula / Algorithm:** $\frac{w}{h}$ where $w$ and $h$ are the width and height of the bounding rectangle (`cv2.boundingRect`).
- **Unit:** Unitless ratio.
- **Valid Range:** $(0, \infty)$
- **Label Class:** `MEASURED`
- **Calibration Requirement:** None.
- **Unreliable Quality Flags:** `occlusion`.

### 1.5 Elongation (`elongation`)
- **JSON Field:** `measurements.geometry.elongation`
- **Formula / Algorithm:** Ratio of the major to minor side lengths of the minimum area bounding box (`cv2.minAreaRect`).
- **Unit:** Unitless ratio.
- **Valid Range:** $[1.0, \infty)$
- **Label Class:** `MEASURED`
- **Calibration Requirement:** None.
- **Unreliable Quality Flags:** `blur`.

### 1.6 Circularity (`circularity`)
- **JSON Field:** `measurements.geometry.circularity`
- **Formula / Algorithm:** $\frac{4 \pi \cdot \text{Area}}{\text{Perimeter}^2}$ clipped to $[0, 1]$.
- **Unit:** Unitless ratio.
- **Valid Range:** $[0.0, 1.0]$
- **Label Class:** `MEASURED`
- **Calibration Requirement:** None.
- **Unreliable Quality Flags:** `blur`.

### 1.7 Symmetry (LR & UD) (`symmetryLR`, `symmetryUD`)
- **JSON Field:** `measurements.geometry.symmetryLR`, `measurements.geometry.symmetryUD`
- **Formula / Algorithm:** Intersection over Union (IoU) between the cropped binary mask and its horizontally/vertically flipped counterpart.
- **Unit:** Unitless ratio.
- **Valid Range:** $[0.0, 1.0]$
- **Label Class:** `MEASURED`
- **Calibration Requirement:** None.
- **Unreliable Quality Flags:** `blur`, `occlusion`.

---

## 2. Appearance Statistics (`Appearance`)
*Note: Image-derived statistics inside the flame mask; not physical state variables or temperature.*

### 2.1 Color Statistics (`colorSpaceStatistics`)
- **JSON Field:** `measurements.appearance.colorSpaceStatistics` (`meanR`, `meanG`, `meanB`)
- **Formula / Algorithm:** Arithmetic mean of RGB pixel values inside the binary mask region.
- **Unit:** Intensity scale $[0, 255]$.
- **Valid Range:** $[0.0, 255.0]$
- **Label Class:** `MEASURED`
- **Calibration Requirement:** Requires camera response and exposure calibration to represent physical radiance.
- **Unreliable Quality Flags:** `saturationClipping`, `lowLight`.

### 2.2 Saturation & Value (`meanSaturationInMask`, `meanValueInMask`)
- **JSON Field:** `measurements.appearance.meanSaturationInMask`, `measurements.appearance.meanValueInMask`
- **Formula / Algorithm:** Mean values of the S and V channels (normalized to $[0, 1]$) converted from RGB to HSV space within the mask.
- **Unit:** Normalized ratio $[0, 1]$.
- **Valid Range:** $[0.0, 1.0]$
- **Label Class:** `MEASURED`
- **Calibration Requirement:** None.
- **Unreliable Quality Flags:** `saturationClipping`, `lowLight`.

---

## 3. Physical Estimates (`PhysicalEstimates`)
*Computed only when `mmPerPixel` calibration metadata is provided.*

### 3.1 Physical Area & Perimeter (`areaMm2`, `perimeterMm`)
- **JSON Field:** `measurements.physicalEstimates.areaMm2`, `measurements.physicalEstimates.perimeterMm`
- **Formula / Algorithm:** $\text{Area}_{\text{pixels}} \times (\text{mmPerPixel})^2$ and $\text{Perimeter}_{\text{pixels}} \times \text{mmPerPixel}$.
- **Unit:** $\text{mm}^2$ and $\text{mm}$.
- **Valid Range:** $[0, \infty)$
- **Label Class:** `ESTIMATED`
- **Calibration Requirement:** Requires valid positive `mmPerPixel`.
- **Unreliable Quality Flags:** `scaleAbsent` (must be False).

---

## Known limitations and failure modes
- Spatial metrics assume a 2D projection plane; perspective distortion is not corrected without depth data.
- RGB intensity and appearance metrics are strictly image-dependent and **cannot** be translated to temperature without full radiometric calibration.

## Changelog
- **v1.2.0 (2026-10-12):** Initial creation of measurement dictionary aligned with auto-adaptive pipeline v1.2.0.