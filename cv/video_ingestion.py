"""
video_ingestion.py - Video ingestion for the flame CV pipeline (A1 / E3-6).

Validates a local video, probes its metadata (fps, resolution, frame count, source vs. derived
timestamps), derives a content-addressed ``videoId`` and stable frame IDs, and yields frames
according to a sampling policy. The source file is only ever opened read-only.

Variable-frame-rate (VFR) policy: streams whose source timestamps drift from a uniform grid are
normalized to a constant frame rate by nearest-frame resampling (frames may be repeated or
skipped); no pixel interpolation is performed.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import cv2
import numpy as np

from cv.flame_cv import (CVError, DecodeError, FileMissingError, FileTooLargeError, InvalidRequestError,
                         UnsupportedMediaError, posix)
from cv.overlay_mask import OverlayMaskConfig

VIDEO_PIPELINE_VERSION = "cv-video-v1.2.0"   # v1.2.0: a faint glow that does not move is rejected
ALLOWED_EXTENSIONS = (".mp4", ".avi", ".mov")
ALLOWED_CODECS = ("avc1", "h264", "x264", "hev1", "hvc1", "hevc", "h265")


class VideoTooLongError(CVError):
    code, http_status = "VIDEO_TOO_LONG", 413


@dataclass(frozen=True)
class VideoConfig:
    max_bytes: int = 500 * 1024 * 1024
    max_duration_s: float = 600.0
    # None disables the codec check (used for synthetic test videos).
    allowed_codecs: Optional[Tuple[str, ...]] = ALLOWED_CODECS
    sample_every: int = 1
    max_frames: Optional[int] = None
    vfr_tolerance_frames: float = 0.5
    # Burned-in text overlays are excluded before segmentation (cv/overlay_mask.py).
    overlay: OverlayMaskConfig = field(default_factory=OverlayMaskConfig)


@dataclass
class FrameRef:
    frameId: str
    frameIndex: int
    sourceFrameIndex: int
    timestamp: float
    sourceTimestamp: Optional[float]
    image: np.ndarray = field(repr=False)


def video_id_for(sha256_hex: str) -> str:
    return f"vid_{sha256_hex[:16]}"


def frame_id_for(video_id: str, index: int) -> str:
    return f"{video_id}_frame_{index:06d}"


def _sha256_hex(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _fourcc(cap: cv2.VideoCapture) -> str:
    code = int(cap.get(cv2.CAP_PROP_FOURCC) or 0)
    return "".join(chr((code >> (8 * i)) & 0xFF) for i in range(4)).strip("\x00 ").lower()


def _scan_timestamps(path: Path) -> List[float]:
    cap = cv2.VideoCapture(str(path))
    stamps: List[float] = []
    try:
        while cap.grab():
            stamps.append(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0)
    finally:
        cap.release()
    return stamps


def _cfr_mapping(stamps: List[float], fps: float) -> List[int]:
    """Map each uniform output index to the nearest source frame index."""
    ts = np.asarray(stamps, dtype=np.float64)
    n_out = max(1, int(round((ts[-1] - ts[0]) * fps)) + 1)
    grid = ts[0] + np.arange(n_out) / fps
    right = np.clip(np.searchsorted(ts, grid), 1, len(ts) - 1)
    left = right - 1
    pick = np.where(np.abs(ts[left] - grid) <= np.abs(ts[right] - grid), left, right)
    return pick.astype(int).tolist()


def probe_video(path: Any, cfg: Optional[VideoConfig] = None) -> Dict[str, Any]:
    """Validate a video and return its metadata and lineage record."""
    cfg = cfg or VideoConfig()
    if not path:
        raise InvalidRequestError("videoPath is required.")
    p = Path(path)
    if not p.is_file():
        raise FileMissingError(f"Video not found: {p.name}")
    if p.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise UnsupportedMediaError(f"Unsupported container '{p.suffix}'. Accepted: {', '.join(ALLOWED_EXTENSIONS)}.")
    size = p.stat().st_size
    if size > cfg.max_bytes:
        raise FileTooLargeError(f"Video is {size} bytes; the limit is {cfg.max_bytes}.")

    cap = cv2.VideoCapture(str(p))
    try:
        if not cap.isOpened():
            raise DecodeError("Video could not be opened (corrupted header or unsupported stream).")
        nominal_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        codec = _fourcc(cap)
    finally:
        cap.release()

    if nominal_fps <= 0 or width <= 0 or height <= 0:
        raise DecodeError("Video reports no valid frame rate or resolution.")
    if cfg.allowed_codecs is not None and codec not in cfg.allowed_codecs:
        raise UnsupportedMediaError(f"Unsupported codec '{codec}'. Accepted: {', '.join(cfg.allowed_codecs)}.")

    stamps = _scan_timestamps(p)
    if not stamps:
        raise DecodeError("No decodable frames found in the video stream.")
    source_count = len(stamps)

    usable = source_count > 1 and all(b > a for a, b in zip(stamps, stamps[1:]))
    deviation = 0.0
    vfr = False
    fps = nominal_fps
    mapping: Optional[List[int]] = None
    if usable:
        offsets = np.asarray(stamps) - stamps[0]
        deviation = float(np.max(np.abs(offsets - np.arange(source_count) / nominal_fps)))
        vfr = deviation > cfg.vfr_tolerance_frames / nominal_fps
        if vfr:
            fps = (source_count - 1) / float(stamps[-1] - stamps[0])
            mapping = _cfr_mapping(stamps, fps)

    frame_count = len(mapping) if mapping is not None else source_count
    duration = frame_count / fps
    if duration > cfg.max_duration_s:
        raise VideoTooLongError(f"Video is {duration:.1f}s; the limit is {cfg.max_duration_s:.0f}s.")

    digest = _sha256_hex(p)
    return {
        "videoId": video_id_for(digest),
        "sourcePath": posix(p),
        "checksum": f"sha256:{digest}",
        "sizeBytes": size,
        "container": p.suffix.lower().lstrip("."),
        "codec": codec,
        "fps": round(fps, 6),
        "nominalFps": round(nominal_fps, 6),
        "frameCount": frame_count,
        "sourceFrameCount": source_count,
        "durationSeconds": round(duration, 6),
        "resolution": [width, height],
        "timestamps": {
            "sourceTimestampsUsable": usable,
            "derived": "frameIndex / fps",
            "maxDeviationSeconds": round(deviation, 6),
            "variableFrameRate": vfr,
            "vfrPolicy": "nearest-frame resampling to a constant frame rate" if vfr else "not applicable",
        },
        "sampling": {"every": cfg.sample_every, "maxFrames": cfg.max_frames},
        "_cfrMapping": mapping,
        "_sourceTimestamps": stamps if usable else None,
    }


def public_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Drop internal fields (leading underscore) from a probe record."""
    return {k: v for k, v in record.items() if not k.startswith("_")}


