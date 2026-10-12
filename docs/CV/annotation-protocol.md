| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess & Ziad | Draft | 1.2.0 | 2026-10-12 | M10, A3 | `cv/flame_cv.py` |

# Annotation Protocol and Ground-Truth Dataset Specification (v1.2.0)

## 1. Mask Annotation Rules
- **Flame Core Definition:** Pixels corresponding to the primary luminous flame region are labeled as positive (foreground).
- **Glow & Soot Policy:** Secondary thermal glow and dispersed soot particles outside the defined luminous core boundary are excluded from the binary mask unless physically continuous and connected to the high-intensity emission.
- **Reflections and Hardware:** Hardware surfaces, internal reflections, or hot background spots are strictly excluded, even if bright.
- **Edge Policy:** Smooth contour interpolation is applied at boundary fringes where intensity fades into background noise.

## 2. Tooling, Formats, and Workflow
- **Annotation Tool:** Standardized polygon/brush labeling tool exporting lossless binary PNG masks.
- **File Naming & Storage:** Masks must share the identical stem of the source image with a `_mask` suffix (e.g., `ISS018E030336_mask.png`) and be stored in designated artifact directories.
- **Review Workflow:** Annotations performed by designated team members and cross-reviewed by Ziad (E5) for quality assurance. Inter-annotator agreement is evaluated using Intersection over Union (IoU) thresholds.

## 3. Dataset Manifest & Leakage Control
- **Manifest Format:** JSONL structured lines adhering to `ImageIntakeRecord` schema.
- **Splitting Strategy:** Split strictly by group / experiment ID (`groupId`) rather than individual frames to prevent data leakage across `dev`, `validation`, and `holdout` splits.
- **Integrity:** Every image and mask is tracked via SHA-256 checksums.

## 4. Provenance and Licensing
- All dataset sources and space experiment frames (such as FF-PSI-107 samples) maintain documented provenance, URLs, and access dates.

## Known limitations and failure modes
- Manual annotation subjectivity on faint outer flame boundaries and low-contrast edges.
- Potential motion blur in video frames complicating precise pixel-level mask delineation.

## Changelog
- **v1.2.0 (2026-10-12):** Initial creation of annotation protocol and ground-truth guidelines.