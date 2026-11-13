"""Historical scenarios (ADR-013): data files validated against their schema, and the scenario-level coverage verdict."""
import csv
import json
from pathlib import Path

import jsonschema
import pytest

from ai.fire_safety import investigations as analytics
from ai.fire_safety import scenarios
from ai.fire_safety.investigations import Canonical, Condition
from ai.fire_safety.investigations import TestRow as Row

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((scenarios.HISTORICAL_DIR / "historical_scenario.schema.json").read_text(encoding="utf-8"))
FILES = sorted(p for p in scenarios.HISTORICAL_DIR.glob("*.json") if not p.name.endswith(".schema.json"))


def _letters(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum() or ch in ".%")


def _registered_reports() -> set[str]:
    with (ROOT / "datasets" / "registry" / "source_registry.csv").open(encoding="utf-8-sig", newline="") as handle:
        return {r["source_id"] for r in csv.DictReader(handle) if r["source_type"] == "technical_report"}


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_every_historical_scenario_matches_the_schema(path):
    jsonschema.validate(json.loads(path.read_text(encoding="utf-8")), SCHEMA)


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_every_cited_page_exists_in_a_registered_committed_report(path):
    """A statement shown to a user must point at a real page of a report we hold."""
    import pymupdf

    data = json.loads(path.read_text(encoding="utf-8"))
    cited = list(data["lesson_sources"]) + list(data["alternative"]["sources"]) + [s for e in data["timeline"] for s in e["sources"]]
    registered = _registered_reports()
    for source in cited:
        assert source["source_id"] in registered, source
        pdf = ROOT / "docs" / "research" / f"{source['source_id'].removeprefix('FF-NTRS-')}.pdf"
        with pymupdf.open(pdf) as doc:
            assert 1 <= source["page"] <= doc.page_count, source
            if source.get("quote"):   # verbatim, ignoring layout: line-break hyphens, OCR underscores, spacing, case
                assert _letters(source["quote"]) in _letters(doc[source["page"] - 1].get_text()), source


def test_apollo1_is_loaded_as_a_historical_earth_gravity_scenario():
    apollo = scenarios.BY_ID["apollo1_pad_1967"]
    assert (apollo.o2_fraction, apollo.gravity, apollo.kind, apollo.basis) == (1.0, "earth", "historical", "historical")
    assert apollo.pressure_kpa == pytest.approx(16.7 * scenarios.KPA_PER_PSIA, abs=0.05)   # 16.7 psia, the Board's figure
    assert scenarios.HISTORIES["apollo1_pad_1967"].alternative["scenario_id"] == "orion_max_o2"
    # mission scenarios keep their microgravity default and their order
    assert [s.scenario_id for s in scenarios.MISSION_SCENARIOS] == ["iss_nominal", "pre_eva", "orion_max_o2", "lunar_lander_max_o2"]
    assert all(s.gravity == "microgravity" and s.kind == "mission" for s in scenarios.MISSION_SCENARIOS)


def test_a_broken_historical_file_is_rejected_at_load(tmp_path):
    good = json.loads(FILES[0].read_text(encoding="utf-8"))
    bad = {**good, "timeline": [{**good["timeline"][0], "sources": []}]}
    (tmp_path / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="timeline"):
        scenarios.load_historical(tmp_path)
    (tmp_path / "bad.json").write_text(json.dumps({**good, "gravity": "venus"}), encoding="utf-8")
    with pytest.raises(ValueError, match="gravity"):
        scenarios.load_historical(tmp_path)


def test_custom_atmospheres_take_a_gravity():
    assert scenarios.custom(0.21, 101.3).gravity == "microgravity"
    assert scenarios.custom(0.21, 101.3, "lunar").gravity == "lunar"
    with pytest.raises(ValueError):
        scenarios.custom(0.21, 101.3, "jovian")


# ------------------------------------------------------------------------------------------- coverage verdict

def _flex(test_id: str, o2: float, kpa: float, end: str = "Extinction") -> Canonical:
    mmhg = kpa / analytics.KPA_PER_MMHG
    conditions = {"o_initial_ambient_composition_mole_fraction": Condition(o2, None, None, f"E-{test_id}-o2"),
                  "ambient_pressure_mmhg": Condition(mmhg, None, None, f"E-{test_id}-p"),
                  "test_end": Condition(None, end, None, f"E-{test_id}-end")}
    return analytics.canonical(Row("FF-PSI-69", f"X-{test_id}", test_id, "Heptane", conditions))


FLIGHT = {"FF-PSI-69": [_flex(f"T{i}", 0.21, 101.3) for i in range(6)] + [_flex("HIGH", 0.34, 72.0, "Disruption")]}


def test_an_atmosphere_nobody_flew_gets_verdict_none_with_the_nearest_test_and_the_gap():
    result = analytics.coverage(FLIGHT, scenarios.BY_ID["apollo1_pad_1967"])
    assert result["verdict"] == "none"
    assert result["headline"] == "None of the 7 flight tests cover this atmosphere."
    assert result["nearest_test"]["test_id"] == "HIGH"
    assert result["nearest_test"]["evidence"] == ["E-HIGH-o2", "E-HIGH-p"]
    assert result["gap"]["o2_ratio"] == pytest.approx(1.0 / 0.34, rel=1e-3)
    assert result["gravity"] == {"scenario": "earth", "flight_tests": ["microgravity"], "covered": False}
    assert any("1 g" in r for r in result["reasons"]) and any("2.9× the highest O₂" in r for r in result["reasons"])


def test_gravity_alone_makes_an_otherwise_covered_atmosphere_uncovered():
    assert analytics.coverage(FLIGHT, scenarios.custom(0.21, 101.3))["verdict"] == "covered"
    lunar_air = analytics.coverage(FLIGHT, scenarios.custom(0.21, 101.3, "lunar"))
    assert lunar_air["verdict"] == "none" and lunar_air["neighbourhood_tests"] == 6
    assert lunar_air["reasons"] == ["every flight test here was flown in microgravity; this scenario is at lunar gravity"]


def test_few_neighbours_or_an_atmosphere_outside_the_flown_range_is_partial():
    few = analytics.coverage({"FF-PSI-69": FLIGHT["FF-PSI-69"][-2:]}, scenarios.custom(0.21, 101.3))
    assert few["verdict"] == "partial" and few["neighbourhood_tests"] == 1
    edge = analytics.coverage(FLIGHT, scenarios.custom(0.21, 85.0))   # inside the flown 72-101 kPa, 6 neighbours within 25%
    assert edge["verdict"] == "covered"
    below = analytics.coverage(FLIGHT, scenarios.custom(0.34, 60.0))   # within 25% of the 72 kPa test, below every flown pressure
    assert below["verdict"] == "partial" and "outside the range that was flown" in below["headline"]
