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
    # Like the specks in empty BASS-II frames: 0.03% of the frame, about 60 gray levels above the background.
    img = np.full((480, 720, 3), 6, np.uint8)
    img[0:5, 600:620] = 68
    path = tmp_path / "speck.png"
    Image.fromarray(img).save(path)
    r = run(path, dirs)
    assert r["detection"]["status"] == "ABSENT"
    assert r["measurements"]["geometry"] is None
    assert any("speck" in w.lower() for w in r["scientificInterpretation"]["warnings"])


def test_small_bright_flame_is_present(tmp_path, dirs):
    # A real flame can be smaller than 0.05% of the frame (a distant or dying flame). With high contrast it is
    # a flame, not a speck: the 0.05% minimum of v1.3.0 missed these (CV evaluation, holdout T23).
    img = np.full((480, 720, 3), 6, np.uint8)
    cv2.ellipse(img, (500, 300), (6, 4), 0, 0, 360, (150, 120, 220), -1)   # ~0.03% of the frame
    path = tmp_path / "small_flame.png"
    Image.fromarray(img).save(path)
    r = run(path, dirs)
    assert r["detection"]["status"] == "PRESENT"
    area = r["measurements"]["geometry"]["pixelArea"] / (720 * 480)
    assert area < 0.0005


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


# ---- static lit scenery (cabin views, lit hardware) was reported as a flame --------------------
def test_bright_region_in_a_lit_scene_is_not_present(tmp_path, dirs):
    # A lit scene (median gray ~70, like a cabin view) with a bright region: brightness cannot tell lit
    # scenery from a flame, so the answer is UNCERTAIN, never PRESENT.
    rng = np.random.default_rng(2)
    img = np.clip(rng.normal(70, 12, (480, 720, 3)), 0, 255).astype(np.uint8)
    cv2.rectangle(img, (100, 300), (500, 470), (235, 235, 245), -1)   # a bright floor panel
    path = tmp_path / "lit.png"
    Image.fromarray(img).save(path)
    r = run(path, dirs)
    assert r["detection"]["status"] == "UNCERTAIN"
    assert any("lit scene" in w.lower() for w in r["scientificInterpretation"]["warnings"])


def test_flame_in_a_dark_scene_is_still_present(tmp_path, dirs):
    p = tmp_path / "c.png"
    make_synthetic_flame(p, size=(800, 600), blobs=[(400, 300, 120, 120)])
    r = run(p, dirs)
    assert r["detection"]["status"] == "PRESENT"
    assert not any("lit scene" in w.lower() for w in r["scientificInterpretation"]["warnings"])


def test_lit_flex_hardware_frame_is_not_present(tmp_path, dirs):
    # FLEX X168M03D_00000: the chamber lit, needle and wall visible, no flame (dev split of cv_gold_v1).
    paths = _samples("FF-PSI-69/X168M03D/X168M03D_00000.png")
    assert run(paths[0], dirs)["detection"]["status"] != "PRESENT"


def test_cabin_view_video_has_no_present_frames(tmp_path):
    # BASS-II TEST_T25 2nd view: a lit glovebox, no flame in the camera's own view (dev split of cv_gold_v1).
    from cv.video_analysis import analyze_video
    from cv.video_ingestion import VideoConfig
    video = next((SAMPLES / "FF-PSI-25" / "videos").glob("*T25_2ND_VIEW*.mp4"), None)
    if video is None:
        pytest.skip("TEST_T25 2nd view not installed")
    result = analyze_video(video, tmp_path, video_cfg=VideoConfig(sample_every=500))
    assert [f["frameIndex"] for f in result["frameMeasurements"] if f["detectionStatus"] == "PRESENT"] == []


# ---- per-camera exclusion zones (camera profiles) -----------------------------------------------
def run_profile(path, dirs, profile):
    return analyze_image({"imagePath": str(path), "imageId": Path(path).stem, "metadata": {"cameraProfile": profile}},
                         *dirs)


def test_exclusion_zone_hides_a_bright_region_and_is_recorded(tmp_path, dirs):
    from cv.flame_cv import CVConfig as _C
    img = np.zeros((480, 640, 3), np.uint8)
    cv2.ellipse(img, (320, 440), (60, 15), 0, 180, 360, (60, 60, 230), 6)   # an arc at the bottom centre
    path = tmp_path / "arc.png"
    Image.fromarray(img).save(path)
    assert run(path, dirs)["detection"]["status"] == "PRESENT"
    r = run(path, dirs, cfg=_C(exclude_regions=((0.30, 0.82, 0.70, 1.00),)))
    assert r["detection"]["status"] == "ABSENT"
    assert r["preprocessing"]["excludedRegions"] == [[0.30, 0.82, 0.70, 1.00]]


