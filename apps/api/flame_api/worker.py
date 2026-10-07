import hashlib
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from flame_api.config import get_settings
from flame_api.database import SessionLocal
from flame_api.models import AnalysisRecord
from flame_api.storage import get_bytes, put_file

settings = get_settings()
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _now():
    return datetime.now(UTC)


def process_analysis(analysis_id: str) -> None:
    session = SessionLocal()
    record = session.get(AnalysisRecord, analysis_id)
    if record is None or record.status != "queued":
        session.close()
        return
    record.status = "processing"
    record.updated_at = _now()
    record.payload = {**record.payload, "status": "processing", "updated_at": record.updated_at.isoformat().replace("+00:00", "Z"), "started_at": record.updated_at.isoformat().replace("+00:00", "Z"), "poll_after_ms": 1000}
    session.commit()
    payload = dict(record.payload)
    artifacts = dict(record.artifacts)
    session.close()

    try:
        import cv2
        from cv.flame_cv import CVConfig, analyze_image

        input_data = payload["input"]
        original = artifacts["original"]
        image_bytes = get_bytes(original["object_key"])
        with tempfile.TemporaryDirectory(prefix="flame-cv-") as working:
            work = Path(working)
            suffix = ".png" if input_data["media_type"] == "image/png" else ".jpg"
            image_path = work / f"original{suffix}"
            image_path.write_bytes(image_bytes)
            calibration = input_data["calibration"]
            mm_per_pixel = 1 / calibration["scale_px_per_mm"] if calibration["scale_px_per_mm"] else None
            legacy = analyze_image(
                {"imagePath": str(image_path), "imageId": analysis_id, "metadata": {"mmPerPixel": mm_per_pixel}},
                work / "processed",
                work / "masks",
                cfg=CVConfig(max_pixels=settings.max_image_pixels),
            )
            result = _adapt_result(legacy, input_data, work)
            produced = []
            preprocessing_path = Path(legacy["preprocessing"]["derivedUri"])
            if preprocessing_path.exists():
                produced.append(("preprocessed", preprocessing_path, "image/png"))
            for kind, uri in (("mask", legacy["segmentation"].get("maskUri")), ("overlay", legacy["segmentation"].get("overlayArtifactUri"))):
                if uri and Path(uri).exists():
                    produced.append((kind, Path(uri), "image/png"))
            for kind, path, media_type in produced:
                key = f"analyses/{analysis_id}/{kind}.png"
                put_file(key, str(path), media_type)
                file_bytes = path.read_bytes()
                with Image.open(path) as artifact_image:
                    artifact_width, artifact_height = artifact_image.size
                artifact = {
                    "kind": kind,
                    "url": f"/api/analyses/{analysis_id}/artifacts/{kind}",
                    "media_type": media_type,
                    "sha256": hashlib.sha256(file_bytes).hexdigest(),
                    "width": artifact_width,
                    "height": artifact_height,
                    "size_bytes": len(file_bytes),
                    "object_key": key,
                }
                artifacts[kind] = artifact

        now = _now()
        session = SessionLocal()
        record = session.get(AnalysisRecord, analysis_id)
        if record:
            completed = {
                **record.payload,
                "status": "completed",
                "updated_at": now.isoformat().replace("+00:00", "Z"),
                "completed_at": now.isoformat().replace("+00:00", "Z"),
                "pipeline": result["pipeline"],
                "result": result["result"],
                "warnings": result["warnings"],
                "artifacts": [{key: value for key, value in item.items() if key != "object_key"} for item in artifacts.values()],
                "poll_after_ms": None,
            }
            record.status = "completed"
            record.updated_at = now
            record.completed_at = now
            record.pipeline_version = result["pipeline"]["pipeline_version"]
            record.payload = completed
            record.artifacts = artifacts
            session.commit()
        session.close()
    except Exception as exc:
        session = SessionLocal()
        record = session.get(AnalysisRecord, analysis_id)
        if record:
            now = _now()
            failure_code = "MODEL_UNAVAILABLE" if isinstance(exc, ImportError) else "IMAGE_DECODE_FAILED" if isinstance(exc, (OSError, ValueError)) else "PIPELINE_ERROR"
            record.status = "failed"
            record.updated_at = now
            record.completed_at = now
            record.payload = {
                **record.payload,
                "status": "failed",
                "updated_at": now.isoformat().replace("+00:00", "Z"),
                "completed_at": now.isoformat().replace("+00:00", "Z"),
                "failure": {"code": failure_code, "message": "Image analysis could not be completed.", "retryable": failure_code == "MODEL_UNAVAILABLE"},
                "poll_after_ms": None,
            }
            session.commit()
        session.close()
        raise


