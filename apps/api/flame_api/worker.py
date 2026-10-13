import hashlib
import json
import logging
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from flame_api.config import get_settings
from flame_api.database import SessionLocal
from ai.providers.contracts.errors import ProviderError
from ai.providers.contracts.vision import ImageAnalysisRequest
from ai.routing import NoCompatibleProvider
from flame_api import ai_runtime
from flame_api.generation import interpret_analysis
from flame_api.ids import stable_ulid
from flame_api.models import AnalysisRecord, EvidenceRecord, ExperimentCondition, FileRecord
from flame_api.storage import get_bytes, put_file

settings = get_settings()
logger = logging.getLogger("flame_worker")
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
        import cv2  # noqa: F401  (fail fast with MODEL_UNAVAILABLE when OpenCV is missing)

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
            # Vision goes through the router: FLAME_CV_PROVIDER picks the preferred provider, the other
            # is the fallback, offline_only never contacts the HF Space, and no text model is eligible.
            request = ImageAnalysisRequest(
                image_path=image_path, image_id=analysis_id, media_type=input_data["media_type"], work_dir=work,
                mm_per_pixel=mm_per_pixel, max_pixels=settings.max_image_pixels,
            )
            routed_cv = ai_runtime.get_router(settings).route("vision.analyze", lambda provider: provider.analyze_image(request))
            legacy = routed_cv.value.analysis
            cv_execution = routed_cv.metadata.to_dict()
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
        aura_request = None
        if record:
            completed = {
                **record.payload,
                "status": "completed",
                "updated_at": now.isoformat().replace("+00:00", "Z"),
                "completed_at": now.isoformat().replace("+00:00", "Z"),
                "pipeline": {**result["pipeline"], "execution": cv_execution},
                "result": result["result"],
                "warnings": result["warnings"],
                "artifacts": [{key: value for key, value in item.items() if key != "object_key"} for item in artifacts.values()],
                "poll_after_ms": None,
            }
            measurement_evidence = _image_measurement_evidence(
                session, record, result, input_data, now
            )
            result["result"]["observations"] = [
                {
                    **observation,
                    "evidence_ids": list(
                        dict.fromkeys(
                            [*observation.get("evidence_ids", []), measurement_evidence.evidence_id]
                        )
                    ),
                }
                for observation in result["result"]["observations"]
            ]
            completed["result"] = result["result"]
            record.status = "completed"
            record.updated_at = now
            record.completed_at = now
            record.pipeline_version = result["pipeline"]["pipeline_version"]
            record.payload = completed
            record.artifacts = artifacts
            session.add(measurement_evidence)
            if completed["interpretation"]["status"] == "pending":
                aura_request = _aura_request_context(session, record, measurement_evidence)
            session.commit()
        session.close()
        if aura_request is not None:
            _run_aura_interpretation(
                analysis_id,
                aura_request["context"],
                aura_request["evidence_ids"],
            )
    except Exception as exc:
        session = SessionLocal()
        record = session.get(AnalysisRecord, analysis_id)
        if record:
            now = _now()
            failure_code = "MODEL_UNAVAILABLE" if isinstance(exc, (ImportError, ProviderError, NoCompatibleProvider)) else "IMAGE_DECODE_FAILED" if isinstance(exc, (OSError, ValueError)) else "PIPELINE_ERROR"
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


def _image_measurement_evidence(session, record, result, input_data, now):
    source_file = (
        session.get(FileRecord, input_data["source_file_id"])
        if input_data.get("source_file_id")
        else None
    )
    evidence_id = stable_ulid(
        f"image-measurement:{record.analysis_id}:{result['pipeline']['pipeline_version']}"
    )
    citation = f"Flame CV analysis {record.analysis_id}, image SHA-256 {record.image_sha256}"
    frame_index = input_data.get("frame_index")
    return EvidenceRecord(
        evidence_id=evidence_id,
        source_id=source_file.source_id if source_file else None,
        file_id=source_file.file_id if source_file else None,
        document_id=None,
        experiment_id=record.experiment_id,
        analysis_id=record.analysis_id,
        kind="image_measurement",
        origin="calculated_measurement",
        excerpt=None,
        locator={
            "type": "frame" if frame_index is not None else "file",
            "page": None,
            "section": None,
            "row": None,
            "frame_index": frame_index,
            "label": f"image analysis {record.analysis_id}",
        },
        payload={
            "citation": citation,
            "value": None,
            "measurement_or_claim_type": "flame_image_measurements",
            "extraction_method": "cv_pipeline",
            "extraction_confidence": None,
            "review_status": "machine_extracted",
            "transformation_id": result["pipeline"]["pipeline_version"],
            "knowledge_version": None,
        },
        created_at=now,
    )


