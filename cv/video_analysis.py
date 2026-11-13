"""
video_analysis.py - End-to-end video analysis: ingestion -> per-frame flame analysis -> temporal summary (A1/A2/A4).

Per-frame measurements are appended to a JSONL checkpoint as they are computed, so an interrupted
run resumes from the last completed frame instead of starting over. A caller that keeps the
checkpoint elsewhere (the API worker keeps it in PostgreSQL, ADR-008) restores it with
``seed_checkpoint`` and receives every new frame through ``on_frame``. Run from the repo root:

    python -m cv.video_analysis path/to/video.mp4 [--out-dir cv/output/video] [--sample-every N] [--max-frames N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import cv2
import numpy as np

from cv.flame_cv import (PIPELINE_VERSION, CVConfig, CVError, ErrorDetail, ErrorResponse, analyze_image_safe,
                         atomic_write_text, posix, sha256_file, utc_now)
from cv.overlay_mask import apply_overlay_mask, build_overlay_mask
from cv.temporal_analysis import TemporalConfig, summarize
from cv.video_ingestion import (VIDEO_PIPELINE_VERSION, VideoConfig, iter_frames, probe_video, public_record,
                                sampled_indexes)

VIDEO_SCHEMA_VERSION = "1.4.0"
FrameAnalyzer = Callable[..., Dict[str, Any]]
# Called once when the run starts ({"event": "start", ...}) and after each frame is checkpointed
# ({"event": "frame", "row": ...}); both carry videoId, digest, total and done. An exception raised
# by the hook stops the run; the frames already written stay in the checkpoint, so it can resume.
FrameHook = Callable[[Dict[str, Any]], None]


def _job_digest(record: Dict[str, Any], vcfg: VideoConfig, cfg: CVConfig) -> str:
    payload = json.dumps({"video": record["checksum"], "pipeline": VIDEO_PIPELINE_VERSION,
                          "cv": PIPELINE_VERSION, "video_cfg": asdict(vcfg), "cv_cfg": asdict(cfg)},
                         sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _measurement(frame, result: Dict[str, Any]) -> Dict[str, Any]:
    """Compact per-frame record built from an AnalysisResult or an error response."""
    base = {"frameId": frame.frameId, "frameIndex": frame.frameIndex, "sourceFrameIndex": frame.sourceFrameIndex,
            "timestamp": frame.timestamp, "sourceTimestamp": frame.sourceTimestamp}
    if result.get("status") != "SUCCESS":
        err = result.get("error", {})
        return {**base, "detectionStatus": "UNCERTAIN", "pixelArea": None,
                "error": {"code": err.get("code", "INTERNAL_ERROR"), "message": err.get("message", "")}}
    det = result["detection"]
    geom = result["measurements"].get("geometry")
    box = det.get("boundingBox") or {}
    rec = {**base, "detectionStatus": det["status"], "detectionConfidence": det["confidence"],
           "pixelArea": geom["pixelArea"] if geom else None,
           "qualityFlags": result["confidenceAndQualityFlags"]["qualityFlags"],
           "analysisId": result["analysisId"]}
    if geom:
        rec["centroid"] = geom["centroid"]
    if all(box.get(k) is not None for k in ("xmin", "ymin", "xmax", "ymax")):
        rec["boundingBox"] = {k: box[k] for k in ("xmin", "ymin", "xmax", "ymax")}
    return rec


def _overlay_mask(video_path: Any, record: Dict[str, Any], vcfg: VideoConfig, job_dir: Path):
    """Build the overlay mask from frames sampled across the whole video; write it as an artifact."""
    ocfg = vcfg.overlay
    if not ocfg.enabled:
        return None, build_overlay_mask(np.zeros((1, 1, 1), np.uint8), ocfg)[1]
    every = max(1, record["frameCount"] // max(1, ocfg.sample_frames))
    sampler = VideoConfig(allowed_codecs=None, sample_every=every, max_frames=ocfg.sample_frames)
    gray = np.stack([cv2.cvtColor(f.image, cv2.COLOR_BGR2GRAY) for f in iter_frames(video_path, record, sampler)])
    mask, info = build_overlay_mask(gray, ocfg)
    mask_path = job_dir / "overlay_mask.png"
    cv2.imwrite(str(mask_path), mask)
    info.update(uri=posix(mask_path), checksum=sha256_file(mask_path))
    return (mask if mask.any() else None), info


def _load_checkpoint(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            break  # truncated tail from an interrupted write
    return rows


def seed_checkpoint(work_dir: Any, video_id: str, digest: str, rows: List[Dict[str, Any]]) -> None:
    """Write a checkpoint kept elsewhere back into ``work_dir`` so that ``analyze_video`` resumes from it.

    ``analyze_video`` still compares ``digest`` with the job it is asked to run and discards the rows
    when they differ (another video, pipeline version or sampling), so a stale seed is harmless.
    """
    job_dir = Path(work_dir) / video_id
    job_dir.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda r: r["frameIndex"])
    atomic_write_text(job_dir / "frames.jsonl", "".join(json.dumps(r) + "\n" for r in ordered))
    atomic_write_text(job_dir / "job.json", json.dumps({"digest": digest, "status": "RUNNING", "videoId": video_id,
                                                        "updatedAt": utc_now()}, indent=2))


def analyze_video(video_path: Any, work_dir: Any, cfg: Optional[CVConfig] = None,
                  video_cfg: Optional[VideoConfig] = None, temporal_cfg: Optional[TemporalConfig] = None,
                  resume: bool = True, analyzer: FrameAnalyzer = analyze_image_safe,
                  on_frame: Optional[FrameHook] = None) -> Dict[str, Any]:
    """Analyze a video and return a ``VideoAnalysisResult`` payload (raises CVError on failure)."""
    cfg = cfg or CVConfig()
    video_cfg = video_cfg or VideoConfig()
    temporal_cfg = temporal_cfg or TemporalConfig()

    record = probe_video(video_path, video_cfg)
    job_dir = Path(work_dir) / record["videoId"]
    frames_dir, masks_dir, cv_dir = job_dir / "frames", job_dir / "masks", job_dir / "cv"
    for d in (frames_dir, masks_dir, cv_dir):
        d.mkdir(parents=True, exist_ok=True)

    digest = _job_digest(record, video_cfg, cfg)
    state_path, ckpt_path = job_dir / "job.json", job_dir / "frames.jsonl"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    if not resume or state.get("digest") != digest:
        ckpt_path.unlink(missing_ok=True)
    done = _load_checkpoint(ckpt_path)
    atomic_write_text(state_path, json.dumps({"digest": digest, "status": "RUNNING", "videoId": record["videoId"],
                                              "updatedAt": utc_now()}, indent=2))

    # Deterministic for a given video and config (both are in the digest), so a resumed run rebuilds the same mask.
    overlay_mask, overlay_info = _overlay_mask(video_path, record, video_cfg, job_dir)

    total = len(sampled_indexes(record["frameCount"], video_cfg))
    done_idx = {r["frameIndex"] for r in done}
    progress = {"videoId": record["videoId"], "digest": digest, "total": total}
    if on_frame is not None:
        on_frame({"event": "start", **progress, "done": len(done)})
    if len(done_idx) < total:
        with open(ckpt_path, "w", encoding="utf-8") as f:  # rewrite to drop any truncated tail
            for r in done:
                f.write(json.dumps(r) + "\n")
        with open(ckpt_path, "a", encoding="utf-8") as f:
            for frame in iter_frames(video_path, record, video_cfg, skip=done_idx):
                img_path = frames_dir / f"{frame.frameId}.png"
                image = frame.image if overlay_mask is None else apply_overlay_mask(frame.image, overlay_mask)
                cv2.imwrite(str(img_path), image)
                result = analyzer({"requestId": frame.frameId, "imageId": frame.frameId, "imagePath": str(img_path)},
                                  cv_dir, masks_dir, cfg=cfg)
                row = _measurement(frame, result)
                f.write(json.dumps(row) + "\n")
                f.flush()
                done.append(row)
                if on_frame is not None:
                    on_frame({"event": "frame", **progress, "done": len(done), "row": row})

    measurements = sorted(done, key=lambda r: r["frameIndex"])
    summary = summarize(measurements, record["fps"], video_cfg.sample_every, temporal_cfg)
    result = {
        "schemaVersion": VIDEO_SCHEMA_VERSION,
        "status": "SUCCESS",
        "analysisId": f"vid_an_{digest}",
        "videoId": record["videoId"],
        "pipelineVersion": f"{VIDEO_PIPELINE_VERSION}+{PIPELINE_VERSION}",
        "videoMetadata": {k: record[k] for k in ("fps", "frameCount", "durationSeconds", "resolution")},
        "lineage": {k: v for k, v in public_record(record).items()
                    if k in ("checksum", "sourcePath", "sizeBytes", "container", "codec", "sourceFrameCount",
                             "timestamps", "sampling")},
        "overlayMask": overlay_info,
        "frameMeasurements": measurements,
        "temporalSummary": summary,
        "provenance": {"createdAt": utc_now(), "cvPipelineVersion": PIPELINE_VERSION,
                       "videoPipelineVersion": VIDEO_PIPELINE_VERSION, "jobDigest": digest},
    }
    summary_path = job_dir / "summary.json"
    atomic_write_text(summary_path, json.dumps(result, indent=2, ensure_ascii=False))
    result["artifacts"] = {"summaryUri": posix(summary_path), "checksum": sha256_file(summary_path)}
    atomic_write_text(state_path, json.dumps({"digest": digest, "status": "COMPLETE", "videoId": record["videoId"],
                                              "updatedAt": utc_now()}, indent=2))
    return result


def analyze_video_safe(video_path: Any, work_dir: Any, **kwargs: Any) -> Dict[str, Any]:
    try:
        return analyze_video(video_path, work_dir, **kwargs)
    except CVError as e:
        return ErrorResponse(requestId=None, error=ErrorDetail(
            code=e.code, message=e.message, retryable=e.retryable, httpStatus=e.http_status)).model_dump(mode="json")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m cv.video_analysis", description="Analyze a flame video.")
    parser.add_argument("video", help="Path to an .mp4/.avi/.mov file.")
    parser.add_argument("--out-dir", default="cv/output/video")
    parser.add_argument("--sample-every", type=int, default=1)
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument("--no-resume", action="store_true", help="Discard any checkpoint and start over.")
    args = parser.parse_args(argv)

    result = analyze_video_safe(args.video, args.out_dir, resume=not args.no_resume,
                                video_cfg=VideoConfig(sample_every=args.sample_every, max_frames=args.max_frames))
    if result.get("status") == "SUCCESS":
        print(json.dumps({k: result[k] for k in ("videoId", "analysisId", "videoMetadata", "temporalSummary",
                                                  "artifacts")}, indent=2))
        print(f"[*] Analyzed {len(result['frameMeasurements'])} frames", file=sys.stderr)
        return 0
    print(json.dumps(result, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
