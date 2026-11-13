"""tests/cv/test_gold.py - the CV evaluation set: schema, leakage, metrics, mask geometry and an end-to-end run."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from jsonschema import Draft202012Validator

from cv import gold
from cv.flame_cv import make_synthetic_flame

REPO = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- committed files
def test_committed_gold_validates_and_has_no_leakage():
    schema = json.loads((REPO / "datasets/evaluation/cv_gold_v1.schema.json").read_text(encoding="utf-8"))
    items = gold.load_gold(REPO / gold.GOLD_PATH)
    assert items, "the gold set is empty"
    validator = Draft202012Validator(schema)
    for item in items:
        validator.validate(item)
    splits = {}
    for item in items:
        splits.setdefault(item["groupId"], set()).add(item["split"])
    assert all(len(s) == 1 for s in splits.values()), "a test appears in more than one split"
    assert len({i["itemId"] for i in items}) == len(items)


def test_committed_gold_covers_every_sampled_frame_and_mask_files_exist():
    sources = gold.load_sources(REPO / gold.SOURCES_PATH)
    items = {i["itemId"]: i for i in gold.load_gold(REPO / gold.GOLD_PATH)}
    expected = {ref.item_id for ref in gold.enumerate_items(sources)}
    assert expected == set(items)
    for item in items.values():
        if item["mask"]:
            assert (REPO / item["mask"]["uri"]).is_file(), item["itemId"]
            assert item["label"] == "present"


def test_committed_gold_has_enough_negatives():
    items = gold.load_gold(REPO / gold.GOLD_PATH)
    for split in ("dev", "holdout"):
        labels = [i["label"] for i in items if i["split"] == split and i["label"] != "unclear"]
        assert labels and labels.count("absent") / len(labels) >= 0.3, split


# ---------------------------------------------------------------- metrics
def test_detection_metrics():
    rows = [("present", "PRESENT"), ("present", "UNCERTAIN"), ("absent", "PRESENT"), ("absent", "ABSENT"),
            ("absent", "UNCERTAIN"), ("unclear", "PRESENT")]
    strict = gold.detection_metrics(rows, positive={"PRESENT"})
    assert (strict["tp"], strict["fp"], strict["fn"], strict["tn"]) == (1, 1, 1, 2)
    assert strict["precision"] == 0.5 and strict["recall"] == 0.5 and strict["falsePositiveRate"] == pytest.approx(1 / 3, abs=1e-4)
    lenient = gold.detection_metrics(rows, positive={"PRESENT", "UNCERTAIN"})
    assert (lenient["tp"], lenient["fp"], lenient["fn"], lenient["tn"]) == (2, 2, 0, 1)
    assert gold.detection_metrics([], positive={"PRESENT"})["precision"] is None


def test_localized_detection_needs_the_right_place():
    # A PRESENT call on a flame frame only counts as found if the mask overlaps the labelled flame.
    rows = [{"groupId": "g", "label": "present", "status": "PRESENT", "iou": 0.6},
            {"groupId": "g", "label": "present", "status": "PRESENT", "iou": 0.0},   # e.g. the overlay text
            {"groupId": "g", "label": "absent", "status": "PRESENT", "iou": None}]
    s = gold._summary(rows, reps=10, seed=0)
    assert s["detection"]["strict"]["tp"] == 2
    loc = s["detection"]["localized"]
    assert (loc["tp"], loc["fn"], loc["fp"]) == (1, 1, 1)


def test_bootstrap_resamples_groups_not_frames():
    # Two groups: one all correct (10 frames), one all wrong (1 frame). Frame-level accuracy is 10/11,
    # but resampling groups must give an interval reaching down to 0 (draw only the bad group).
    rows = [("g1", 1.0)] * 10 + [("g2", 0.0)]
    lo, hi = gold.group_bootstrap(rows, lambda vals: float(np.mean(vals)), reps=500, seed=0)
    assert lo == 0.0 and hi == 1.0


def test_iou_after_letterbox():
    gt = np.zeros((480, 720), np.uint8)
    cv2.ellipse(gt, (360, 240), (80, 60), 0, 0, 360, 255, -1)
    lb = gold.letterbox_for(720, 480)
    canvas = gold.to_letterbox(gt, lb)
    assert canvas.shape == (lb.target, lb.target)
    assert gold.mask_iou(canvas, canvas) == 1.0
    assert gold.mask_iou(canvas, np.zeros_like(canvas)) == 0.0


def test_draft_mask_from_box_finds_the_blob_not_the_box():
    img = np.zeros((240, 320, 3), np.uint8)
    cv2.ellipse(img, (160, 120), (40, 30), 0, 0, 360, (80, 180, 255), -1)
    mask = gold.draft_mask(img, (100, 70, 220, 170))
    truth = np.zeros((240, 320), np.uint8)
    cv2.ellipse(truth, (160, 120), (40, 30), 0, 0, 360, 255, -1)
    assert gold.mask_iou(mask, truth) > 0.85
    assert mask[:, :90].max() == 0, "nothing outside the box"


# ---------------------------------------------------------------- end to end on a synthetic set
def _synthetic_set(tmp_path: Path):
    imgs = tmp_path / "imgs"
    imgs.mkdir()
    make_synthetic_flame(imgs / "flame.png", size=(400, 300), blobs=[(200, 150, 50, 50)], gt_path=imgs / "flame_gt.png")
    cv2.imwrite(str(imgs / "empty.png"), np.zeros((300, 400, 3), np.uint8))
    sources = {"datasetId": "t", "sources": [
        {"sourceId": "flame", "groupId": "A/1", "split": "dev", "kind": "image", "path": str(imgs / "flame.png"),
         "sha256": gold.sha256_hex(imgs / "flame.png"), "sizeBytes": 1, "psi": None, "inGit": True, "sampling": None},
        {"sourceId": "empty", "groupId": "A/2", "split": "holdout", "kind": "image", "path": str(imgs / "empty.png"),
         "sha256": gold.sha256_hex(imgs / "empty.png"), "sizeBytes": 1, "psi": None, "inGit": True, "sampling": None}]}
    masks = tmp_path / "masks"
    masks.mkdir()
    gt = cv2.imread(str(imgs / "flame_gt.png"), cv2.IMREAD_GRAYSCALE)
    cv2.imwrite(str(masks / "flame.png"), gt)
    prov = {"labeller": "test", "labelledAt": "2026-11-13T00:00:00Z", "verified": False, "verifiedBy": None, "verifiedAt": None}
    items = [
        {"itemId": "flame", "sourceId": "flame", "groupId": "A/1", "split": "dev", "frameIndex": None, "label": "present",
         "mask": {"uri": str(masks / "flame.png"), "method": "test", "box": [0, 0, 400, 300]}, "notes": "", "provenance": prov},
        {"itemId": "empty", "sourceId": "empty", "groupId": "A/2", "split": "holdout", "frameIndex": None, "label": "absent",
         "mask": None, "notes": "", "provenance": prov}]
    return sources, items


def test_evaluate_end_to_end(tmp_path):
    sources, items = _synthetic_set(tmp_path)
    report = gold.evaluate(sources, items, tmp_path / "work", reps=50)
    dev, holdout = report["splits"]["dev"]["all"], report["splits"]["holdout"]["all"]
    assert dev["detection"]["strict"]["tp"] == 1 and dev["segmentation"]["meanIoU"] > 0.9
    assert holdout["detection"]["strict"]["tn"] == 1
    assert report["splits"]["dev"]["verified"]["n"] == 0, "nothing is verified yet"
    assert {r["itemId"] for r in report["items"]} == {"flame", "empty"}


def test_review_and_adopt_roundtrip(tmp_path):
    sources, items = _synthetic_set(tmp_path)
    csv_path = tmp_path / "review.csv"
    gold.write_review_sheet(items, csv_path)
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    assert [r["itemId"] for r in rows] == ["flame", "empty"]
    rows[0].update(verdict="accept", maskOk="yes", reviewer="ana")
    rows[1].update(verdict="fix", correctedLabel="unclear", reviewer="ana", notes="glare")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    adopted, summary = gold.adopt_review(items, csv_path, now="2026-11-14T00:00:00Z")
    by_id = {i["itemId"]: i for i in adopted}
    assert by_id["flame"]["provenance"]["verified"] and by_id["flame"]["provenance"]["verifiedBy"] == "ana"
    assert by_id["empty"]["label"] == "unclear" and by_id["empty"]["provenance"]["verified"]
    assert summary == {"accepted": 1, "fixed": 1, "skipped": 0, "maskRejected": 0}


def test_adopt_rejected_mask_is_dropped_and_item_stays_unverified(tmp_path):
    sources, items = _synthetic_set(tmp_path)
    csv_path = tmp_path / "review.csv"
    gold.write_review_sheet(items, csv_path)
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    rows[0].update(verdict="accept", maskOk="no", reviewer="ana")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    adopted, summary = gold.adopt_review(items, csv_path, now="2026-11-14T00:00:00Z")
    flame = next(i for i in adopted if i["itemId"] == "flame")
    assert flame["mask"] is None and flame["provenance"]["verified"] is False
    assert "mask rejected" in flame["notes"] and summary["maskRejected"] == 1
