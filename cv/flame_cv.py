"""
flame_cv.py - Flame in Freefall: computer-vision pipeline (Engineer 3), v1.1.0 (Auto-Adaptive)
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
# Configuration (Supports auto-calculation flags or base defaults)
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class CVConfig:
    target_size: Optional[int] = None  # If None, computed automatically from input image dimensions
    max_file_bytes: int = 10 * 1024 * 1024
    max_pixels: int = 100_000_000
    min_dim: int = 64
    allowed_formats: Tuple[str, ...] = ("jpeg", "png")
    
    # Auto-adaptive or fallback hyperparameters
    blur_kernel: Optional[int] = None  # Auto-computed if None based on image size
    min_threshold_offset: float = 0.0  # Dynamic offset applied on top of Otsu
    min_area_ratio: float = 0.0001     # Minimum area as a ratio of total image pixels
    multi_flame_ratio: float = 0.20  
    stability_delta: float = 0.10    
    
    min_contrast_factor: float = 0.1   # Dynamic contrast factor based on image std
    present_score: float = 0.60
    
    score_contrast_weight: float = 0.5
    score_area_weight: float = 0.3
    score_stability_weight: float = 0.2
    
    blur_gradient_min: float = 10.0  
    clip_level: int = 250
    clip_fraction: float = 0.05
    lowlight_percentile_threshold: float = 99.5
    edge_margin_px: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return json.loads(json.dumps(asdict(self)))

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()[:16]


# --------------------------------------------------------------------------------------
# Auto-Adaptive Parameter Calculation Functions
# --------------------------------------------------------------------------------------
def compute_auto_target_size(w: int, h: int, default_target: int = 512) -> int:
    """Automatically computes target size based on image dimensions while maintaining bounds."""
    max_dim = max(w, h)
    if max_dim < default_target:
        return max(max_dim, 64)
    return default_target


def compute_auto_blur_kernel(w: int, h: int) -> int:
    """Automatically computes an odd blur kernel size proportional to image dimensions."""
    dim = min(w, h)
    k = int(dim * 0.01) | 1  # ~1% of the smallest dimension, forced to be odd
    return max(3, k)


def get_image_paths_from_directory(image_dir: Any, extensions: Tuple[str, ...] = (".jpg", ".jpeg", ".png")) -> List[Path]:
    dir_path = Path(image_dir)
    if not dir_path.exists():
        return []
    return sorted(p for p in dir_path.glob("**/*") if p.suffix.lower() in extensions)


def get_ground_truth_path(image_path: Any, gt_dir: Any, extensions: Tuple[str, ...] = (".png", ".jpg", ".jpeg", ".bmp", ".tif")) -> Optional[Path]:
    if not gt_dir:
        return None
    p = Path(image_path)
    gt_base = Path(gt_dir)
    for ext in extensions:
        cand = gt_base / f"{p.stem}{ext}"
        if cand.exists():
            return cand
    return None


# --------------------------------------------------------------------------------------
# Errors and Utilities (Same robust structure)
# --------------------------------------------------------------------------------------
class CVError(Exception):
    code = "CV_ERROR"
    http_status = 500
    retryable = False

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class InvalidRequestError(CVError): code, http_status = "INVALID_REQUEST", 400
class FileMissingError(CVError): code, http_status = "FILE_NOT_FOUND", 404
class FileTooLargeError(CVError): code, http_status = "FILE_TOO_LARGE", 413
class TooManyPixelsError(CVError): code, http_status = "IMAGE_TOO_LARGE", 413
class UnsupportedMediaError(CVError): code, http_status = "UNSUPPORTED_MEDIA_TYPE", 415
class ImageTooSmallError(CVError): code, http_status = "IMAGE_TOO_SMALL", 422
class DecodeError(CVError): code, http_status = "DECODE_FAILED", 422


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def posix(p: Any) -> str:
    if p is None: return ""
    path_obj = Path(str(p))
    try:
        if path_obj.is_absolute(): path_obj = path_obj.relative_to(Path.cwd())
    except ValueError: pass
    return path_obj.as_posix()

def sha256_file(path: Any) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return f"sha256:{h.hexdigest()}"

def atomic_write_text(path: Any, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f: f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.remove(tmp)

def _clip01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


# --------------------------------------------------------------------------------------
# Contracts & Pydantic Schemas (Abbreviated for integration)
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

class Point(_M): x: float; y: float

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

class ColorStats(_M): colorSpace: Literal["RGB"] = "RGB"; meanR: float; meanG: float; meanB: float

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
    blur: bool; saturationClipping: bool; lowLight: bool; multipleFlames: bool; occlusion: bool; scaleAbsent: bool; calibrationAbsent: bool

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
    inputUri: str; inputChecksum: str; pipelineVersion: str; preprocessVersion: str; segmenterName: str; segmenterVersion: str; configDigest: str; config: Dict[str, Any]; libraries: Dict[str, str]; createdAt: str

class CacheInfo(_M): hit: bool; key: str

class AnalysisResult(_M):
    schemaVersion: str = SCHEMA_VERSION
    status: Literal["SUCCESS"] = "SUCCESS"
    analysisId: str; imageId: str; pipelineVersion: str; preprocessing: PreprocessingInfo; detection: Detection; segmentation: Segmentation; measurements: Measurements; confidenceAndQualityFlags: ConfidenceAndQualityFlags; scientificInterpretation: ScientificInterpretation; provenance: Provenance; request: Optional[Dict[str, Any]] = None; cache: Optional[CacheInfo] = None

class ErrorDetail(_M): code: str; message: str; retryable: bool; httpStatus: int
class ErrorResponse(_M): status: Literal["ERROR"] = "ERROR"; requestId: Optional[str] = None; error: ErrorDetail

class DerivedInfo(_M): uri: str; sha256: str; preprocessVersion: str; resizingRule: str; scale: float; padX: int; padY: int

class ImageIntakeRecord(_M):
    imageId: str; originalPath: str; sha256: str; sizeBytes: int; width: int; height: int; mimeType: str; validationStatus: Literal["PASSED", "FAILED"] = "PASSED"; derived: DerivedInfo; source: Optional[Any] = None; license: Optional[str] = None; groupId: Optional[str] = Field(default=None); split: Literal["dev", "validation", "holdout", "unassigned"] = "unassigned"; groundTruthMaskUri: Optional[str] = None; ingestedAt: str


# --------------------------------------------------------------------------------------
# Core Processing with Auto-Adaptive Logic
# --------------------------------------------------------------------------------------
def validate_image(path: Any, cfg: CVConfig) -> Dict[str, Any]:
    p = Path(path)
    if not p.is_file(): raise FileMissingError(f"File not found: {posix(path)}")
    size = p.stat().st_size
    if size > cfg.max_file_bytes: raise FileTooLargeError(f"File is {size} bytes; limit is {cfg.max_file_bytes}.")
    try:
        with Image.open(p) as im:
            fmt = (im.format or "").lower()
            if fmt not in cfg.allowed_formats: raise UnsupportedMediaError(f"Unsupported image format '{fmt}'")
            w, h = im.size
            if w * h > cfg.max_pixels: raise TooManyPixelsError(f"Too many pixels")
            if w < cfg.min_dim or h < cfg.min_dim: raise ImageTooSmallError(f"Image too small")
            im.verify()
        with Image.open(p) as im: im.load()
    except CVError: raise
    except Exception as e: raise DecodeError(f"Could not decode image: {e}")
    return {"imageId": p.stem, "originalPath": posix(path), "sha256": sha256_file(p), "sizeBytes": int(size), "width": int(w), "height": int(h), "mimeType": f"image/{fmt}"}


@dataclass(frozen=True)
class Letterbox:
    scale: float; pad_x: int; pad_y: int; new_w: int; new_h: int; orig_w: int; orig_h: int; target: int


def letterbox_geometry(w: int, h: int, target: int) -> Letterbox:
    s = min(target / w, target / h)
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    return Letterbox(s, (target - nw) // 2, (target - nh) // 2, nw, nh, w, h, target)


def preprocess_image(path: Any, out_dir: Any, cfg: CVConfig) -> Tuple[np.ndarray, Letterbox, str, str, CVConfig]:
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        orig_w, orig_h = im.size
        
        # Auto-compute target size if not explicitly provided
        effective_target = cfg.target_size if cfg.target_size is not None else compute_auto_target_size(orig_w, orig_h)
        cfg = replace(cfg, target_size=effective_target)
        
        lb = letterbox_geometry(orig_w, orig_h, effective_target)
        resized = im.resize((lb.new_w, lb.new_h), Image.Resampling.LANCZOS)
        
    canvas = Image.new("RGB", (effective_target, effective_target), (0, 0, 0))
    canvas.paste(resized, (lb.pad_x, lb.pad_y))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    derived = out_dir / f"{Path(path).stem}_processed.png"
    canvas.save(derived, format="PNG")
    return np.asarray(canvas, dtype=np.uint8), lb, posix(derived), sha256_file(derived), cfg


def _find_main(gray_blur: np.ndarray, lb: Letterbox, cfg: CVConfig, thr: Optional[float] = None) -> Dict[str, Any]:
    crop = gray_blur[lb.pad_y:lb.pad_y + lb.new_h, lb.pad_x:lb.pad_x + lb.new_w]
    otsu, _ = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Auto-dynamic threshold calculation
    dynamic_threshold = otsu + cfg.min_threshold_offset
    t = float(dynamic_threshold) if thr is None else float(thr)
    
    binm = (gray_blur > t).astype(np.uint8) * 255
    k = np.ones((3, 3), np.uint8)
    binm = cv2.morphologyEx(binm, cv2.MORPH_OPEN, k)
    binm = cv2.morphologyEx(binm, cv2.MORPH_CLOSE, k)
    
    n, labels, stats, _ = cv2.connectedComponentsWithStats(binm, connectivity=8)
    res = {"main": None, "contour": None, "n_significant": 0, "otsu": float(otsu), "threshold": t, "largest_area": 0}
    if n <= 1: return res
    
    areas = {i: int(stats[i, cv2.CC_STAT_AREA]) for i in range(1, n)}
    res["largest_area"] = max(areas.values())
    
    # Auto-adaptive minimum area based on image dimensions ratio
    total_pixels = lb.new_w * lb.new_h
    adaptive_min_area = max(10, int(total_pixels * cfg.min_area_ratio))
    
    valid = [i for i, a in areas.items() if a >= adaptive_min_area]
    if not valid: return res
    
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
    if a is None or b is None: return 0.0
    a, b = a > 0, b > 0
    union = np.logical_or(a, b).sum()
    return 1.0 if union == 0 else float(np.logical_and(a, b).sum() / union)


def _content_mask(lb: Letterbox) -> np.ndarray:
    m = np.zeros((lb.target, lb.target), np.uint8)
    m[lb.pad_y:lb.pad_y + lb.new_h, lb.pad_x:lb.pad_x + lb.new_w] = 255
    return m


def _compute(req: Dict[str, Any], intake: Dict[str, Any], cfg: CVConfig, options: Dict[str, bool],
             mm: Optional[float], out_cv_dir: Any, out_masks_dir: Any, key: str) -> Dict[str, Any]:
    
    rgb, lb, derived_path, derived_sha, cfg = preprocess_image(intake["originalPath"], out_cv_dir, cfg)

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    
    # Auto-compute blur kernel if not specified
    effective_blur_kernel = cfg.blur_kernel if cfg.blur_kernel is not None else compute_auto_blur_kernel(lb.new_w, lb.new_h)
    k = effective_blur_kernel | 1
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
    
    # Dynamic low-light threshold based on image statistics (e.g. median intensity)
    median_intensity = float(np.median(content_gray))
    dynamic_lowlight_peak = max(50.0, median_intensity * 0.8)
    
    flags = {"blur": False, "saturationClipping": False, "lowLight": p995 < dynamic_lowlight_peak,
             "multipleFlames": seg_info["n_significant"] > 1, "occlusion": False}

    run_seg = options["runSegmentation"]
    if not run_seg:
        main = cnt = None
        status = "UNCERTAIN"
        warnings.append("Segmentation not requested.")
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
        
        # Adaptive min contrast based on standard deviation of background
        bg_std = float(gray[outside_sel].std()) if outside_sel.any() else 10.0
        adaptive_min_contrast = max(15.0, bg_std * cfg.min_contrast_factor)
        
        area_frac = float(sel.sum()) / float(lb.new_w * lb.new_h)
        score = (cfg.score_contrast_weight * _clip01(contrast / 120.0) + 
                 cfg.score_area_weight * _clip01(area_frac / 0.002) + 
                 cfg.score_stability_weight * seg_conf)

        if score >= cfg.present_score and contrast >= adaptive_min_contrast:
            status, det_conf = "PRESENT", _clip01(score)
        elif contrast >= adaptive_min_contrast / 2:
            status, det_conf = "UNCERTAIN", _clip01(score)
            warnings.append("Detection UNCERTAIN.")
        else:
            status, det_conf = "ABSENT", min(0.9, _clip01(1 - score))

        edge = main.astype(np.int16) - cv2.erode(main, np.ones((3, 3), np.uint8)).astype(np.int16)
        gx = cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3) / 8.0
        gy = cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3) / 8.0
        grad = np.hypot(gx, gy)
        bsel = edge > 0
        bgrad = float(grad[bsel].mean()) if bsel.any() else 0.0
        clip_frac = float((rgb[sel].max(axis=1) >= cfg.clip_level).mean())
        
        x, y, w_b, h_b = cv2.boundingRect(cnt)
        m = cfg.edge_margin_px
        touches = (x <= lb.pad_x + m or y <= lb.pad_y + m or
                   x + w_b >= lb.pad_x + lb.new_w - m or y + h_b >= lb.pad_y + lb.new_h - m)
        flags.update(blur=bgrad < cfg.blur_gradient_min, saturationClipping=clip_frac > cfg.clip_fraction, occlusion=bool(touches))
        metrics.update(boundaryGradient=round(bgrad, 2), flameContrast=round(contrast, 2), clippedFraction=round(clip_frac, 4))
    else:
        det_conf = 0.9

    # Additional result construction wrappers remain fully aligned with schema...
    return AnalysisResult(
        analysisId=f"an_{key[:16]}",
        imageId=req.get("imageId") or intake["imageId"],
        pipelineVersion=PIPELINE_VERSION,
        preprocessing=PreprocessingInfo(
            version=PREPROCESS_VERSION, targetSize=cfg.target_size, orientation="exif_transposed", colorSpace="RGB",
            resizingRule=f"letterbox-lanczos-{cfg.target_size}x{cfg.target_size}", scale=round(lb.scale, 6),
            padX=lb.pad_x, padY=lb.pad_y, originalWidth=lb.orig_w, originalHeight=lb.orig_h,
            contentWidth=lb.new_w, contentHeight=lb.new_h,
            denoising=f"auto-computed blur kernel {k}x{k}",
            derivedUri=derived_path, derivedChecksum=derived_sha),
        detection=Detection(status=status, confidence=round(det_conf, 3), boundingBox=BoundingBox(), modelName=SEGMENTER_NAME,
                            modelVersion=SEGMENTER_VERSION, modelDigest=cfg.digest()),
        segmentation=Segmentation(maskStatus="SUCCESS" if main is not None else "EMPTY_MASK"),
        measurements=Measurements(),
        confidenceAndQualityFlags=ConfidenceAndQualityFlags(
            detectorConfidence=round(det_conf, 3), segmenterConfidence=round(seg_conf, 3),
            qualityFlags=QualityFlags(scaleAbsent=mm is None, calibrationAbsent=True, **flags),
            qualityMetrics=QualityMetrics(brightnessP995=round(p995, 2), significantComponents=int(seg_info["n_significant"]), **metrics)),
        scientificInterpretation=ScientificInterpretation(
            classification="MEASURED", calibrationState="SCALE_ONLY" if mm is not None else "ABSENT",
            fieldLabels={"detection": "INFERRED"}, warnings=warnings),
        provenance=Provenance(
            inputUri=intake["originalPath"], inputChecksum=intake["sha256"], pipelineVersion=PIPELINE_VERSION,
            preprocessVersion=PREPROCESS_VERSION, segmenterName=SEGMENTER_NAME, segmenterVersion=SEGMENTER_VERSION,
            configDigest=cfg.digest(), config=cfg.to_dict(),
            libraries={"opencv": cv2.__version__, "numpy": np.__version__, "pillow": PIL.__version__},
            createdAt=utc_now()),
    ).model_dump(mode="json")