def sampled_indexes(frame_count: int, cfg: VideoConfig) -> List[int]:
    if cfg.sample_every < 1:
        raise InvalidRequestError("sample_every must be >= 1.")
    indexes = list(range(0, frame_count, cfg.sample_every))
    return indexes[: cfg.max_frames] if cfg.max_frames else indexes


def iter_frames(path: Any, record: Dict[str, Any], cfg: Optional[VideoConfig] = None,
                skip: Optional[set] = None) -> Iterator[FrameRef]:
    """Yield sampled frames with stable IDs. Indexes in ``skip`` are decoded past but not yielded."""
    cfg = cfg or VideoConfig()
    skip = skip or set()
    wanted = sampled_indexes(record["frameCount"], cfg)
    if not wanted:
        return
    mapping: Optional[List[int]] = record.get("_cfrMapping")
    stamps: Optional[List[float]] = record.get("_sourceTimestamps")
    fps = record["fps"]
    # source frame index -> output indexes that use it (a VFR gap repeats frames)
    by_source: Dict[int, List[int]] = {}
    for k in wanted:
        by_source.setdefault(mapping[k] if mapping is not None else k, []).append(k)
    last_source = max(by_source)

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise DecodeError("Video could not be opened for frame extraction.")
    try:
        for src in range(last_source + 1):
            if not cap.grab():
                raise DecodeError(f"Decoding stopped at source frame {src} of {record['sourceFrameCount']}.")
            if src not in by_source:
                continue
            todo = [k for k in by_source[src] if k not in skip]
            if not todo:
                continue
            ok, image = cap.retrieve()
            if not ok:
                raise DecodeError(f"Frame {src} could not be decoded.")
            for k in todo:
                yield FrameRef(
                    frameId=frame_id_for(record["videoId"], k), frameIndex=k, sourceFrameIndex=src,
                    timestamp=round(k / fps, 6),
                    sourceTimestamp=round(stamps[src] - stamps[0], 6) if stamps else None, image=image)
    finally:
        cap.release()
