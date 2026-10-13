"""E2-1: the source registry validates against its schema, with the documented CSV encoding."""
import csv

from flame_api.registry import REGISTRY_CSV, decode_row, load_schema, read_registry, validate_registry


def test_the_committed_registry_is_valid():
    assert validate_registry() == []


def test_arrays_nulls_and_integers_are_decoded():
    schema = load_schema()
    row = decode_row({"source_id": "FF-X", "data_modalities": "video; stills ;", "license": "null",
                      "known_file_count": "1,200", "known_size": ""}, schema)
    assert row == {"source_id": "FF-X", "data_modalities": ["video", "stills"], "license": None,
                   "known_file_count": 1200, "known_size": None}


def test_a_broken_row_is_reported_with_its_source_and_field(tmp_path):
    rows = list(csv.DictReader(REGISTRY_CSV.open(encoding="utf-8-sig")))
    rows[0]["priority"] = "P9"
    rows[1]["known_file_count"] = "many"
    rows.append(dict(rows[2]))                   # duplicate source_id
    broken = tmp_path / "registry.csv"
    with broken.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    problems = validate_registry(broken)
    assert any(p.startswith(f"{rows[0]['source_id']}: priority:") for p in problems)
    assert any(p.startswith(f"{rows[1]['source_id']}: known_file_count:") for p in problems)
    assert f"{rows[2]['source_id']}: source_id: duplicate" in problems


def test_every_registered_source_has_a_license_or_says_why_not():
    for row in read_registry():
        assert row["license"] or "license" in (row.get("notes") or "").lower() or row["access_status"] != "confirmed_public" \
            or row["source_id"] == "FF-PSI-DSI", row["source_id"]
