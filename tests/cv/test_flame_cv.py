import json
import math
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from cv.flame_cv import (AnalysisCache, AnalysisResult, CVConfig, DecodeError, FileMissingError, ImageTooSmallError,
                      IntakeManifest, UnsupportedMediaError, analyze_image, analyze_image_safe, dedupe_legacy_manifest,
                      compute_auto_blur_kernel, compute_auto_target_size, export_schemas,
                      flame_analysis_api_adapter, ingest_image, make_synthetic_flame,
                      run_cv_evaluation, segmentation_metrics, split_for_group, validate_image)


@pytest.fixture
def dirs(tmp_path):
    return tmp_path / "cv", tmp_path / "masks"


def req(path, **kw):
    return {"requestId": "r1", "imageId": Path(path).stem, "imagePath": str(path), **kw}


def circle(tmp_path, name="c.jpg", **kw):
    p = tmp_path / name
    make_synthetic_flame(p, **kw)
    return p


# ---- #1 letterbox: geometry must not be distorted ----------------------------------------
def test_letterbox_keeps_geometry(tmp_path, dirs):
    p = circle(tmp_path, blobs=[(1500, 1000, 300, 300)])
    r = analyze_image(req(p), *dirs)
    g = r["measurements"]["geometry"]
    assert r["detection"]["status"] == "PRESENT"
    assert 0.95 <= g["aspectRatio"] <= 1.05
    assert g["circularity"] > 0.9
    assert abs(g["pixelArea"] - math.pi * 300 ** 2) / (math.pi * 300 ** 2) < 0.06
    assert abs(g["centroid"]["x"] - 1500) < 4 and abs(g["centroid"]["y"] - 1000) < 4
    bb = r["detection"]["boundingBox"]
    assert abs(bb["xmin"] - 1200) < 12 and abs(bb["ymax"] - 1300) < 12


def test_auto_adaptive_preprocessing_defaults():
    assert compute_auto_target_size(400, 300) == 400
    assert compute_auto_target_size(3008, 2000) == 512
    assert compute_auto_blur_kernel(400, 300) == 3
    assert compute_auto_blur_kernel(1000, 1000) == 11


def test_small_image_uses_adaptive_target_and_blur(tmp_path, dirs):
    image = tmp_path / "small.png"
    make_synthetic_flame(image, size=(400, 300), blobs=[(200, 150, 50, 50)])
    result = analyze_image(req(image), *dirs)
    preprocessing = result["preprocessing"]
    assert preprocessing["targetSize"] == 400
    assert "3x3 Gaussian" in preprocessing["denoising"]


# ---- #2 detection is computed, not hard-coded --------------------------------------------
def test_absent_on_dark_image(tmp_path, dirs):
    p = circle(tmp_path, "dark.jpg", blobs=[])
    r = analyze_image(req(p), *dirs)
    assert r["detection"]["status"] == "ABSENT"
    assert r["measurements"]["geometry"] is None
    assert r["segmentation"]["maskUri"] is None
    assert any("No flame-like" in w for w in r["scientificInterpretation"]["warnings"])


def test_confidence_not_constant(tmp_path, dirs):
    a = analyze_image(req(circle(tmp_path, "a.jpg", blobs=[(1500, 1000, 300, 300)])), *dirs)
    b = analyze_image(req(circle(tmp_path, "b.jpg", blobs=[(1500, 1000, 40, 40)], soften=25)), *dirs)
    assert a["detection"]["confidence"] != 0.96
    assert a["confidenceAndQualityFlags"]["segmenterConfidence"] != b["confidenceAndQualityFlags"]["segmenterConfidence"] \
        or a["detection"]["confidence"] != b["detection"]["confidence"]


# ---- #3/#4 flags computed ----------------------------------------------------------------
def test_multiple_flames_flag(tmp_path, dirs):
    p = circle(tmp_path, blobs=[(800, 1000, 250, 250), (2200, 1000, 250, 250)])
    f = analyze_image(req(p), *dirs)["confidenceAndQualityFlags"]["qualityFlags"]
    assert f["multipleFlames"] is True and f["occlusion"] is False