def _measured(value, unit, method, classification="measured"):
    return {"value": value, "unit": unit, "classification": classification, "method": method, "uncertainty": None}


def _adapt_result(legacy, input_data, work):
    import cv2

    detection = legacy["detection"]
    geometry = legacy["measurements"].get("geometry") or {}
    appearance = legacy["measurements"].get("appearance") or {}
    box = detection.get("boundingBox") or {}
    detected = detection["status"].lower()
    bbox = None if detected == "absent" else {"x_min": box.get("xmin"), "y_min": box.get("ymin"), "x_max": box.get("xmax"), "y_max": box.get("ymax")}
    width = (box.get("xmax", 0) - box.get("xmin", 0)) if bbox else None
    height = (box.get("ymax", 0) - box.get("ymin", 0)) if bbox else None
    area = geometry.get("pixelArea")
    perimeter = geometry.get("perimeter")
    centroid = geometry.get("centroid") or {}
    measured_geometry = {
        "area": _measured(area, "px2", "mask_pixel_count"),
        "width": _measured(width, "px", "mask_bbox"),
        "height": _measured(height, "px", "mask_bbox"),
        "perimeter": _measured(perimeter, "px", "contour_perimeter_opencv"),
        "centroid": {"x": centroid.get("x"), "y": centroid.get("y"), "unit": "px", "classification": "measured", "method": "mask_moments"},
        "aspect_ratio": _measured(height / width if width else None, "ratio", "mask_bbox_height_over_width"),
        "circularity": _measured(geometry.get("circularity"), "ratio", "contour_circularity"),
    }
    physical = None
    calibration = input_data["calibration"]
    if calibration["scale_px_per_mm"] and area is not None and width is not None and height is not None and perimeter is not None:
        mm_per_pixel = 1 / calibration["scale_px_per_mm"]
        physical = {
            "area": _measured(area * mm_per_pixel**2, "mm2", "pixel_area_scaled", "estimated"),
            "width": _measured(width * mm_per_pixel, "mm", "bbox_width_scaled", "estimated"),
            "height": _measured(height * mm_per_pixel, "mm", "bbox_height_scaled", "estimated"),
            "perimeter": _measured(perimeter * mm_per_pixel, "mm", "contour_perimeter_scaled", "estimated"),
        }
    mean_rgb: list[float | None] = [None, None, None]
    mean_intensity = None
    saturated_fraction = None
    if legacy["segmentation"].get("maskUri"):
        with Image.open(legacy["provenance"]["inputUri"]) as source_image:
            image = np.asarray(ImageOps.exif_transpose(source_image).convert("RGB"))
        mask = cv2.imread(legacy["segmentation"]["maskUri"], cv2.IMREAD_GRAYSCALE)
        pre = legacy["preprocessing"]
        if mask is not None:
            content_mask = mask[
                pre["padY"]:pre["padY"] + pre["contentHeight"],
                pre["padX"]:pre["padX"] + pre["contentWidth"],
            ]
            original_mask = cv2.resize(
                content_mask,
                (pre["originalWidth"], pre["originalHeight"]),
                interpolation=cv2.INTER_NEAREST,
            )
            selected = image[original_mask > 0]
            if selected.size:
                mean_rgb = [float(value) for value in selected.mean(axis=0)]
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                mean_intensity = float(gray[original_mask > 0].mean())
                saturated_fraction = float(np.any(selected == 255, axis=1).mean())
    measurements = {
        "geometry_px": measured_geometry,
        "geometry_physical": physical,
        "appearance": {
            "color_space": "RGB",
            "mean_r": _measured(mean_rgb[0], "intensity_8bit", "masked_mean_rgb") if mean_rgb[0] is not None else _measured(None, "intensity_8bit", "masked_mean_rgb"),
            "mean_g": _measured(mean_rgb[1], "intensity_8bit", "masked_mean_rgb") if mean_rgb[1] is not None else _measured(None, "intensity_8bit", "masked_mean_rgb"),
            "mean_b": _measured(mean_rgb[2], "intensity_8bit", "masked_mean_rgb") if mean_rgb[2] is not None else _measured(None, "intensity_8bit", "masked_mean_rgb"),
            "mean_intensity": _measured(mean_intensity, "intensity_8bit", "masked_mean_luma_bt601"),
            "saturated_fraction": _measured(saturated_fraction, "fraction", "channel_max_pixel_fraction"),
            "physical_interpretation": "none",
        },
    }
    if detected == "absent":
        for value in measured_geometry.values():
            if isinstance(value, dict) and "value" in value:
                value["value"] = None
            elif isinstance(value, dict) and "x" in value:
                value["x"] = value["y"] = None
        for value in measurements["appearance"].values():
            if isinstance(value, dict) and "value" in value:
                value["value"] = None
    flags = legacy["confidenceAndQualityFlags"]["qualityFlags"]
    quality_flags = {
        "blur": flags.get("blur"),
        "saturation_clipping": flags.get("saturationClipping"),
        "low_light": flags.get("lowLight"),
        "multiple_flames": flags.get("multipleFlames"),
        "occlusion": flags.get("occlusion"),
        "scale_absent": calibration["state"] == "absent",
        "calibration_absent": True,
    }
    contours = []
    if legacy["segmentation"].get("maskUri"):
        mask = cv2.imread(legacy["segmentation"]["maskUri"], cv2.IMREAD_GRAYSCALE)
        if mask is not None:
            found, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            scale = legacy["preprocessing"]["scale"]
            pad_x, pad_y = legacy["preprocessing"]["padX"], legacy["preprocessing"]["padY"]
            for contour in found[:10]:
                points = cv2.approxPolyDP(contour, 2.0, True).reshape(-1, 2)
                contours.append([
                    {
                        "x": min(float(input_data["width"]), max(0.0, (float(x) - pad_x) / scale)),
                        "y": min(float(input_data["height"]), max(0.0, (float(y) - pad_y) / scale)),
                    }
                    for x, y in points
                ])
    result = {
        "detection": {"status": detected, "confidence": detection.get("confidence"), "bounding_box": bbox},
        "segmentation": None if detected == "absent" else {"mask_type": "binary", "threshold_policy": "otsu-v1", "component_count": legacy["confidenceAndQualityFlags"]["qualityMetrics"].get("significantComponents", len(contours)), "confidence": legacy["confidenceAndQualityFlags"].get("segmenterConfidence"), "contours": contours, "simplification_tolerance_px": 2.0},
        "measurements": measurements,
        "quality_flags": quality_flags,
        "observations": [{"statement_id": "cv-detection", "text": "Brightness-based CV detection: " + detected + ".", "claim_class": "inferred", "origin": "cv_pipeline", "evidence_ids": [], "measurement_refs": []}],
    }
    warnings = [
        {"code": "TEMPERATURE_NOT_AVAILABLE", "severity": "info", "message": "Temperature is not reported without radiometric calibration."},
    ]
    if calibration["state"] == "absent":
        warnings.append({"code": "SCALE_CALIBRATION_ABSENT", "severity": "warning", "message": "Spatial measurements are in pixels; no scale calibration was supplied."})
    if detected != "absent":
        warnings.append({"code": "LOW_DETECTION_CONFIDENCE", "severity": "warning", "message": "Brightness-based detection is heuristic; inspect the overlay before scientific use."})
    pipeline = {
        "pipeline_version": legacy["pipelineVersion"],
        "preprocessing_version": legacy["preprocessing"]["version"],
        "detector": {"name": detection["modelName"], "version": detection["modelVersion"], "artifact_digest": None},
        "segmenter": {"name": detection["modelName"], "version": detection["modelVersion"], "artifact_digest": None},
        "measurement_space": "original_oriented_px",
    }
    return {"pipeline": pipeline, "result": result, "warnings": warnings}