def test_unknown_camera_profile_is_rejected(tmp_path, dirs):
    p = tmp_path / "c.png"
    make_synthetic_flame(p, size=(800, 600), blobs=[(400, 300, 120, 120)])
    from cv.flame_cv import CVError
    with pytest.raises(CVError) as err:
        run_profile(p, dirs, "no-such-camera")
    assert err.value.code == "INVALID_REQUEST"


def test_no_profile_changes_nothing(tmp_path, dirs):
    p = tmp_path / "c.png"
    make_synthetic_flame(p, size=(800, 600), blobs=[(400, 300, 120, 120)])
    r = run(p, dirs)
    assert r["preprocessing"]["excludedRegions"] == [] and r["preprocessing"]["cameraProfile"] is None


ARC_FRAMES = ["176F001D/176F001D_01319", "195F002D/195F002D_00000", "195F002D/195F002D_01061",
              "H08M101D/H08M101D_00642", "H08M101D/H08M101D_01284"]


@pytest.mark.parametrize("name", ARC_FRAMES)
def test_flex_profile_excludes_the_hardware_arc(tmp_path, dirs, name):
    # The five FLEX colour frames whose false positive was a static glowing arc (dev split of cv_gold_v1). With the
    # profile the arc is never the detection. (Three of them then detect other static hardware: see the next test.)
    path = _samples(f"FF-PSI-69/{name}.png")[0]
    before = run(path, dirs)
    assert before["detection"]["status"] == "PRESENT" and before["detection"]["boundingBox"]["ymin"] > 0.82 * 480
    r = run_profile(path, dirs, "flex-colour")
    assert r["preprocessing"]["cameraProfile"] == "flex-colour"
    if r["detection"]["status"] == "PRESENT":
        assert r["detection"]["boundingBox"]["ymax"] <= 0.82 * 480, "the excluded arc was detected"


@pytest.mark.parametrize("name", ["176F001D/176F001D_01319", "195F002D/195F002D_01061"])
def test_flex_profile_fixes_frames_where_the_arc_was_the_only_hardware(tmp_path, dirs, name):
    path = _samples(f"FF-PSI-69/{name}.png")[0]
    assert run_profile(path, dirs, "flex-colour")["detection"]["status"] != "PRESENT"


def test_real_flex_flame_survives_the_flex_profile(tmp_path, dirs):
    # 195F002D_00530: the one FLEX frame labelled as a flame in the dev split (a large burning droplet; draft label).
    path = _samples("FF-PSI-69/195F002D/195F002D_00530.png")[0]
    before, after = run(path, dirs), run_profile(path, dirs, "flex-colour")
    assert before["detection"]["status"] == after["detection"]["status"] == "PRESENT"
    assert before["detection"]["boundingBox"] == after["detection"]["boundingBox"]


@pytest.mark.parametrize("name", ["176F001D/176F001D_00000", "X168M03D/X168M03D_00000", "X177H10D/X177H10D_00000"])
def test_excluded_region_does_not_count_as_dark_scene(tmp_path, dirs, name):
    # Lit FLEX hardware frames are UNCERTAIN by the lit-scene rule. With the camera profile they must stay so: the
    # excluded band is not part of the scene, so its pixels must not pull the scene's brightness statistics down
    # (blacking them out and counting them flipped these frames to PRESENT).
    path = _samples(f"FF-PSI-69/{name}.png")[0]
    assert run(path, dirs)["detection"]["status"] == "UNCERTAIN"
    assert run_profile(path, dirs, "flex-colour")["detection"]["status"] != "PRESENT"


# ------------------------------------------------- v1.7.0: a FLEX region smaller than a droplet is not PRESENT
def _point_light(path, radius=5):
    img = np.zeros((480, 640, 3), np.uint8)
    cv2.circle(img, (320, 250), radius, (255, 235, 245), -1)   # a small saturated point, like a droplet glint
    cv2.imwrite(str(path), img)
    return path