def test_edge_touch_sets_occlusion(tmp_path, dirs):
    p = circle(tmp_path, blobs=[(10, 1000, 300, 300)])
    assert analyze_image(req(p), *dirs)["confidenceAndQualityFlags"]["qualityFlags"]["occlusion"] is True


def test_blur_flag_on_soft_edges(tmp_path, dirs):
    sharp = analyze_image(req(circle(tmp_path, "s.jpg", soften=2)), *dirs)
    soft = analyze_image(req(circle(tmp_path, "f.jpg", soften=60)), *dirs)
    gs = sharp["confidenceAndQualityFlags"]["qualityMetrics"]["boundaryGradient"]
    gf = soft["confidenceAndQualityFlags"]["qualityMetrics"]["boundaryGradient"]
    assert gs > gf
    assert sharp["confidenceAndQualityFlags"]["qualityFlags"]["blur"] is False


def test_saturation_is_real_saturation(tmp_path, dirs):
    r = analyze_image(req(circle(tmp_path)), *dirs)
    a = r["measurements"]["appearance"]
    assert "saturationScore" not in a
    assert 0.4 < a["meanSaturationInMask"] < 0.7  # warm colour (255,200,120) => S ~0.53


# ---- #5 artifacts / bbox / checksum / options --------------------------------------------
def test_artifacts_checksums_and_overlay(tmp_path, dirs):
    r = analyze_image(req(circle(tmp_path)), *dirs)
    seg = r["segmentation"]
    assert seg["maskStatus"] == "SUCCESS" and seg["maskChecksum"].startswith("sha256:")
    assert Path(seg["maskUri"]).exists() and Path(seg["overlayArtifactUri"]).exists()
    assert "\\" not in seg["maskUri"] and "\\" not in r["provenance"]["inputUri"]


def test_options_are_honoured(tmp_path, dirs):
    p = circle(tmp_path)
    r = analyze_image(req(p, options={"generateMaskArtifact": False, "extractGeometry": False}), *dirs)
    assert r["segmentation"]["maskUri"] is None and r["segmentation"]["maskStatus"] == "NOT_WRITTEN"
    assert r["measurements"]["geometry"] is None and r["measurements"]["appearance"] is not None
    r2 = analyze_image(req(p, options={"runSegmentation": False}), *dirs)
    assert r2["detection"]["status"] == "UNCERTAIN" and r2["segmentation"]["maskStatus"] == "NOT_REQUESTED"


# ---- #6 honest naming / reproducible ids -------------------------------------------------
def test_deterministic_and_reproducible(tmp_path, dirs):
    p = circle(tmp_path)
    a, b = analyze_image(req(p), *dirs), analyze_image(req(p), *dirs)
    for r in (a, b):
        r["provenance"].pop("createdAt")
    assert a == b and a["analysisId"].startswith("an_")
    assert a["pipelineVersion"] == "cv-opencv-v1.2.0-auto" and "pytorch" not in a["pipelineVersion"]
    assert a["provenance"]["configDigest"] and a["provenance"]["libraries"]["opencv"]


# ---- #7 cache ----------------------------------------------------------------------------
def test_cache_hit_miss_and_invalidation(tmp_path, dirs):
    p = circle(tmp_path)
    cache = AnalysisCache(tmp_path / "cache.jsonl")
    r1 = analyze_image(req(p), *dirs, cache=cache)
    r2 = analyze_image(req(p, requestId="other"), *dirs, cache=cache)
    assert r1["cache"]["hit"] is False and r2["cache"]["hit"] is True
    assert r2["request"]["requestId"] == "other" and r1["analysisId"] == r2["analysisId"]
    # changing a threshold must NOT return the stale result
    r3 = analyze_image(req(p), *dirs, cache=cache, cfg=replace(CVConfig(), min_threshold=80))
    assert r3["cache"]["hit"] is False and r3["cache"]["key"] != r1["cache"]["key"]
    # explicit invalidation of entries made with other versions
    current_config = replace(CVConfig(), target_size=compute_auto_target_size(3008, 2000))
    removed = cache.invalidate_stale({"pipelineVersion": "cv-opencv-v1.2.0-auto",
                                      "preprocessVersion": "letterbox-lanczos-auto-v1",
                                      "segmenterVersion": "1.2.0", "configDigest": current_config.digest()})
    assert removed == 1


