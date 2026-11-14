"""tests/cv/test_video_pipeline.py - video ingestion, temporal analysis, resumable video analysis and contract validation."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import cv2
import numpy as np
import pytest
from jsonschema import Draft202012Validator

from cv import video_ingestion as vi
from cv.flame_cv import CVError, analyze_image_safe
from cv.temporal_analysis import NOT_ESTIMABLE, TemporalConfig, assign_tracks, flicker_frequency, summarize
from cv.video_analysis import analyze_video, analyze_video_safe, main as video_main
from cv.video_ingestion import VideoConfig

REPO = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO / "cv" / "contracts" / "video_analysis_result.schema.json").read_text(encoding="utf-8"))
SAMPLE_VIDEO = next((REPO / "datasets" / "samples" / "cv").rglob("*B1.mp4"), None)
RAW = VideoConfig(allowed_codecs=None)


def make_video(path, frames=20, fps=20.0, size=(320, 240)):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, size)
    assert writer.isOpened()
    for i in range(frames):
        img = np.zeros((size[1], size[0], 3), np.uint8)
        cv2.ellipse(img, (160, 120), (50 + i % 3, 60), 0, 0, 360, (80, 200, 255), -1)
        writer.write(cv2.GaussianBlur(img, (0, 0), 3))
    writer.release()
    return path


def validate(payload):
    Draft202012Validator(SCHEMA).validate(payload)


@pytest.fixture
def video(tmp_path):
    return make_video(tmp_path / "flame.avi")


# ---------------------------------------------------------------- ingestion
def test_probe_metadata_ids_and_lineage(video):
    rec = vi.probe_video(video, RAW)
    assert rec["frameCount"] == 20 and rec["resolution"] == [320, 240] and rec["fps"] == pytest.approx(20.0)
    assert rec["videoId"] == "vid_" + rec["checksum"].split(":")[1][:16]
    assert rec["timestamps"]["variableFrameRate"] is False
    ids = [f.frameId for f in vi.iter_frames(video, rec, RAW)]
    assert ids[0] == f"{rec['videoId']}_frame_000000" and ids[-1] == f"{rec['videoId']}_frame_000019"
    assert vi.frame_id_for(rec["videoId"], 7) == ids[7]


def test_sampling_and_timestamps(video):
    cfg = VideoConfig(allowed_codecs=None, sample_every=5)
    rec = vi.probe_video(video, cfg)
    frames = list(vi.iter_frames(video, rec, cfg))
    assert [f.frameIndex for f in frames] == [0, 5, 10, 15]
    assert [f.timestamp for f in frames] == pytest.approx([0.0, 0.25, 0.5, 0.75])
    capped = VideoConfig(allowed_codecs=None, max_frames=3)
    assert len(list(vi.iter_frames(video, vi.probe_video(video, capped), capped))) == 3


def test_source_is_not_modified(video):
    before = video.read_bytes()
    analyze_video(video, video.parent / "out", video_cfg=VideoConfig(allowed_codecs=None, sample_every=10))
    assert video.read_bytes() == before


@pytest.mark.parametrize("name,exc", [("clip.mkv", "UNSUPPORTED_MEDIA_TYPE"), ("missing.avi", "FILE_NOT_FOUND")])
def test_rejections(tmp_path, name, exc):
    (tmp_path / "clip.mkv").write_bytes(b"x")
    with pytest.raises(CVError) as err:
        vi.probe_video(tmp_path / name, RAW)
    assert err.value.code == exc


def test_default_codec_check_rejects_other_codecs(video):
    with pytest.raises(CVError) as err:
        vi.probe_video(video)
    assert err.value.code == "UNSUPPORTED_MEDIA_TYPE" and "codec" in err.value.message


def test_size_and_duration_limits(video):
    with pytest.raises(CVError) as err:
        vi.probe_video(video, VideoConfig(allowed_codecs=None, max_bytes=10))
    assert err.value.code == "FILE_TOO_LARGE"
    with pytest.raises(CVError) as err:
        vi.probe_video(video, VideoConfig(allowed_codecs=None, max_duration_s=0.5))
    assert err.value.code == "VIDEO_TOO_LONG"


def test_corrupt_video_is_a_controlled_error(tmp_path):
    bad = tmp_path / "bad.avi"
    bad.write_bytes(b"not a video" * 50)
    out = analyze_video_safe(bad, tmp_path / "out", video_cfg=RAW)
    assert out["status"] == "ERROR" and out["error"]["code"] == "DECODE_FAILED"


def test_variable_frame_rate_is_normalized(video, monkeypatch):
    # Frames 0-4 at 20 fps, then a 0.5 s stall before frames 5-9.
    stamps = [0.0, 0.05, 0.10, 0.15, 0.20, 0.70, 0.75, 0.80, 0.85, 0.90]
    monkeypatch.setattr(vi, "_scan_timestamps", lambda p: stamps)
    rec = vi.probe_video(video, VideoConfig(allowed_codecs=None, max_frames=None))
    assert rec["timestamps"]["variableFrameRate"] is True
    assert rec["fps"] == pytest.approx(10.0)  # average rate over the clip
    mapping = rec["_cfrMapping"]
    assert len(set(mapping)) < len(mapping)  # the stall repeats frame 4 on the uniform grid
    assert mapping == sorted(mapping) and mapping[0] == 0 and mapping[-1] == len(stamps) - 1
    frames = list(vi.iter_frames(video, rec, RAW))
    assert [f.frameIndex for f in frames] == list(range(rec["frameCount"]))
    assert [f.timestamp for f in frames] == pytest.approx([k / rec["fps"] for k in range(rec["frameCount"])])


# ---------------------------------------------------------------- temporal analysis
def frame(i, fps=30.0, status="PRESENT", area=1000.0, box=(0, 0, 10, 10), centroid=(5, 5), flags=None):
    return {"frameIndex": i, "timestamp": i / fps, "detectionStatus": status,
            "pixelArea": None if status != "PRESENT" else area,
            "centroid": {"x": centroid[0], "y": centroid[1]} if status == "PRESENT" else None,
            "boundingBox": dict(zip(("xmin", "ymin", "xmax", "ymax"), box)) if status == "PRESENT" else None,
            "qualityFlags": flags or {}}


def test_tracking_sessions_split_on_gap_and_jump():
    cfg = TemporalConfig(max_gap_s=0.2)
    frames = [frame(0), frame(1), frame(2, status="ABSENT"), frame(3), frame(30), frame(31, box=(500, 500, 510, 510))]
    assert assign_tracks(frames, cfg) == [1, 1, None, 1, 2, 3]


def test_summary_metrics_on_known_signal():
    frames = [frame(i, area=1000.0 + 30 * i, centroid=(5, 5)) for i in range(10)] + [frame(10, status="ABSENT")]
    s = summarize(frames, fps=30.0, sample_every=1)
    assert s["persistenceRate"] == pytest.approx(10 / 11, abs=1e-4)
    assert s["areaChangeRate"]["meanAbs"] == pytest.approx(900.0)  # 30 px^2 per 1/30 s
    assert s["trackingStability"]["value"] == pytest.approx(0.0)
    assert s["trackSessions"] == 1


def sine_frames(hz, seconds=4.0, fps=30.0):
    n = int(seconds * fps)
    return [frame(i, fps, area=1000 + 100 * math.sin(2 * math.pi * hz * i / fps)) for i in range(n)]


def test_flicker_estimates_known_frequency():
    out = flicker_frequency(sine_frames(3.0), 30.0, 1, TemporalConfig())
    assert out["valueHz"] == pytest.approx(3.0, abs=0.3)


@pytest.mark.parametrize("case", ["nyquist", "short", "constant", "noise", "flagged"])
def test_flicker_not_estimable(case):
    fps, sample_every, frames = 30.0, 1, sine_frames(3.0)
    if case == "nyquist":
        sample_every = 2  # 15 Hz sampling < 2 x 10 Hz
    elif case == "short":
        frames = sine_frames(3.0, seconds=1.0)
    elif case == "constant":
        frames = [frame(i) for i in range(120)]
    elif case == "noise":
        rng = np.random.default_rng(0)
        frames = [frame(i, area=1000 + float(rng.normal(0, 50))) for i in range(120)]
    elif case == "flagged":
        frames = [frame(i, area=1000 + 100 * math.sin(i), flags={"blur": i % 20 == 0}) for i in range(120)]
    out = flicker_frequency(frames, fps, sample_every, TemporalConfig())
    assert out["valueHz"] == NOT_ESTIMABLE and out["reason"]


def test_summary_reports_not_estimable_status():
    s = summarize(sine_frames(3.0, seconds=1.0), 30.0, 1)
    assert s["flickerFrequencyHz"] == NOT_ESTIMABLE and s["flickerStatus"] == "NOT_ESTIMABLE" and s["flickerNote"]


# ---------------------------------------------------------------- end-to-end, contract, resume
def test_analyze_video_matches_contract(video, tmp_path):
    result = analyze_video(video, tmp_path / "out", video_cfg=VideoConfig(allowed_codecs=None, sample_every=4))
    validate(result)
    assert result["videoMetadata"]["frameCount"] == 20
    assert [m["frameIndex"] for m in result["frameMeasurements"]] == [0, 4, 8, 12, 16]
    assert all(m["frameId"].startswith(result["videoId"]) for m in result["frameMeasurements"])
    assert result["frameMeasurements"][0]["detectionStatus"] == "PRESENT"
    assert (REPO / result["artifacts"]["summaryUri"]).exists() or Path(result["artifacts"]["summaryUri"]).exists()


class Interrupted(RuntimeError):
    pass


def test_interrupted_run_resumes_from_checkpoint(video, tmp_path):
    cfg = VideoConfig(allowed_codecs=None, sample_every=2)
    out = tmp_path / "out"
    calls = []

    def flaky(request, *a, **k):
        if len(calls) == 4:
            raise Interrupted()
        calls.append(request["imageId"])
        return analyze_image_safe(request, *a, **k)

    with pytest.raises(Interrupted):
        analyze_video(video, out, video_cfg=cfg, analyzer=flaky)
    state = json.loads(next(out.glob("*/job.json")).read_text())
    assert state["status"] == "RUNNING"

    resumed = []

    def counting(request, *a, **k):
        resumed.append(request["imageId"])
        return analyze_image_safe(request, *a, **k)

    result = analyze_video(video, out, video_cfg=cfg, analyzer=counting)
    assert len(resumed) == 10 - 4 and not set(resumed) & set(calls)
    assert len(result["frameMeasurements"]) == 10
    validate(result)
    assert json.loads(next(out.glob("*/job.json")).read_text())["status"] == "COMPLETE"

    # A completed job re-assembles from its checkpoint without re-analyzing.
    again = []
    analyze_video(video, out, video_cfg=cfg, analyzer=lambda r, *a, **k: again.append(r) or {})
    assert again == []


def test_truncated_checkpoint_line_is_tolerated(video, tmp_path):
    cfg = VideoConfig(allowed_codecs=None, sample_every=5)
    out = tmp_path / "out"
    analyze_video(video, out, video_cfg=cfg)
    ckpt = next(out.glob("*/frames.jsonl"))
    lines = ckpt.read_text().splitlines()
    ckpt.write_text("\n".join(lines[:2]) + "\n" + lines[2][:20])
    result = analyze_video(video, out, video_cfg=cfg)
    assert len(result["frameMeasurements"]) == 4


def test_changed_config_discards_stale_checkpoint(video, tmp_path):
    out = tmp_path / "out"
    analyze_video(video, out, video_cfg=VideoConfig(allowed_codecs=None, sample_every=5))
    result = analyze_video(video, out, video_cfg=VideoConfig(allowed_codecs=None, sample_every=10))
    assert [m["frameIndex"] for m in result["frameMeasurements"]] == [0, 10]


def test_frame_analysis_error_becomes_uncertain(video, tmp_path):
    bad = lambda *a, **k: {"status": "ERROR", "error": {"code": "DECODE_FAILED", "message": "x"}}
    result = analyze_video(video, tmp_path / "out", video_cfg=VideoConfig(allowed_codecs=None, sample_every=10),
                           analyzer=bad)
    assert all(m["detectionStatus"] == "UNCERTAIN" and m["error"]["code"] == "DECODE_FAILED"
               for m in result["frameMeasurements"])
    validate(result)


def test_cli(video, tmp_path, capsys):
    code = video_main([str(video), "--out-dir", str(tmp_path / "o"), "--sample-every", "10"])
    assert code == 1  # default codec policy rejects MJPG
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


@pytest.mark.skipif(SAMPLE_VIDEO is None, reason="sample video not present")
def test_real_sample_video_end_to_end(tmp_path):
    result = analyze_video(SAMPLE_VIDEO, tmp_path / "out", video_cfg=VideoConfig(sample_every=300))
    validate(result)
    assert result["videoMetadata"]["resolution"] == [720, 480]
    assert result["lineage"]["codec"] in vi.ALLOWED_CODECS
    assert re.fullmatch(r"vid_[0-9a-f]{16}", result["videoId"])


def test_a_glow_that_never_moves_is_rejected_and_a_moving_one_is_kept(tmp_path):
    # Two synthetic dark videos: a faint blue lobe fixed in place (scenery) and one drifting across the frame
    # (a spreading dim flame). Only the drifting one stays UNCERTAIN.
    from cv.video_analysis import analyze_video
    from cv.video_ingestion import VideoConfig

    def write(path, moving):
        vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (320, 240))
        for i in range(30):
            img = np.zeros((240, 320, 3), np.uint8)
            x = 60 + 7 * i if moving else 160
            cv2.ellipse(img, (x, 120), (22, 8), 0, 0, 360, (8, 0, 0), -1)
            vw.write(img)
        vw.release()
        return path

    cfg = VideoConfig(allowed_codecs=None, sample_every=3, max_frames=10)
    still = analyze_video(write(tmp_path / "still.avi", False), tmp_path / "w1", video_cfg=cfg, resume=False)
    moving = analyze_video(write(tmp_path / "moving.avi", True), tmp_path / "w2", video_cfg=cfg, resume=False)
    assert {f["detectionStatus"] for f in still["frameMeasurements"]} == {"ABSENT"}
    assert any(f.get("qualityFlags", {}).get("staticGlow") for f in still["frameMeasurements"])
    kept = [f for f in moving["frameMeasurements"] if f["detectionStatus"] == "UNCERTAIN"]
    assert len(kept) >= 5 and all(f["qualityFlags"]["dimGlow"] for f in kept)
