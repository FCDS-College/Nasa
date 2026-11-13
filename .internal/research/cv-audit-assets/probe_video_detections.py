"""Count where the served video pipeline puts its "flame" boxes (CV audit, finding CV-1).

    PYTHONPATH=. python .internal/research/cv-audit-assets/probe_video_detections.py <workdir> <video.mp4> [...]

Boxes that end in the top 25% of the frame are the telemetry overlay, not a flame.
"""
import collections
import sys

from cv.video_analysis import analyze_video
from cv.video_ingestion import VideoConfig

work_dir = sys.argv[1]
for video in sys.argv[2:]:
    result = analyze_video(video, work_dir, video_cfg=VideoConfig(sample_every=30, max_frames=60), resume=False)
    frames = result["frameMeasurements"]
    statuses = collections.Counter(f["detectionStatus"] for f in frames)
    height = result["videoMetadata"]["resolution"][1]
    boxes = [f["boundingBox"] for f in frames if f.get("boundingBox")]
    in_overlay = sum(1 for b in boxes if b["ymax"] <= 0.25 * height)
    multi = sum(1 for f in frames if f.get("qualityFlags", {}).get("multipleFlames"))
    print(video.split("/")[-1][-45:], dict(statuses), "boxes", len(boxes),
          "entirely_in_top25%", in_overlay, "multipleFlames", multi)
    print("  sample boxes:", boxes[:4])
    print("  temporal:", {k: result["temporalSummary"][k]
                          for k in ("persistenceRate", "flickerFrequencyHz", "flickerNote", "trackSessions")})
