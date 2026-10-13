"""tests/cv/test_contract_examples.py - every committed CV contract example validates against its schema."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[2]
CONTRACTS = REPO / "cv" / "contracts"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_schemas_are_valid_json_schemas():
    for name in ("analysis_result.schema.json", "video_analysis_result.schema.json", "image_intake_schema.json"):
        Draft202012Validator.check_schema(load(CONTRACTS / name))


def test_video_contract_doc_examples_validate():
    text = (REPO / "docs" / "cv" / "video-contract.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```json\s*(\{.*?\n\})\s*```", text, flags=re.S)
    assert blocks, "docs/cv/video-contract.md has no JSON example block"
    validator = Draft202012Validator(load(CONTRACTS / "video_analysis_result.schema.json"))
    for block in blocks:
        validator.validate(json.loads(block))


def test_video_fixture_validates_current_schema():
    fixture = Path(__file__).parent / "fixtures" / "video_analysis_result.example.json"
    Draft202012Validator(load(CONTRACTS / "video_analysis_result.schema.json")).validate(load(fixture))


def test_per_image_results_validate():
    validator = Draft202012Validator(load(CONTRACTS / "analysis_result.schema.json"))
    files = sorted((CONTRACTS / "results").glob("*.json"))
    assert files, "no per-image results committed"
    for path in files:
        validator.validate(load(path))


def test_aggregate_results_validate():
    validator = Draft202012Validator(load(CONTRACTS / "analysis_result.schema.json"))
    for item in load(CONTRACTS / "analysis_results_all.json"):
        validator.validate(item)
    validator.validate(load(CONTRACTS / "analysis_result.json"))