def _aura_request_context(session, record, measurement_evidence):
    result = record.payload.get("result") or {}
    context = [
        {
            "id": measurement_evidence.evidence_id,
            "source": "flame/image_measurement",
            "text": json.dumps(
                {
                    "analysis_id": record.analysis_id,
                    "evidence_id": measurement_evidence.evidence_id,
                    "image_sha256": record.image_sha256,
                    "pipeline_version": (record.payload.get("pipeline") or {}).get(
                        "pipeline_version"
                    ),
                    "detection": (result.get("detection") or {}).get("status"),
                    "measurements": _measurement_summary(result.get("measurements") or {}),
                    "quality_flags": result.get("quality_flags") or {},
                },
                separators=(",", ":"),
                allow_nan=False,
            ),
        }
    ]
    evidence_ids = {measurement_evidence.evidence_id}
    if record.experiment_id is None:
        return {"context": context, "evidence_ids": evidence_ids}

    conditions = (
        session.query(ExperimentCondition)
        .filter(ExperimentCondition.experiment_id == record.experiment_id)
        .limit(15)
        .all()
    )
    condition_ids = {condition.evidence_id for condition in conditions}
    evidence = (
        session.query(EvidenceRecord)
        .filter(EvidenceRecord.evidence_id.in_(condition_ids))
        .all()
        if condition_ids
        else []
    )
    evidence_by_id = {item.evidence_id: item for item in evidence}
    for condition in conditions:
        source_evidence = evidence_by_id.get(condition.evidence_id)
        if source_evidence is None:
            continue
        context.append(
            {
                "id": source_evidence.evidence_id,
                "source": "flame/source_evidence",
                "text": source_evidence.excerpt
                or f"{condition.variable}: "
                + str(
                    condition.value_numeric
                    if condition.value_numeric is not None
                    else condition.value_text
                ),
            }
        )
        context[-1]["text"] = context[-1]["text"][:2000]
        evidence_ids.add(source_evidence.evidence_id)
    return {"context": context, "evidence_ids": evidence_ids}


def _measurement_summary(measurements):
    summary = {}
    for group_name, group in measurements.items():
        if not isinstance(group, dict):
            continue
        values = {}
        for name, measurement in group.items():
            if not isinstance(measurement, dict):
                if name in {"color_space", "physical_interpretation"} and isinstance(
                    measurement, str
                ):
                    values[name] = measurement
                continue
            if "value" in measurement:
                values[name] = {
                    key: measurement.get(key)
                    for key in ("value", "unit", "classification")
                }
            elif "x" in measurement and "y" in measurement:
                values[name] = {
                    key: measurement.get(key)
                    for key in ("x", "y", "unit", "classification")
                }
        summary[group_name] = values
    return summary


def _store_interpretation(analysis_id, interpretation, *, warning):
    session = SessionLocal()
    record = session.get(AnalysisRecord, analysis_id)
    if record is None or record.status != "completed":
        session.close()
        return
    payload = dict(record.payload)
    payload["interpretation"] = interpretation
    if warning and not any(
        item.get("code") == "INTERPRETATION_UNAVAILABLE"
        for item in payload.get("warnings", [])
    ):
        payload.setdefault("warnings", []).append(
            {
                "code": "INTERPRETATION_UNAVAILABLE",
                "severity": "info",
                "message": "AURA interpretation was unavailable or included rejected statements.",
            }
        )
    record.payload = payload
    record.updated_at = _now()
    try:
        session.commit()
    finally:
        session.close()


def _run_aura_interpretation(analysis_id, context, evidence_ids):
    """Optional interpretation through the router (AURA, or a local model when AURA is absent or blocked)."""
    try:
        interpreted = interpret_analysis(
            ai_runtime.get_router(settings),
            analysis_id=analysis_id,
            context=context,
            allowed_evidence_ids=evidence_ids,
        )
    except (NoCompatibleProvider, ProviderError) as exc:
        logger.warning(
            "analysis_id=%s interpretation_unavailable status=%s",
            analysis_id,
            exc.status_code,
        )
        _store_interpretation(
            analysis_id,
            {
                "status": "unavailable",
                "provider": None,
                "model": None,
                "statements": [],
                "rejected_statement_count": 0,
                "generated_at": None,
            },
            warning=True,
        )
        return

    provider = interpreted["provider"]
    origin = "aura_interpretation" if provider == "aura" else "model_interpretation"
    _store_interpretation(
        analysis_id,
        {
            "status": "completed",
            "provider": provider,
            "model": interpreted["model"],
            "statements": [
                {
                    "statement_id": stable_ulid(
                        f"aura-statement:{analysis_id}:{index}:{statement['text']}"
                    ),
                    **statement,
                    "origin": origin,
                    "measurement_refs": [],
                }
                for index, statement in enumerate(interpreted["statements"])
            ],
            "rejected_statement_count": interpreted["rejected_statement_count"],
            "generated_at": interpreted["generated_at"],
            "execution": interpreted["execution"],
        },
        warning=interpreted["rejected_statement_count"] > 0,
    )


def _measured(value, unit, method, classification="measured"):
    return {"value": value, "unit": unit, "classification": classification, "method": method, "uncertainty": None}


def _adapt_result(legacy, input_data, work):
    import cv2

    detection = legacy["detection"]
    geometry = legacy["measurements"].get("geometry") or {}
    appearance = legacy["measurements"].get("appearance") or {}  # noqa: F841
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