def test_small_region_is_uncertain_with_the_flex_profile_and_present_without(tmp_path, dirs):
    path = _point_light(tmp_path / "glint.png")
    plain = run(path, dirs)
    assert plain["detection"]["status"] == "PRESENT"     # bright, contrasting and stable: a flame by brightness
    flex = run_profile(path, dirs, "flex-colour")
    assert flex["detection"]["status"] == "UNCERTAIN"
    assert any("smaller than" in w for w in flex["scientificInterpretation"]["warnings"])
    assert flex["preprocessing"]["minPresentAreaFraction"] == 0.001
    assert plain["preprocessing"]["minPresentAreaFraction"] is None


# Droplet glints after a methanol flame went out (H08M101: extinction at 0.3 s) and a hardware glint at the top edge
# of 195F002D_00000: the three FLEX colour false positives left at v1.6.0.
GLINT_FRAMES = ["H08M101D/H08M101D_00642", "H08M101D/H08M101D_01284", "195F002D/195F002D_00000"]


@pytest.mark.parametrize("name", GLINT_FRAMES)
def test_flex_glints_are_not_present(tmp_path, dirs, name):
    path = _samples(f"FF-PSI-69/{name.split('/')[0]}/{name.split('/')[1]}.png")[0]
    assert run_profile(path, dirs, "flex-colour")["detection"]["status"] == "UNCERTAIN"


def test_a_large_region_is_unaffected_by_the_floor(tmp_path, dirs):
    path = _point_light(tmp_path / "big.png", radius=40)
    assert run_profile(path, dirs, "flex-colour")["detection"]["status"] == "PRESENT"


# ------------------------------------------------- v1.8.0: a straight-edged region is not PRESENT
def _shape_image(path, kind, size):
    img = np.zeros((512, 512, 3), np.uint8)
    if kind == "rectangle":
        cv2.rectangle(img, (256 - size, 256 - size // 2), (256 + size, 256 + size // 2), (230, 230, 230), -1)
    else:
        cv2.ellipse(img, (256, 256), (size, size // 2), 20, 0, 360, (230, 230, 230), -1)
    cv2.imwrite(str(path), img)
    return path


def test_a_bright_rectangle_is_uncertain_and_an_ellipse_of_the_same_size_is_present(tmp_path, dirs):
    rect = run(_shape_image(tmp_path / "rect.png", "rectangle", 80), dirs)
    assert rect["detection"]["status"] == "UNCERTAIN"
    assert any("straight-edged" in w for w in rect["scientificInterpretation"]["warnings"])
    assert run(_shape_image(tmp_path / "ellipse.png", "ellipse", 80), dirs)["detection"]["status"] == "PRESENT"


def test_a_tiny_square_is_not_judged_by_its_shape(tmp_path, dirs):
    # A few pixels always look square; the shape rule only applies from 20 px across.
    img = np.zeros((512, 512, 3), np.uint8)
    cv2.rectangle(img, (250, 250), (256, 256), (255, 255, 255), -1)
    cv2.imwrite(str(tmp_path / "dot.png"), img)
    r = run(tmp_path / "dot.png", dirs)
    assert not any("straight-edged" in w for w in r["scientificInterpretation"]["warnings"])


# DECLIC DSI (directional solidification, not combustion): a backlit sample cell, bright with straight edges.
DSI_CELL_FRAMES = ["DSI_SEQ2_ACTIVITE04_HR1_1018759522_1", "DSI_SEQ2_ACTIVITE04_HR1_1022430520_1"]


@pytest.mark.parametrize("name", DSI_CELL_FRAMES)
def test_dsi_backlit_cell_is_not_present(tmp_path, dirs, name):
    path = _samples(f"FF-PSI-DSI/ACTIVITE04_HR1/{name}.png")[0]
    assert run(path, dirs)["detection"]["status"] == "UNCERTAIN"


@pytest.mark.parametrize("name", ["FF-PSI-107/SPICE_GMT045_2009_jpegs/ISS018E030372.jpg",
                                  "FF-PSI-107/SPICE_GMT045_2009_jpegs/ISS018E030351.jpg"])
def test_the_boxiest_real_flames_stay_present(tmp_path, dirs, name):
    # The two real flames with the highest rectangularity among the committed samples (0.844 and 0.829).
    assert run(_samples(name)[0], dirs)["detection"]["status"] == "PRESENT"
