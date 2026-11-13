import json
from pathlib import Path

import jsonschema

from ai.rag.nlp.evaluation import GoldCase, gold_sha256, load_gold, score
from ai.rag.nlp.records import NlpRecord

GOLD = Path("datasets/evaluation/nlp_gold_v1.jsonl")
SCHEMA = Path("datasets/evaluation/nlp_gold_v1.schema.json")


def _pred(t, s, e):
    return NlpRecord(record_type=t, text="x" * (e - s), document_id="d", document_version="v1", page=1, char_start=s,
                     char_end=e, chunk_id="c", extractor="x", extractor_version="1", method="rule", confidence=1.0)


CASE = GoldCase("g1", "dev", "d", 1, "x" * 60, [{"record_type": "experiment", "char_start": 7, "char_end": 14},
                                                 {"record_type": "fuel", "char_start": 20, "char_end": 28}])


def test_strict_scores_per_type():
    out = score([CASE], {"g1": [_pred("experiment", 7, 14), _pred("experiment", 30, 35)]})
    assert out["experiment"] == {"tp": 1, "fp": 1, "fn": 0, "precision": 0.5, "recall": 1.0, "f1": 2 / 3}
    assert out["fuel"]["precision"] is None and out["fuel"]["recall"] == 0.0 and out["fuel"]["f1"] is None


def test_relaxed_accepts_overlap_but_strict_does_not():
    prediction = {"g1": [_pred("experiment", 7, 12)]}   # IoU 5/7 >= 0.5
    assert score([CASE], prediction)["experiment"]["tp"] == 0
    assert score([CASE], prediction, relaxed=True)["experiment"]["tp"] == 1


def test_wrong_type_never_matches():
    assert score([CASE], {"g1": [_pred("fuel", 7, 14)]})["experiment"]["tp"] == 0


def test_gold_file_validates_against_its_schema_and_spans_match_the_text():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    for line in GOLD.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        jsonschema.validate(case, schema)
        for annotation in case["annotations"]:
            assert case["chunk_text"][annotation["char_start"]:annotation["char_end"]] == annotation["text"], case["gold_id"]


def test_load_gold_filters_by_split_and_checksum_is_stable(tmp_path):
    path = tmp_path / "g.jsonl"
    rows = [{"gold_id": f"NG-00{i}", "split": s, "document_id": "d", "page": 1, "chunk_text": "abc", "annotations": []}
            for i, s in enumerate(["dev", "validation", "dev"])]
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    assert [c.gold_id for c in load_gold(path, split="dev")] == ["NG-000", "NG-002"]
    assert len(load_gold(path)) == 3 and gold_sha256(path) == gold_sha256(path) and len(gold_sha256(path)) == 64