def test_cache_miss_when_artifact_deleted(tmp_path, dirs):
    p = circle(tmp_path)
    cache = AnalysisCache(tmp_path / "cache.jsonl")
    r1 = analyze_image(req(p), *dirs, cache=cache)
    Path(r1["segmentation"]["maskUri"]).unlink()
    assert analyze_image(req(p), *dirs, cache=cache)["cache"]["hit"] is False


# ---- #8 evaluation -----------------------------------------------------------------------
def test_segmentation_metrics_basic():
    a = np.zeros((10, 10), np.uint8)
    a[:5] = 255
    assert segmentation_metrics(a, a)["iou"] == 1.0
    b = np.zeros_like(a)
    b[:, :5] = 255
    m = segmentation_metrics(a, b)
    assert m["iou"] == pytest.approx(25 / 75, abs=1e-3)


def test_evaluation_with_and_without_gt(tmp_path, dirs):
    imgs, gts = tmp_path / "imgs", tmp_path / "gt"
    imgs.mkdir(), gts.mkdir()
    make_synthetic_flame(imgs / "a.jpg", blobs=[(1500, 1000, 300, 250)], gt_path=gts / "a.png")
    make_synthetic_flame(imgs / "b.jpg", blobs=[(900, 800, 200, 200)], gt_path=gts / "b.png", seed=3)
    rep = run_cv_evaluation(imgs, *dirs, gt_dir=gts, acceptance_iou=0.8)
    assert rep["segmentation"]["status"] == "EVALUATED" and rep["segmentation"]["meanIoU"] > 0.9
    assert rep["acceptance"]["verdict"] == "PASS" and rep["dataset"]["nWithGroundTruth"] == 2
    rep2 = run_cv_evaluation(imgs, *dirs, gt_dir=None)
    assert rep2["segmentation"]["status"] == "NOT_EVALUATED" and rep2["acceptance"]["verdict"] == "NOT_EVALUATED"


# ---- intake / manifest -------------------------------------------------------------------
def test_intake_errors(tmp_path):
    cfg = CVConfig()
    with pytest.raises(FileMissingError):
        validate_image(tmp_path / "nope.jpg", cfg)
    Image.new("RGB", (20, 20)).save(tmp_path / "tiny.png")
    with pytest.raises(ImageTooSmallError):
        validate_image(tmp_path / "tiny.png", cfg)
    Image.new("RGB", (100, 100)).save(tmp_path / "x.bmp")
    with pytest.raises(UnsupportedMediaError):
        validate_image(tmp_path / "x.bmp", cfg)
    (tmp_path / "fake.jpg").write_bytes(b"not an image")
    with pytest.raises(DecodeError):
        validate_image(tmp_path / "fake.jpg", cfg)


def test_manifest_is_idempotent_and_keeps_curation(tmp_path, dirs):
    p = circle(tmp_path)
    m = tmp_path / "manifest.jsonl"
    ingest_image(p, dirs[0], m, license="NASA-PSI", group_id="FF-PSI-107/SPICE")
    ingest_image(p, dirs[0], m)  # re-run, no curated fields
    ingest_image(p, dirs[0], m)
    recs = IntakeManifest(m).records()
    assert len(recs) == 1 and recs[0]["license"] == "NASA-PSI" and recs[0]["split"] in ("dev", "validation", "holdout")


