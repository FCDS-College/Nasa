"""
tests/cv/test_contracts.py - Automated schema validation test for CV and video contracts.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest
from jsonschema import validate, ValidationError


def get_project_root() -> Path:
    """Get the root directory of the repository."""
    return Path(__file__).resolve().parents[2]


def test_video_contract_schema_validation() -> None:
    """Validate the synthetic video contract example against video_analysis_result.schema.json."""
    root = get_project_root()
    schema_path = root / "cv" / "contracts" / "video_analysis_result.schema.json"
    
    assert schema_path.exists(), f"Video schema not found at {schema_path}"
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
        
    # Synthetic example payload matching video contract v1.2.0
    example_payload = {
        "schemaVersion": "1.2.0",
        "status": "SUCCESS",
        "analysisId": "vid_an_987654321",
        "videoId": "vid_sample_01",
        "pipelineVersion": "cv-opencv-v1.2.0-auto",
        "videoMetadata": {
            "fps": 30.0,
            "frameCount": 90,
            "durationSeconds": 3.0,
            "resolution": [1920, 1080]
        },
        "frameMeasurements": [
            {
                "frameIndex": 0,
                "timestamp": 0.0,
                "detectionStatus": "PRESENT",
                "pixelArea": 45000.5
            }
        ],
        "temporalSummary": {
            "persistenceRate": 1.0,
            "flickerFrequencyHz": "not estimable"
        },
        "artifacts": {
            "summaryUri": "datasets/processed/videos/vid_sample_01_summary.json",
            "checksum": "sha256:abcdef1234567890"
        }
    }
    
    try:
        validate(instance=example_payload, schema=schema)
    except ValidationError as e:
        pytest.fail(f"Video contract example failed schema validation: {e.message}")


def test_analysis_result_committed_examples() -> None:
    """Validate committed analysis result files against analysis_result.schema.json."""
    root = get_project_root()
    schema_path = root / "cv" / "contracts" / "analysis_result.schema.json"
    
    if not schema_path.exists():
        pytest.skip("analysis_result.schema.json not found.")
        
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
        
    contracts_dir = root / "cv" / "contracts"
    # استبعاد ملفات المخطط (Schema files) وفقط جلب ملفات النتائج
    json_files = [f for f in contracts_dir.glob("analysis_result*.json") if not f.name.endswith(".schema.json")]
    
    if not json_files:
        pytest.skip("No committed analysis result JSON files found to validate.")

    for file_path in json_files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        instances = data if isinstance(data, list) else [data]
        for idx, instance in enumerate(instances):
            try:
                validate(instance=instance, schema=schema)
            except ValidationError as e:
                pytest.fail(f"File {file_path.name} at index {idx} failed schema validation: {e.message}")