"""
flame_cv.py - Flame in Freefall: computer-vision pipeline (Engineer 3), v1.1.0

Image -> Validation -> Letterbox preprocessing -> Segmentation -> Features
      -> Confidence / quality flags -> AnalysisResult (+ mask/overlay artifacts)

Design rules (from the team blueprint):
  * deterministic, versioned preprocessing; originals are never modified
  * measurements are reported in ORIGINAL-image pixels (letterbox keeps the aspect ratio)
  * every confidence / flag is computed, never hard-coded
  * cache keys depend on input checksum + pipeline/preprocess/segmenter/config versions
  * observed / measured / estimated / inferred / hypothesized labels on every result block
  * no temperature claims from RGB imagery
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple

import cv2
import numpy as np
import PIL
from PIL import Image, ImageOps
from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------------------------
# Versions
# --------------------------------------------------------------------------------------
SCHEMA_VERSION = "1.2.0"
PIPELINE_VERSION = "cv-opencv-v1.2.0-auto"
PREPROCESS_VERSION = "letterbox-lanczos-auto-v1"
SEGMENTER_NAME = "otsu-contour-adaptive"
SEGMENTER_VERSION = "1.2.0"

DEFAULT_OPTIONS = {
    "runSegmentation": True,
    "extractGeometry": True,
    "runAppearanceAnalysis": True,
    "generateMaskArtifact": True,
}


# --------------------------------------------------------------------------------------
# Configuration (every threshold lives here, so it is hashed into the cache key)
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class CVConfig:
    # intake policy
    target_size: Optional[int] = None
    max_file_bytes: int = 10 * 1024 * 1024
    max_pixels: int = 100_000_000
    min_dim: int = 64
    allowed_formats: Tuple[str, ...] = ("jpeg", "png")
    # segmentation
    blur_kernel: Optional[int] = None
    min_threshold: Optional[int] = None  # legacy explicit floor applied on top of Otsu
    min_threshold_offset: float = 0.0
    min_area_px: Optional[int] = None  # legacy explicit minimum in processed pixels
    min_area_ratio: float = 0.0001
    multi_flame_ratio: float = 0.20  # a 2nd blob >= 20% of the largest counts as another flame
    stability_delta: float = 0.10    # +/-10% threshold perturbation for stability IoU
    # detection decision
    min_contrast: Optional[float] = None  # legacy fixed contrast threshold
    min_contrast_factor: float = 0.1
    present_score: float = 0.60
    score_contrast_weight: float = 0.5
    score_area_weight: float = 0.3
    score_stability_weight: float = 0.2
    # quality flags
    blur_gradient_min: float = 10.0  # mean boundary gradient (gray levels / pixel)
    clip_level: int = 250
    clip_fraction: float = 0.05
    lowlight_peak: Optional[int] = None  # legacy fixed threshold
    lowlight_percentile_threshold: float = 99.5
    edge_margin_px: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return json.loads(json.dumps(asdict(self)))

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()[:16]


def compute_auto_target_size(w: int, h: int, default_target: int = 512) -> int:
    """Choose a bounded square preprocessing size based on the input dimensions."""
    max_dim = max(w, h)
    if max_dim < default_target:
        return max(max_dim, 64)
    return default_target


def compute_auto_blur_kernel(w: int, h: int) -> int:
    """Choose an odd Gaussian kernel proportional to the smaller image dimension."""
    return max(3, int(min(w, h) * 0.01) | 1)


# --------------------------------------------------------------------------------------
# Errors (mapped to RFC 7807-style envelopes)
# --------------------------------------------------------------------------------------
class CVError(Exception):
    code = "CV_ERROR"
    http_status = 500
    retryable = False

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidRequestError(CVError):
    code, http_status = "INVALID_REQUEST", 400


class FileMissingError(CVError):
    code, http_status = "FILE_NOT_FOUND", 404


class FileTooLargeError(CVError):
    code, http_status = "FILE_TOO_LARGE", 413


class TooManyPixelsError(CVError):
    code, http_status = "IMAGE_TOO_LARGE", 413


class UnsupportedMediaError(CVError):
    code, http_status = "UNSUPPORTED_MEDIA_TYPE", 415


class ImageTooSmallError(CVError):
    code, http_status = "IMAGE_TOO_SMALL", 422


class DecodeError(CVError):
    code, http_status = "DECODE_FAILED", 422


# --------------------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------------------
def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def posix(p: Any) -> str:
    """Always store paths with forward slashes (fixes Windows backslashes in JSON) and repo-relative if possible."""
    if p is None:
        return ""
    path_obj = Path(str(p))
    try:
        if path_obj.is_absolute():
            path_obj = path_obj.relative_to(Path.cwd())
    except ValueError:
        pass
    return path_obj.as_posix()


def sha256_file(path: Any) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return f"sha256:{h.hexdigest()}"


def atomic_write_text(path: Any, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _clip01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


# --------------------------------------------------------------------------------------
# Contracts (Pydantic v2). One master schema = AnalysisResult.
# --------------------------------------------------------------------------------------
Label = Literal["OBSERVED", "MEASURED", "ESTIMATED", "INFERRED", "HYPOTHESIZED"]


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BoundingBox(_M):
    ymin: Optional[float] = None
    xmin: Optional[float] = None
    ymax: Optional[float] = None
    xmax: Optional[float] = None


class PreprocessingInfo(_M):
    version: str
    targetSize: int
    orientation: str
    colorSpace: str
    resizingRule: str
    scale: float
    padX: int
    padY: int
    originalWidth: int
    originalHeight: int
    contentWidth: int
    contentHeight: int
    denoising: str
    derivedUri: str
    derivedChecksum: str


class Detection(_M):
    status: Literal["PRESENT", "ABSENT", "UNCERTAIN"]
    confidence: float = Field(ge=0, le=1)
    confidenceBasis: Literal["heuristic_uncalibrated"] = "heuristic_uncalibrated"
    boundingBox: BoundingBox
    modelName: str
    modelVersion: str
    modelDigest: str


class Segmentation(_M):
    maskType: Literal["binary"] = "binary"
    maskStatus: Literal["SUCCESS", "EMPTY_MASK", "NOT_REQUESTED", "NOT_WRITTEN"]
    maskCoordinateSpace: str = "processed_letterbox"
    maskUri: Optional[str] = None
    maskChecksum: Optional[str] = None
    overlayArtifactUri: Optional[str] = None
    overlayChecksum: Optional[str] = None
    thresholdOtsu: Optional[float] = None
    thresholdApplied: Optional[float] = None


class Point(_M):
    x: float
    y: float


class Geometry(_M):
    coordinateSpace: Literal["original_image_pixels"] = "original_image_pixels"
    pixelArea: float
    centroid: Point
    perimeter: float
    aspectRatio: float
    elongation: float
    circularity: float
    symmetryLR: float
    symmetryUD: float


class ColorStats(_M):
    colorSpace: Literal["RGB"] = "RGB"
    meanR: float
    meanG: float
    meanB: float


class Appearance(_M):
    note: str = "Image-derived statistics inside the flame mask; not physical state variables."
    colorSpaceStatistics: ColorStats
    meanSaturationInMask: float
    meanValueInMask: float
    intensityP5: float
    intensityP50: float
    intensityP95: float


class PhysicalEstimates(_M):
    classification: Label = "ESTIMATED"
    mmPerPixel: float
    areaMm2: float
    perimeterMm: float
    equivalentDiameterMm: float
    assumptions: str


class Measurements(_M):
    geometry: Optional[Geometry] = None
    appearance: Optional[Appearance] = None
    physicalEstimates: Optional[PhysicalEstimates] = None


class QualityFlags(_M):
    blur: bool
    saturationClipping: bool
    lowLight: bool
    multipleFlames: bool
    occlusion: bool
    scaleAbsent: bool
    calibrationAbsent: bool


class QualityMetrics(_M):
    boundaryGradient: Optional[float] = None
    flameContrast: Optional[float] = None
    clippedFraction: Optional[float] = None
    brightnessP995: float
    significantComponents: int


class ConfidenceAndQualityFlags(_M):
    detectorConfidence: float = Field(ge=0, le=1)
    segmenterConfidence: float = Field(ge=0, le=1)
    segmenterConfidenceBasis: Literal["threshold_stability_iou"] = "threshold_stability_iou"
    qualityFlags: QualityFlags
    qualityMetrics: QualityMetrics


class ScientificInterpretation(_M):
    classification: Label
    calibrationState: Literal["ABSENT", "SCALE_ONLY"]
    fieldLabels: Dict[str, Label]
    warnings: List[str]


class Provenance(_M):
    inputUri: str
    inputChecksum: str
    pipelineVersion: str
    preprocessVersion: str
    segmenterName: str
    segmenterVersion: str
    configDigest: str
    config: Dict[str, Any]
    libraries: Dict[str, str]
    createdAt: str


class CacheInfo(_M):
    hit: bool
    key: str


class AnalysisResult(_M):
    schemaVersion: str = SCHEMA_VERSION
    status: Literal["SUCCESS"] = "SUCCESS"
    analysisId: str
    imageId: str
    pipelineVersion: str
    preprocessing: PreprocessingInfo
    detection: Detection
    segmentation: Segmentation
    measurements: Measurements
    confidenceAndQualityFlags: ConfidenceAndQualityFlags
    scientificInterpretation: ScientificInterpretation
    provenance: Provenance
    request: Optional[Dict[str, Any]] = None
    cache: Optional[CacheInfo] = None


class ErrorDetail(_M):
    code: str
    message: str
    retryable: bool
    httpStatus: int


class ErrorResponse(_M):
    status: Literal["ERROR"] = "ERROR"
    requestId: Optional[str] = None
    error: ErrorDetail


class SourceInfo(_M):
    sourceId: Optional[str] = None
    experiment: Optional[str] = None
    url: Optional[str] = None
    accessDate: Optional[str] = None


class DerivedInfo(_M):
    uri: str
    sha256: str
    preprocessVersion: str
    resizingRule: str
    scale: float
    padX: int
    padY: int


class ImageIntakeRecord(_M):
    imageId: str
    originalPath: str
    sha256: str
    sizeBytes: int
    width: int
    height: int
    mimeType: str
    validationStatus: Literal["PASSED", "FAILED"] = "PASSED"
    derived: DerivedInfo
    source: Optional[SourceInfo] = None
    license: Optional[str] = None
    groupId: Optional[str] = Field(default=None)
    split: Literal["dev", "validation", "holdout", "unassigned"] = "unassigned"
    groundTruthMaskUri: Optional[str] = None
    ingestedAt: str


class JsonlStore:
    def __init__(self, path: Any):
        self.path = Path(path)

    def _load(self) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        if not self.path.exists():
            return out
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "_key" in rec:
                    out[rec["_key"]] = rec
        return out

    def _write(self, d: Dict[str, Dict[str, Any]]) -> None:
        atomic_write_text(self.path, "".join(json.dumps(r, sort_keys=True) + "\n" for r in d.values()))

    def upsert(self, key: str, record: Dict[str, Any]) -> None:
        d = self._load()
        d[key] = {"_key": key, **record}
        self._write(d)

    def records(self) -> List[Dict[str, Any]]:
        return [{k: v for k, v in r.items() if k != "_key"} for r in self._load().values()]


class IntakeManifest(JsonlStore):
    @staticmethod
    def key_for(sha256: str, preprocess_version: str, target: int) -> str:
        return f"{sha256}:{preprocess_version}:{target}"

    def upsert_record(self, rec: ImageIntakeRecord, target: int) -> None:
        key = self.key_for(rec.sha256, rec.derived.preprocessVersion, target)
        old = self._load().get(key)
        data = rec.model_dump(mode="json")
        if old:
            for f in ("source", "license", "groupId", "split", "groundTruthMaskUri"):
                if data.get(f) in (None, "unassigned") and old.get(f) not in (None, "unassigned"):
                    data[f] = old[f]
        self.upsert(key, data)


def dedupe_legacy_manifest(path: Any) -> Dict[str, int]:
    path = Path(path)
    if not path.exists():
        return {"before": 0, "after": 0}
    shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    latest: Dict[str, Dict[str, Any]] = {}
    before = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            before += 1
            rec = {k: v for k, v in rec.items() if k != "_key"}
            sha = rec.get("sha256") or rec.get("checksumSha256")
            if "checksumSha256" in rec and "sha256" not in rec:
                rec["sha256"] = rec.pop("checksumSha256")
            key = sha or rec.get("imageId") or str(before)
            latest[key] = {**latest.get(key, {}), **rec}
    atomic_write_text(path, "".join(json.dumps(r, sort_keys=True) + "\n" for r in latest.values()))
    return {"before": before, "after": len(latest)}


def split_for_group(group_id: str, dev: float = 0.6, val: float = 0.2) -> str:
    bucket = int(hashlib.sha256(group_id.encode()).hexdigest(), 16) % 1000 / 1000.0
    return "dev" if bucket < dev else ("validation" if bucket < dev + val else "holdout")


class AnalysisCache(JsonlStore):
    VERSION_FIELDS = ("pipelineVersion", "preprocessVersion", "segmenterVersion", "configDigest")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self._load().get(key)

    def put(self, key: str, deps: Dict[str, Any], payload: Dict[str, Any]) -> None:
        self.upsert(key, {"dependencies": deps, "createdAt": utc_now(), "payload": payload})

    def invalidate_stale(self, current: Dict[str, Any]) -> int:
        d = self._load()
        keep = {k: r for k, r in d.items()
                if all(r.get("dependencies", {}).get(f) == current.get(f) for f in self.VERSION_FIELDS)}
        removed = len(d) - len(keep)
        if removed:
            self._write(keep)
        return removed


def make_cache_key(input_sha: str, cfg: CVConfig, options: Dict[str, bool],
                   mm_per_pixel: Optional[float]) -> Tuple[str, Dict[str, Any]]:
    deps = {
        "inputChecksum": input_sha,
        "pipelineVersion": PIPELINE_VERSION,
        "preprocessVersion": PREPROCESS_VERSION,
        "segmenterVersion": SEGMENTER_VERSION,
        "configDigest": cfg.digest(),
        "options": {k: bool(options[k]) for k in sorted(options)},
        "mmPerPixel": mm_per_pixel,
    }
    key = hashlib.sha256(json.dumps(deps, sort_keys=True).encode()).hexdigest()
    return key, deps


def validate_image(path: Any, cfg: CVConfig) -> Dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise FileMissingError(f"File not found: {posix(path)}")
    size = p.stat().st_size
    if size > cfg.max_file_bytes:
        raise FileTooLargeError(f"File is {size} bytes; limit is {cfg.max_file_bytes}.")
    try:
        with Image.open(p) as im:
            fmt = (im.format or "").lower()
            if fmt not in cfg.allowed_formats:
                raise UnsupportedMediaError(f"Unsupported image format '{fmt}'. Allowed: {list(cfg.allowed_formats)}")
            w, h = im.size
            if w * h > cfg.max_pixels:
                raise TooManyPixelsError(f"{w}x{h} exceeds the {cfg.max_pixels} pixel limit.")
            if w < cfg.min_dim or h < cfg.min_dim:
                raise ImageTooSmallError(f"{w}x{h} is below the {cfg.min_dim}px minimum.")
            im.verify()
        with Image.open(p) as im:
            im.load()
    except CVError:
        raise
    except Image.DecompressionBombError as e:
        raise TooManyPixelsError(str(e))
    except Exception as e:
        raise DecodeError(f"Could not decode image: {e}")
    return {
        "imageId": p.stem,
        "originalPath": posix(path),
        "sha256": sha256_file(p),
        "sizeBytes": int(size),
        "width": int(w),
        "height": int(h),
        "mimeType": f"image/{fmt}",
    }


@dataclass(frozen=True)
class Letterbox:
    scale: float
    pad_x: int
    pad_y: int
    new_w: int
    new_h: int
    orig_w: int
    orig_h: int
    target: int


def letterbox_geometry(w: int, h: int, target: int) -> Letterbox:
    s = min(target / w, target / h)
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    return Letterbox(s, (target - nw) // 2, (target - nh) // 2, nw, nh, w, h, target)


def preprocess_image(
    path: Any, out_dir: Any, cfg: CVConfig
) -> Tuple[np.ndarray, Letterbox, str, str]:
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        orig_w, orig_h = im.size
        target_size = cfg.target_size or compute_auto_target_size(orig_w, orig_h)
        lb = letterbox_geometry(orig_w, orig_h, target_size)
        resized = im.resize((lb.new_w, lb.new_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (target_size, target_size), (0, 0, 0))
    canvas.paste(resized, (lb.pad_x, lb.pad_y))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    derived = out_dir / f"{Path(path).stem}_processed.png"
    canvas.save(derived, format="PNG")
    return np.asarray(canvas, dtype=np.uint8), lb, posix(derived), sha256_file(derived)


def ingest_image(path: Any, out_dir: Any, manifest_path: Any, cfg: Optional[CVConfig] = None,
                 source: Optional[SourceInfo] = None, license: Optional[str] = None,
                 group_id: Optional[str] = None, split: Optional[str] = None) -> ImageIntakeRecord:
    cfg = cfg or CVConfig()
    intake = validate_image(path, cfg)
    if cfg.target_size is None:
        cfg = replace(cfg, target_size=compute_auto_target_size(intake["width"], intake["height"]))
    _, lb, derived_path, derived_sha = preprocess_image(path, out_dir, cfg)
    rec = _intake_record(intake, lb, derived_path, derived_sha, cfg, source, license, group_id, split)
    IntakeManifest(manifest_path).upsert_record(rec, cfg.target_size)
    return rec


def _intake_record(intake, lb, derived_path, derived_sha, cfg, source=None, license=None,
                   group_id=None, split=None) -> ImageIntakeRecord:
    if split is None:
        split = split_for_group(group_id) if group_id else "unassigned"
    return ImageIntakeRecord(
        **intake,
        derived=DerivedInfo(uri=derived_path, sha256=derived_sha, preprocessVersion=PREPROCESS_VERSION,
                            resizingRule=f"letterbox-lanczos-{cfg.target_size}x{cfg.target_size}",
                            scale=lb.scale, padX=lb.pad_x, padY=lb.pad_y),
        source=source, license=license, groupId=group_id, split=split, ingestedAt=utc_now())


def _find_main(gray_blur: np.ndarray, lb: Letterbox, cfg: CVConfig, thr: Optional[float] = None) -> Dict[str, Any]:
    crop = gray_blur[lb.pad_y:lb.pad_y + lb.new_h, lb.pad_x:lb.pad_x + lb.new_w]
    otsu, _ = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    threshold = otsu + cfg.min_threshold_offset
    if cfg.min_threshold is not None:
        threshold = max(threshold, cfg.min_threshold)
    t = float(threshold) if thr is None else float(thr)
    binm = (gray_blur > t).astype(np.uint8) * 255
    k = np.ones((3, 3), np.uint8)
    binm = cv2.morphologyEx(binm, cv2.MORPH_OPEN, k)
    binm = cv2.morphologyEx(binm, cv2.MORPH_CLOSE, k)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(binm, connectivity=8)
    res = {"main": None, "contour": None, "n_significant": 0, "otsu": float(otsu), "threshold": t,
           "largest_area": 0}
    if n <= 1:
        return res
    areas = {i: int(stats[i, cv2.CC_STAT_AREA]) for i in range(1, n)}
    res["largest_area"] = max(areas.values())
    min_area = cfg.min_area_px
    if min_area is None:
        min_area = max(10, int(lb.new_w * lb.new_h * cfg.min_area_ratio))
    valid = [i for i, a in areas.items() if a >= min_area]
    if not valid:
        return res
    best = max(valid, key=lambda i: areas[i])
    res["n_significant"] = sum(1 for i in valid if areas[i] >= cfg.multi_flame_ratio * areas[best])
    comp = (labels == best).astype(np.uint8) * 255
    cnts, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnt = max(cnts, key=cv2.contourArea)
    main = np.zeros_like(comp)
    cv2.drawContours(main, [cnt], -1, 255, cv2.FILLED)
    res["main"], res["contour"] = main, cnt
    return res


def _iou(a: Optional[np.ndarray], b: Optional[np.ndarray]) -> float:
    if a is None or b is None:
        return 0.0
    a, b = a > 0, b > 0
    union = np.logical_or(a, b).sum()
    return 1.0 if union == 0 else float(np.logical_and(a, b).sum() / union)


def _content_mask(lb: Letterbox) -> np.ndarray:
    m = np.zeros((lb.target, lb.target), np.uint8)
    m[lb.pad_y:lb.pad_y + lb.new_h, lb.pad_x:lb.pad_x + lb.new_w] = 255
    return m


def _geometry(main: np.ndarray, cnt: np.ndarray, lb: Letterbox) -> Geometry:
    s = lb.scale
    area_p = float(cv2.countNonZero(main))
    perim_p = float(cv2.arcLength(cnt, True))
    m = cv2.moments(main, binaryImage=True)
    cx, cy = m["m10"] / m["m00"], m["m01"] / m["m00"]
    x, y, w, h = cv2.boundingRect(cnt)
    (_, _), (rw, rh), _ = cv2.minAreaRect(cnt)
    crop = main[y:y + h, x:x + w] > 0
    return Geometry(
        pixelArea=round(area_p / s ** 2, 2),
        centroid=Point(x=round((cx - lb.pad_x) / s, 2), y=round((cy - lb.pad_y) / s, 2)),
        perimeter=round(perim_p / s, 2),
        aspectRatio=round(w / h, 3) if h else 0.0,
        elongation=round(max(rw, rh) / min(rw, rh), 3) if min(rw, rh) > 0 else 0.0,
        circularity=round(_clip01(4 * np.pi * area_p / perim_p ** 2), 3) if perim_p > 0 else 0.0,
        symmetryLR=round(_iou(crop, crop[:, ::-1]), 3),
        symmetryUD=round(_iou(crop, crop[::-1, :]), 3),
    )


def _bbox_original(cnt: np.ndarray, lb: Letterbox) -> BoundingBox:
    x, y, w, h = cv2.boundingRect(cnt)
    s = lb.scale
    return BoundingBox(xmin=round(max(0.0, (x - lb.pad_x) / s), 2), ymin=round(max(0.0, (y - lb.pad_y) / s), 2),
                       xmax=round(min(lb.orig_w, (x + w - lb.pad_x) / s), 2),
                       ymax=round(min(lb.orig_h, (y + h - lb.pad_y) / s), 2))


def _appearance(rgb: np.ndarray, gray: np.ndarray, main: np.ndarray) -> Appearance:
    sel = main > 0
    px = rgb[sel].astype(np.float64)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    g = gray[sel]
    return Appearance(
        colorSpaceStatistics=ColorStats(meanR=round(float(px[:, 0].mean()), 2),
                                        meanG=round(float(px[:, 1].mean()), 2),
                                        meanB=round(float(px[:, 2].mean()), 2)),
        meanSaturationInMask=round(float(hsv[..., 1][sel].mean() / 255.0), 3),
        meanValueInMask=round(float(hsv[..., 2][sel].mean() / 255.0), 3),
        intensityP5=float(np.percentile(g, 5)), intensityP50=float(np.percentile(g, 50)),
        intensityP95=float(np.percentile(g, 95)))


def _write_artifacts(rgb, main, cnt, masks_dir: Path, stem: str) -> Tuple[str, str, str, str]:
    masks_dir.mkdir(parents=True, exist_ok=True)
    mask_path = masks_dir / f"{stem}_mask.png"
    cv2.imwrite(str(mask_path), main)
    ov = rgb.copy()
    cv2.drawContours(ov, [cnt], -1, (0, 255, 0), 1)
    x, y, w, h = cv2.boundingRect(cnt)
    cv2.rectangle(ov, (x, y), (x + w - 1, y + h - 1), (255, 0, 0), 1)
    overlay_path = masks_dir / f"{stem}_overlay.png"
    cv2.imwrite(str(overlay_path), cv2.cvtColor(ov, cv2.COLOR_RGB2BGR))
    return posix(mask_path), sha256_file(mask_path), posix(overlay_path), sha256_file(overlay_path)


def _compute(req: Dict[str, Any], intake: Dict[str, Any], cfg: CVConfig, options: Dict[str, bool],
             mm: Optional[float], out_cv_dir: Any, out_masks_dir: Any, key: str,
             manifest_path: Any) -> Dict[str, Any]:
    rgb, lb, derived_path, derived_sha = preprocess_image(intake["originalPath"], out_cv_dir, cfg)
    if manifest_path:
        IntakeManifest(manifest_path).upsert_record(
            _intake_record(intake, lb, derived_path, derived_sha, cfg), cfg.target_size)

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    blur_kernel = cfg.blur_kernel or compute_auto_blur_kernel(lb.new_w, lb.new_h)
    k = blur_kernel | 1
    gb = cv2.GaussianBlur(gray, (k, k), 0)
    content = _content_mask(lb)
    content_gray = gray[content > 0]
    p995 = float(np.percentile(content_gray, cfg.lowlight_percentile_threshold))

    seg_info = _find_main(gb, lb, cfg)
    main, cnt = seg_info["main"], seg_info["contour"]
    warnings: List[str] = []
    det_conf, seg_conf = 0.0, 0.0
    status = "ABSENT"
    metrics: Dict[str, Any] = {"boundaryGradient": None, "flameContrast": None, "clippedFraction": None}
    median_intensity = float(np.median(content_gray))
    lowlight_threshold = cfg.lowlight_peak if cfg.lowlight_peak is not None else max(50.0, median_intensity * 0.8)
    flags = {"blur": False, "saturationClipping": False, "lowLight": p995 < lowlight_threshold,
             "multipleFlames": seg_info["n_significant"] > 1, "occlusion": False}

    run_seg = options["runSegmentation"]
    if not run_seg:
        main = cnt = None
        status = "UNCERTAIN"
        warnings.append("Segmentation not requested: detection status is UNCERTAIN and no measurements were computed.")
    elif main is not None:
        d = cfg.stability_delta
        t = seg_info["threshold"]
        hi = _find_main(gb, lb, cfg, thr=t * (1 + d))["main"]
        lo = _find_main(gb, lb, cfg, thr=t * (1 - d))["main"]
        seg_conf = _iou(hi, lo)

        sel = main > 0
        ring = cv2.dilate(main, np.ones((7, 7), np.uint8), iterations=2)
        outside_sel = (content > 0) & (ring == 0)
        inside_mean = float(gray[sel].mean())
        outside_mean = float(gray[outside_sel].mean()) if outside_sel.any() else 0.0
        contrast = inside_mean - outside_mean
        background_std = float(gray[outside_sel].std()) if outside_sel.any() else 10.0
        min_contrast = cfg.min_contrast if cfg.min_contrast is not None else max(
            15.0, background_std * cfg.min_contrast_factor)
        area_frac = float(sel.sum()) / float(lb.new_w * lb.new_h)
        score = (
            cfg.score_contrast_weight * _clip01(contrast / 120.0)
            + cfg.score_area_weight * _clip01(area_frac / 0.002)
            + cfg.score_stability_weight * seg_conf
        )

        if score >= cfg.present_score and contrast >= min_contrast:
            status, det_conf = "PRESENT", _clip01(score)
        elif contrast >= min_contrast / 2:
            status, det_conf = "UNCERTAIN", _clip01(score)
            warnings.append("Detection UNCERTAIN: low contrast or small/unstable region; treat measurements with caution.")
        else:
            status, det_conf = "ABSENT", min(0.9, _clip01(1 - score))

        edge = main.astype(np.int16) - cv2.erode(main, np.ones((3, 3), np.uint8)).astype(np.int16)
        gx = cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3) / 8.0
        gy = cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3) / 8.0
        grad = np.hypot(gx, gy)
        bsel = edge > 0
        bgrad = float(grad[bsel].mean()) if bsel.any() else 0.0
        clip_frac = float((rgb[sel].max(axis=1) >= cfg.clip_level).mean())
        x, y, w, h = cv2.boundingRect(cnt)
        m = cfg.edge_margin_px
        touches = (x <= lb.pad_x + m or y <= lb.pad_y + m or
                   x + w >= lb.pad_x + lb.new_w - m or y + h >= lb.pad_y + lb.new_h - m)
        flags.update(blur=bgrad < cfg.blur_gradient_min, saturationClipping=clip_frac > cfg.clip_fraction,
                     occlusion=bool(touches))
        metrics.update(boundaryGradient=round(bgrad, 2), flameContrast=round(contrast, 2),
                       clippedFraction=round(clip_frac, 4))
    else:
        det_conf = 0.9

    if status == "ABSENT":
        main = cnt = None
        det_conf = det_conf or 0.9
        seg_conf = 0.0
        warnings.append("No flame-like bright region detected; no measurements were produced.")

    geometry = appearance = physical = None
    bbox = BoundingBox()
    seg = Segmentation(maskStatus="NOT_REQUESTED" if not run_seg else "EMPTY_MASK",
                       thresholdOtsu=round(seg_info["otsu"], 2), thresholdApplied=round(seg_info["threshold"], 2))
    if main is not None:
        bbox = _bbox_original(cnt, lb)
        if options["extractGeometry"]:
            geometry = _geometry(main, cnt, lb)
        if options["runAppearanceAnalysis"]:
            appearance = _appearance(rgb, gray, main)
        if options["generateMaskArtifact"]:
            mp, msha, op, osha = _write_artifacts(rgb, main, cnt, Path(out_masks_dir), intake["imageId"])
            seg = seg.model_copy(update=dict(maskStatus="SUCCESS", maskUri=mp, maskChecksum=msha,
                                             overlayArtifactUri=op, overlayChecksum=osha))
        else:
            seg = seg.model_copy(update=dict(maskStatus="NOT_WRITTEN"))
        if mm is not None and geometry is not None:
            a = geometry.pixelArea * mm ** 2
            physical = PhysicalEstimates(
                mmPerPixel=mm, areaMm2=round(a, 3), perimeterMm=round(geometry.perimeter * mm, 3),
                equivalentDiameterMm=round(float(2 * np.sqrt(a / np.pi)), 3),
                assumptions="mmPerPixel refers to ORIGINAL image pixels at the flame plane; no lens, perspective "
                            "or depth correction applied. 2D projected values only.")

    if mm is None:
        warnings.append("Scale calibration absent: spatial measurements are in original-image pixels, not physical units.")
    warnings.append("Temperature cannot be claimed from RGB imagery without camera response, spectral and exposure "
                    "calibration; appearance values are image-derived statistics only.")
    if status != "ABSENT":
        warnings.append("Detection is a brightness-based heuristic: a bright region is not necessarily a flame "
                        "(reflections, hardware, hot surfaces). Review the overlay.")
    for flag, text in (("blur", "Blurry flame boundary."), ("saturationClipping", "Flame region has clipped/overexposed pixels."),
                       ("lowLight", "Low overall brightness."),
                       ("multipleFlames", "More than one significant bright region; only the largest was measured."),
                       ("occlusion", "Flame region touches the frame edge: possibly cropped or occluded.")):
        if flags[flag]:
            warnings.append(f"Quality flag: {text}")

    labels: Dict[str, Label] = {"detection": "INFERRED"}
    if geometry is not None:
        labels["geometry"] = "MEASURED"
    if appearance is not None:
        labels["appearance"] = "MEASURED"
    if physical is not None:
        labels["physicalEstimates"] = "ESTIMATED"

    cfg_dict = cfg.to_dict()
    result = AnalysisResult(
        analysisId=f"an_{key[:16]}",
        imageId=req.get("imageId") or intake["imageId"],
        pipelineVersion=PIPELINE_VERSION,
        preprocessing=PreprocessingInfo(
            version=PREPROCESS_VERSION, targetSize=cfg.target_size, orientation="exif_transposed", colorSpace="RGB",
            resizingRule=f"letterbox-lanczos-{cfg.target_size}x{cfg.target_size}", scale=round(lb.scale, 6),
            padX=lb.pad_x, padY=lb.pad_y, originalWidth=lb.orig_w, originalHeight=lb.orig_h,
            contentWidth=lb.new_w, contentHeight=lb.new_h,
            denoising=f"none on derived image; segmentation uses a {k}x{k} Gaussian on a copy",
            derivedUri=derived_path, derivedChecksum=derived_sha),
        detection=Detection(status=status, confidence=round(det_conf, 3), boundingBox=bbox, modelName=SEGMENTER_NAME,
                            modelVersion=SEGMENTER_VERSION, modelDigest=cfg.digest()),
        segmentation=seg,
        measurements=Measurements(geometry=geometry, appearance=appearance, physicalEstimates=physical),
        confidenceAndQualityFlags=ConfidenceAndQualityFlags(
            detectorConfidence=round(det_conf, 3), segmenterConfidence=round(seg_conf, 3),
            qualityFlags=QualityFlags(scaleAbsent=mm is None, calibrationAbsent=True, **flags),
            qualityMetrics=QualityMetrics(brightnessP995=round(p995, 2),
                                          significantComponents=int(seg_info["n_significant"]), **metrics)),
        scientificInterpretation=ScientificInterpretation(
            classification="MEASURED", calibrationState="SCALE_ONLY" if mm is not None else "ABSENT",
            fieldLabels=labels, warnings=warnings),
        provenance=Provenance(
            inputUri=intake["originalPath"], inputChecksum=intake["sha256"], pipelineVersion=PIPELINE_VERSION,
            preprocessVersion=PREPROCESS_VERSION, segmenterName=SEGMENTER_NAME, segmenterVersion=SEGMENTER_VERSION,
            configDigest=cfg.digest(), config=cfg_dict,
            libraries={"opencv": cv2.__version__, "numpy": np.__version__, "pillow": PIL.__version__},
            createdAt=utc_now()),
    )
    return result.model_dump(mode="json")


def _artifacts_exist(payload: Dict[str, Any]) -> bool:
    seg = payload.get("segmentation", {})
    return all(Path(u).exists() for u in (seg.get("maskUri"), seg.get("overlayArtifactUri")) if u)


def analyze_image(request: Dict[str, Any], out_cv_dir: Any, out_masks_dir: Any, cfg: Optional[CVConfig] = None,
                  cache: Optional[AnalysisCache] = None, manifest_path: Any = None) -> Dict[str, Any]:
    cfg = cfg or CVConfig()
    req = dict(request)
    if not req.get("imagePath"):
        raise InvalidRequestError("imagePath is required.")
    meta = req.get("metadata") or {}
    tr = meta.get("targetResolution")
    if tr:
        if len(tr) != 2 or tr[0] != tr[1] or int(tr[0]) < 64:
            raise InvalidRequestError("targetResolution must be a square [N, N] with N >= 64.")
        cfg = replace(cfg, target_size=int(tr[0]))
    mm = meta.get("mmPerPixel")
    if mm is not None and not (isinstance(mm, (int, float)) and mm > 0):
        raise InvalidRequestError("metadata.mmPerPixel must be a positive number.")
    options = {**DEFAULT_OPTIONS, **{k: bool(v) for k, v in (req.get("options") or {}).items() if k in DEFAULT_OPTIONS}}

    intake = validate_image(req["imagePath"], cfg)
    if cfg.target_size is None:
        cfg = replace(cfg, target_size=compute_auto_target_size(intake["width"], intake["height"]))
    key, deps = make_cache_key(intake["sha256"], cfg, options, mm)

    if cache is not None:
        rec = cache.get(key)
        if rec and _artifacts_exist(rec["payload"]):
            payload = copy.deepcopy(rec["payload"])
            payload["request"], payload["cache"] = req, {"hit": True, "key": key}
            return AnalysisResult.model_validate(payload).model_dump(mode="json")

    result = _compute(req, intake, cfg, options, mm, out_cv_dir, out_masks_dir, key, manifest_path)
    if cache is not None:
        cache.put(key, deps, {**result, "request": None, "cache": None})
        result["cache"] = {"hit": False, "key": key}
    result["request"] = req
    return AnalysisResult.model_validate(result).model_dump(mode="json")


def analyze_image_safe(request: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
    try:
        return analyze_image(request, *args, **kwargs)
    except CVError as e:
        return ErrorResponse(requestId=request.get("requestId"), error=ErrorDetail(
            code=e.code, message=e.message, retryable=e.retryable, httpStatus=e.http_status)).model_dump(mode="json")
    except Exception as e:
        return ErrorResponse(requestId=request.get("requestId"), error=ErrorDetail(
            code="INTERNAL_ERROR", message=f"Unexpected failure: {type(e).__name__}", retryable=False,
            httpStatus=500)).model_dump(mode="json")


def flame_analysis_api_adapter(request_payload: Dict[str, Any], output_cv_dir: Any, output_masks_dir: Any,
                               manifest_file: Any = None, cache_manifest_path: Any = None,
                               cfg: Optional[CVConfig] = None) -> Dict[str, Any]:
    cache = AnalysisCache(cache_manifest_path) if cache_manifest_path else None
    return analyze_image_safe(request_payload, output_cv_dir, output_masks_dir, cfg=cfg, cache=cache,
                              manifest_path=manifest_file)


def segmentation_metrics(pred: np.ndarray, gt: np.ndarray) -> Dict[str, float]:
    p, g = pred > 0, gt > 0
    tp = float(np.logical_and(p, g).sum())
    fp = float(np.logical_and(p, ~g).sum())
    fn = float(np.logical_and(~p, g).sum())
    union = tp + fp + fn
    iou = 1.0 if union == 0 else tp / union
    prec = 1.0 if tp + fp == 0 else tp / (tp + fp)
    rec = 1.0 if tp + fn == 0 else tp / (tp + fn)
    f1 = 1.0 if (2 * tp + fp + fn) == 0 else 2 * tp / (2 * tp + fp + fn)
    return {"iou": round(iou, 4), "f1": round(f1, 4), "precision": round(prec, 4), "recall": round(rec, 4)}


def letterbox_mask(gt_path: Any, result: Dict[str, Any]) -> np.ndarray:
    pre = result["preprocessing"]
    with Image.open(gt_path) as im:
        im = im.convert("L")
        if im.size != (pre["originalWidth"], pre["originalHeight"]):
            raise ValueError(f"GT size {im.size} != image size {(pre['originalWidth'], pre['originalHeight'])}")
        r = im.resize((pre["contentWidth"], pre["contentHeight"]), Image.Resampling.NEAREST)
    target = pre["targetSize"]
    canvas = Image.new("L", (target, target), 0)
    canvas.paste(r, (pre["padX"], pre["padY"]))
    return (np.asarray(canvas) > 127).astype(np.uint8) * 255


def run_cv_evaluation(image_dir: Any, out_cv_dir: Any, out_masks_dir: Any, gt_dir: Any = None,
                      cfg: Optional[CVConfig] = None, acceptance_iou: Optional[float] = None) -> Dict[str, Any]:
    cfg = cfg or CVConfig()
    images = sorted(p for p in Path(image_dir).glob("**/*") if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    per_image, errors, ious = [], [], []
    det_counts = {"PRESENT": 0, "ABSENT": 0, "UNCERTAIN": 0}
    flag_counts: Dict[str, int] = {}
    n_gt = 0
    for p in images:
        res = analyze_image_safe({"requestId": f"eval_{p.stem}", "imageId": p.stem, "imagePath": str(p)},
                                 out_cv_dir, out_masks_dir, cfg=cfg)
        if res.get("status") == "ERROR":
            errors.append({"imageId": p.stem, "code": res["error"]["code"], "message": res["error"]["message"]})
            continue
        det_counts[res["detection"]["status"]] += 1
        fl = res["confidenceAndQualityFlags"]["qualityFlags"]
        true_flags = [k for k, v in fl.items() if v and k not in ("scaleAbsent", "calibrationAbsent")]
        for k in true_flags:
            flag_counts[k] = flag_counts.get(k, 0) + 1
        row = {"imageId": p.stem, "detection": res["detection"]["status"],
               "detectorConfidence": res["detection"]["confidence"], "flags": true_flags}
        gt_path = None
        if gt_dir:
            for ext in (".png", ".jpg", ".jpeg", ".bmp", ".tif"):
                cand = Path(gt_dir) / f"{p.stem}{ext}"
                if cand.exists():
                    gt_path = cand
                    break
        if gt_path is not None:
            n_gt += 1
            try:
                gt = letterbox_mask(gt_path, res)
                if res["segmentation"]["maskUri"]:
                    pred = cv2.imread(res["segmentation"]["maskUri"], cv2.IMREAD_GRAYSCALE)
                else:
                    pred = np.zeros_like(gt)
                m = segmentation_metrics(pred, gt)
                row.update(m)
                ious.append(m)
            except Exception as e:
                errors.append({"imageId": p.stem, "code": "GT_ERROR", "message": str(e)})
        per_image.append(row)

    seg: Dict[str, Any] = {"status": "NOT_EVALUATED", "reason": "No ground-truth masks provided or acceptance threshold is null."}
    verdict = "NOT_EVALUATED"
    if ious and acceptance_iou is not None:
        arr = lambda k: [m[k] for m in ious]
        seg = {"status": "EVALUATED", "n": len(ious),
               "meanIoU": round(float(np.mean(arr("iou"))), 4), "medianIoU": round(float(np.median(arr("iou"))), 4),
               "minIoU": round(float(np.min(arr("iou"))), 4), "meanF1": round(float(np.mean(arr("f1"))), 4),
               "meanPrecision": round(float(np.mean(arr("precision"))), 4),
               "meanRecall": round(float(np.mean(arr("recall"))), 4)}
        verdict = "PASS" if seg["meanIoU"] >= acceptance_iou else "FAIL"
    elif ious:
        arr = lambda k: [m[k] for m in ious]
        seg = {"status": "EVALUATED", "n": len(ious),
               "meanIoU": round(float(np.mean(arr("iou"))), 4), "medianIoU": round(float(np.median(arr("iou"))), 4),
               "minIoU": round(float(np.min(arr("iou"))), 4), "meanF1": round(float(np.mean(arr("f1"))), 4),
               "meanPrecision": round(float(np.mean(arr("precision"))), 4),
               "meanRecall": round(float(np.mean(arr("recall"))), 4)}
        verdict = "REPORT_ONLY"

    n = len(per_image)
    return {
        "schemaVersion": SCHEMA_VERSION, "generatedAt": utc_now(), "pipelineVersion": PIPELINE_VERSION,
        "segmenterVersion": SEGMENTER_VERSION, "configDigest": cfg.digest(),
        "dataset": {"imageDir": posix(image_dir), "nImagesFound": len(images), "nAnalyzed": n,
                    "nWithGroundTruth": n_gt, "nErrors": len(errors)},
        "detection": {"counts": det_counts, "note": "Heuristic detector: counts are not accuracy."},
        "qualityFlagRates": {k: round(v / n, 3) for k, v in flag_counts.items()} if n else {},
        "segmentation": seg,
        "acceptance": {"metric": "meanIoU", "threshold": acceptance_iou, "verdict": verdict},
        "perImage": per_image, "errors": errors,
        "limitations": ["No measurement-error evaluation: no calibrated reference values are available.",
                        "Frames from the same experiment are highly correlated; split by group, not by frame.",
                        "Detector confidence is a heuristic score, not a calibrated probability."],
    }


def export_schemas(out_dir: Any, cfg: Optional[CVConfig] = None) -> List[str]:
    cfg = cfg or CVConfig()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    a = AnalysisResult.model_json_schema()
    a.update({"$schema": "https://json-schema.org/draft/2020-12/schema", "title": f"AnalysisResult v{SCHEMA_VERSION}"})
    i = ImageIntakeRecord.model_json_schema()
    i.update({"$schema": "https://json-schema.org/draft/2020-12/schema",
              "title": f"ImageIntakeRecord v{SCHEMA_VERSION}",
              "x-intakePolicy": {
                  "allowedFormats": list(cfg.allowed_formats), "maxFileBytes": cfg.max_file_bytes,
                  "maxPixels": cfg.max_pixels, "minDimensionPx": cfg.min_dim,
                  "checksum": "sha256 (streamed)", "exifPolicy": "apply orientation, strip metadata in derived image",
                  "preprocess": {"version": PREPROCESS_VERSION, "rule": "aspect-preserving Lanczos resize + black padding",
                                 "targetSize": cfg.target_size, "derivedFormat": "PNG (lossless)"},
                  "splitPolicy": "split by groupId (experiment/run), never by frame",
                  "quarantine": "files failing validation are not preprocessed or manifested",
                  "requiredForTraining": ["license", "source", "groupId"]}})
    paths = []
    for name, schema in (("analysis_result.schema.json", a), ("image_intake_schema.json", i)):
        p = out_dir / name
        p.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
        paths.append(posix(p))
    return paths


def make_synthetic_flame(path: Any, size: Tuple[int, int] = (3008, 2000),
                         blobs: Iterable[Tuple[int, int, int, int]] = ((1500, 1000, 300, 300),),
                         noise: float = 2.0, seed: int = 0, gt_path: Any = None, soften: float = 5.0) -> None:
    w, h = size
    rng = np.random.default_rng(seed)
    gt = np.zeros((h, w), np.uint8)
    for cx, cy, rx, ry in blobs:
        cv2.ellipse(gt, (cx, cy), (rx, ry), 0, 0, 360, 255, -1)
    soft = cv2.GaussianBlur(gt.astype(np.float32) / 255.0, (0, 0), soften)
    img = np.stack([soft * 255, soft * 200, soft * 120], axis=-1)
    img += rng.normal(0, noise, img.shape)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(path, quality=95)
    if gt_path:
        Image.fromarray(gt).save(gt_path)
