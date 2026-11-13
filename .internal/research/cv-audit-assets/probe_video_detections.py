import sys, json, collections
from cv.video_analysis import analyze_video
from cv.video_ingestion import VideoConfig
S=sys.argv[1]
for v in sys.argv[2:]:
    r = analyze_video(v, S+"/vid", video_cfg=VideoConfig(sample_every=30, max_frames=60), resume=False)
    fm = r["frameMeasurements"]
    st = collections.Counter(f["detectionStatus"] for f in fm)
    h = r["videoMetadata"]["resolution"][1]
    boxes=[f["boundingBox"] for f in fm if f.get("boundingBox")]
    in_banner = sum(1 for b in boxes if b["ymax"] <= 0.25*h)
    touch_banner = sum(1 for b in boxes if b["ymin"] <= 0.20*h)
    multi = sum(1 for f in fm if f.get("qualityFlags",{}).get("multipleFlames"))
    areas=[f["pixelArea"] for f in fm if f.get("pixelArea")]
    print(v.split("/")[-1][-45:], dict(st), "boxes",len(boxes),"entirely_in_top25%",in_banner,"ymin_in_top20%",touch_banner,"multiFlag",multi)
    print("  sample boxes:", boxes[:4])
    print("  temporal:", {k:r["temporalSummary"][k] for k in ("persistenceRate","flickerFrequencyHz","flickerNote","trackSessions")})