def test_dedupe_legacy_manifest(tmp_path):
    m = tmp_path / "manifest.jsonl"
    rows = [{"imageId": "a", "checksumSha256": "sha256:1", "status": "VALIDATED_AND_PREPROCESSED"},
            {"imageId": "a", "checksumSha256": "sha256:1", "validationStatus": "PASSED"},
            {"imageId": "b", "checksumSha256": "sha256:2", "validationStatus": "PASSED"}] * 3
    m.write_text("\n".join(json.dumps(r) for r in rows))
    stats = dedupe_legacy_manifest(m)
    assert stats == {"before": 9, "after": 2} and m.with_suffix(".jsonl.bak").exists()


def test_split_is_deterministic_by_group():
    assert split_for_group("FF-PSI-107") == split_for_group("FF-PSI-107")


# ---- contract / errors / physical estimates ----------------------------------------------
def test_contract_roundtrip_and_schema_export(tmp_path, dirs):
    r = analyze_image(req(circle(tmp_path)), *dirs)
    assert AnalysisResult.model_validate(r).analysisId == r["analysisId"]
    with pytest.raises(Exception):
        AnalysisResult.model_validate({**r, "surprise": 1})
    paths = export_schemas(tmp_path / "contracts")
    for p in paths:
        assert json.loads(Path(p).read_text())["$schema"].endswith("2020-12/schema")
    assert "x-intakePolicy" in json.loads(Path(paths[1]).read_text())


def test_error_envelope(tmp_path, dirs):
    r = flame_analysis_api_adapter({"requestId": "r9", "imagePath": str(tmp_path / "missing.jpg")}, *dirs)
    assert r["status"] == "ERROR" and r["error"]["code"] == "FILE_NOT_FOUND" and r["error"]["httpStatus"] == 404
    r = analyze_image_safe({"requestId": "r8"}, *dirs)
    assert r["error"]["code"] == "INVALID_REQUEST"


def test_physical_estimates_only_with_scale(tmp_path, dirs):
    p = circle(tmp_path)
    r0 = analyze_image(req(p), *dirs)
    assert r0["measurements"]["physicalEstimates"] is None
    assert r0["confidenceAndQualityFlags"]["qualityFlags"]["scaleAbsent"] is True
    r1 = analyze_image(req(p, metadata={"mmPerPixel": 0.05}), *dirs)
    pe = r1["measurements"]["physicalEstimates"]
    assert pe["classification"] == "ESTIMATED"
    assert pe["areaMm2"] == pytest.approx(r1["measurements"]["geometry"]["pixelArea"] * 0.05 ** 2, rel=1e-3)
    assert r1["scientificInterpretation"]["calibrationState"] == "SCALE_ONLY"
    assert r1["confidenceAndQualityFlags"]["qualityFlags"]["calibrationAbsent"] is True  # radiometric still absent
    assert any("Temperature" in w for w in r1["scientificInterpretation"]["warnings"])
    assert r1["analysisId"] != r0["analysisId"]


def test_naive_resize_would_have_distorted(tmp_path):
    """Regression guard documenting the original bug: squashing 3008x2000 -> 512x512."""
    p = circle(tmp_path)
    naive = cv2.resize(cv2.imread(str(p), 0), (512, 512))
    _, th = cv2.threshold(naive, 50, 255, cv2.THRESH_BINARY)
    x, y, w, h = cv2.boundingRect(max(cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0],
                                      key=cv2.contourArea))
    assert w / h < 0.75  # a perfect circle becomes a tall ellipse

def test_artifact_paths_are_normalized_and_resolvable(tmp_path, dirs):
    p = circle(tmp_path)
    r = analyze_image(req(p), *dirs)
    
    mask_uri = r["segmentation"].get("maskUri")
    if mask_uri:
        assert "\\" not in mask_uri
        assert Path(mask_uri).exists()
        
    derived_uri = r["preprocessing"].get("derivedUri")
    if derived_uri:
        assert "\\" not in derived_uri
        assert Path(derived_uri).exists()
