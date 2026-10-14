import numpy as np
import torch

from cv.telemetry_ocr import (OCRConfig, field_accuracy, in_range, parse_numbers,
                              preprocess, vote)
from cv.video_embedding import train_next_embedding


def test_parse_numbers_drops_long_tokens():
    assert parse_numbers("FUEL 2 AIR -20 FAN 14.5 20091231") == ["2", "-20", "14.5"]


def test_in_range_rejects_noise():
    cfg = OCRConfig()
    assert in_range("fan", "144", cfg)
    assert not in_range("fuel", "144", cfg)


def test_vote_majority_and_min_votes():
    reads = [{"fuel": "2", "air": "5", "fan": None, "rad": "1"},
             {"fuel": "2", "air": "6", "fan": None, "rad": "1"},
             {"fuel": "3", "air": "7", "fan": "9", "rad": "1"}]
    res = vote(reads)
    assert res["fuel"]["value"] == "2" and abs(res["fuel"]["confidence"] - 0.667) < 1e-3
    assert res["air"]["value"] is None  # no two reads agree
    assert res["fan"]["value"] is None
    assert res["rad"]["confidence"] == 1.0


def test_field_accuracy():
    pred = vote([{"fuel": "2", "air": "5", "fan": "1", "rad": "1"}] * 2)
    assert field_accuracy(pred, {"fuel": "2", "air": "6"}) == {"fuel": 1.0, "air": 0.0}


def test_preprocess_dark_text_on_light():
    img = np.full((20, 40), 255, np.uint8)
    img[5:15, 10:20] = 0
    assert preprocess(img, 2.0).mean() > 127


def test_next_embedding_trains_and_reports_baseline():
    t = torch.linspace(0, 6, 40).unsqueeze(1)
    emb = torch.sin(t * torch.arange(1, 9)).repeat(1, 4)
    res = train_next_embedding(emb, epochs=60, device=torch.device("cpu"))
    assert res["val_mse"] >= 0 and "beats_baseline" in res
from cv.video_training import fuel_family, video_test_id, pool


def test_fuel_family_and_test_id():
    assert fuel_family("Nomex natural (nomex III)") == "nomex"
    assert fuel_family("Japan Wax candle") == "wax"
    assert fuel_family("3/8\" clear rod") == "rod"
    assert video_test_id("PSI-25_Raw Data_BASS_GMT50_SAMPLE_147_TEST_B1.mp4") == "B1"
    assert video_test_id("x_TEST_T25_2ND_VIEW.mp4") == "T25"


def test_pool_clips_colour_ratios():
    feats = {"emb": np.zeros((4, 3), np.float32), "hand": np.full((4, 8), 1e4, np.float32)}
    assert pool(feats, "hand").max() <= 1e4 and pool(feats, "hand").shape[0] == 24
