"""tests/cv/test_detection_scoring.py - detection decisions that the CV audit found wrong (finding CV-2).

Each test names the failure it guards against. Real-data tests use committed NASA samples and skip when
they are not installed.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from cv.flame_cv import CVConfig, analyze_image, make_synthetic_flame

REPO = Path(__file__).resolve().parents[2]
SAMPLES = REPO / "datasets" / "samples" / "cv"


@pytest.fixture
def dirs(tmp_path):
    return tmp_path / "cv", tmp_path / "masks"


def run(path, dirs, cfg=None):
    return analyze_image({"imagePath": str(path), "imageId": Path(path).stem}, *dirs, cfg=cfg)


def save16(path: Path, arr: np.ndarray) -> Path:
    Image.fromarray(arr.astype(np.uint16)).save(path)
    assert Image.open(path).mode.startswith("I;16")
    return path


def dark_frame16(h=512, w=512, seed=0) -> np.ndarray:
    """A 16-bit sensor dark frame: column readout banding plus noise, no flame (like FLEX C021H03C)."""
    rng = np.random.default_rng(seed)
    bands = np.repeat(rng.integers(2400, 3200, size=w // 64), 64)[None, :]
    return np.clip(bands + rng.normal(0, 60, (h, w)), 0, 65535)


# ---- 16-bit input was clipped to a white frame by convert("RGB") ---------------------------
def test_16bit_dark_frame_is_not_a_flame(tmp_path, dirs):
    r = run(save16(tmp_path / "dark16.png", dark_frame16()), dirs)
    assert r["detection"]["status"] != "PRESENT"
    assert r["preprocessing"]["sourceBitDepth"] == 16
    assert r["confidenceAndQualityFlags"]["qualityFlags"]["saturationClipping"] is False


def test_16bit_flame_is_still_detected(tmp_path, dirs):
    img = dark_frame16()
    cv2.ellipse(img, (256, 256), (60, 80), 0, 0, 360, 60000, -1)
    r = run(save16(tmp_path / "flame16.png", img), dirs)
    assert r["detection"]["status"] == "PRESENT"
    bb = r["detection"]["boundingBox"]
    assert abs((bb["xmin"] + bb["xmax"]) / 2 - 256) < 4 and abs((bb["ymin"] + bb["ymax"]) / 2 - 256) < 4


def test_declared_bit_depth_scales_a_12bit_sensor(tmp_path, dirs):
    img = np.full((512, 512), 300.0)
    cv2.ellipse(img, (256, 256), (60, 80), 0, 0, 360, 4000, -1)
    path = save16(tmp_path / "flame12.png", img)
    assert run(path, dirs)["detection"]["status"] != "PRESENT", "full 16-bit scaling leaves a 12-bit flame too dim"
    r = run(path, dirs, cfg=CVConfig(input_bit_depth=12))
    assert r["detection"]["status"] == "PRESENT" and r["preprocessing"]["sourceBitDepth"] == 16


# ---- a region that fills the frame had contrast 255 (no background, outside mean defaulted to 0) --
def test_region_filling_the_frame_is_not_present(tmp_path, dirs):
    path = tmp_path / "white.png"
    Image.fromarray(np.full((480, 640, 3), 240, np.uint8)).save(path)
    r = run(path, dirs)
    assert r["detection"]["status"] != "PRESENT"
    assert r["confidenceAndQualityFlags"]["qualityMetrics"]["flameContrast"] is None
    assert any("background" in w.lower() for w in r["scientificInterpretation"]["warnings"])


# ---- PRESENT with segmentation stability 0 --------------------------------------------------
def test_unstable_segmentation_is_not_present(tmp_path, dirs):
    p = tmp_path / "c.png"
    make_synthetic_flame(p, size=(800, 600), blobs=[(400, 300, 120, 120)])
    assert run(p, dirs)["detection"]["status"] == "PRESENT"
    r = run(p, dirs, cfg=replace(CVConfig(), min_present_stability=1.01))  # no mask can be this stable
    assert r["detection"]["status"] == "UNCERTAIN"
    assert any("stab" in w.lower() for w in r["scientificInterpretation"]["warnings"])


# ---- tiny specks in an empty dark frame were UNCERTAIN "flames" ------------------------------
def test_tiny_speck_is_absent(tmp_path, dirs):
    img = np.zeros((480, 720, 3), np.uint8)
    img[0:5, 600:620] = 255  # a 100-pixel scan-line speck at the frame edge (0.03% of the frame, like TEST_P12)
    path = tmp_path / "speck.png"
    Image.fromarray(img).save(path)
    r = run(path, dirs)
    assert r["detection"]["status"] == "ABSENT"
    assert r["measurements"]["geometry"] is None


def test_smallest_real_flame_size_is_kept(tmp_path, dirs):
    # 0.094% of the frame: the BASS-II TEST_B1 ignition kernel, the smallest real flame in the samples.
    p = tmp_path / "kernel.png"
    r_px = int(round(np.sqrt(0.00094 * 720 * 480 / np.pi)))
    make_synthetic_flame(p, size=(720, 480), blobs=[(360, 240, r_px, r_px)], soften=1.0)
    assert run(p, dirs)["detection"]["status"] == "PRESENT"


# ---- hard-coded ABSENT confidence (0.9) and classification always MEASURED -------------------
def test_absent_confidence_is_computed(tmp_path, dirs):
    black = tmp_path / "black.png"
    Image.fromarray(np.zeros((480, 640, 3), np.uint8)).save(black)
    hazy = tmp_path / "hazy.png"
    rng = np.random.default_rng(1)
    Image.fromarray(np.clip(rng.normal(40, 25, (480, 640, 3)), 0, 255).astype(np.uint8)).save(hazy)
    a, b = run(black, dirs), run(hazy, dirs)
    assert a["detection"]["status"] == b["detection"]["status"] == "ABSENT"
    assert a["detection"]["confidence"] > b["detection"]["confidence"], "more bright clutter, less sure it is absent"
    assert a["detection"]["confidence"] <= CVConfig().absent_confidence_cap


def test_classification_follows_what_was_measured(tmp_path, dirs):
    black = tmp_path / "black.png"
    Image.fromarray(np.zeros((480, 640, 3), np.uint8)).save(black)
    assert run(black, dirs)["scientificInterpretation"]["classification"] == "INFERRED"
    p = tmp_path / "c.png"
    make_synthetic_flame(p, size=(800, 600), blobs=[(400, 300, 120, 120)])
    assert run(p, dirs)["scientificInterpretation"]["classification"] == "MEASURED"


# ---- regression on committed NASA samples ---------------------------------------------------
def _samples(pattern):
    paths = sorted(SAMPLES.glob(pattern))
    if not paths:
        pytest.skip(f"samples {pattern} not installed")
    return paths


@pytest.mark.parametrize("sequence", ["C021H03C", "C024M06C", "H14H101C"])
def test_flex_16bit_dark_frames_are_not_flames(tmp_path, dirs, sequence):
    # These FLEX sequences are 16-bit sensor dark frames; before the fix every one was PRESENT at 0.8.
    for path in _samples(f"FF-PSI-69/{sequence}/*.png")[::7]:
        assert run(path, dirs)["detection"]["status"] != "PRESENT", path.name


def test_spice_flames_are_still_present(tmp_path, dirs):
    paths = _samples("FF-PSI-107/SPICE_GMT045_2009_jpegs/*.jpg")
    assert all(run(p, dirs)["detection"]["status"] == "PRESENT" for p in paths)
