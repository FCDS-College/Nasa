"""Fire-safety dashboard API (contract 0.5.0) over the committed PSI tables and ISA-Tab metadata."""
import json

import numpy as np
import pytest
from sqlalchemy import or_

from api_contract import assert_contract_component
from flame_api import investigations
from flame_api.ingest import ingest_file
from flame_api.models import FileRecord
from flame_api.seed import seed_files, seed_sources

from ai.fire_safety import flex
from ai.fire_safety import model as outcome_model


@pytest.fixture
def ingested(session_factory):
    investigations.reset_cache()
    session = session_factory()
    seed_sources(session)
    session.commit()   # seed_files looks sources up; the test session does not autoflush
    seed_files(session)
    session.commit()
    files = session.query(FileRecord).filter(or_(
        FileRecord.original_filename.like("%Experimental table%"), FileRecord.original_filename.like("%metadata%.zip"),
    )).all()
    assert len(files) == 8
    for record in files:
        if record.source_id != "FF-PSI-DSI":
            ingest_file(session, record)
    session.commit()
    session.close()
    yield session_factory
    investigations.reset_cache()


def test_investigations_are_ranked_for_the_lunar_lander_atmosphere(client, ingested):
    response = client.get("/api/investigations", params={"scenario": "lunar_lander_max_o2"})
    assert response.status_code == 200
    body = response.json()
    assert_contract_component(body, "InvestigationListResponse")
    items = {i["acronym"]: i for i in body["items"]}
    assert body["totals"]["flight_tests"] == 840
    assert items["FLEX"]["rank"] == 1 and items["FLEX"]["data"]["tests"] == 274
    # BASS-II never flew above 22.2% O2, so it cannot speak to a 34% O2 cabin.
    assert items["BASS-II"]["data"]["o2_fraction"]["max"] == pytest.approx(0.222)
    assert items["BASS-II"]["relevance"]["components"]["oxygen_match"] < 0.2
    assert items["BASS-II"]["relevance"]["not_recorded"] == ["pressure"]
    # Investigations without ingested data are listed but not ranked.
    assert items["ACME-CLD"]["status"] == "metadata_only" and items["ACME-CLD"]["rank"] is None
    assert body["not_acquired"][0]["acronym"] == "SAME"
    # NASA's own objective text, cited to its evidence row.
    objective = items["FLEX"]["objective"]
    assert "flammability limits" in objective["text"]
    assert client.get(f"/api/evidence/{objective['evidence_id']}").status_code == 200


def test_ranking_follows_the_atmosphere(client, ingested):
    iss = {i["acronym"]: i["relevance"]["score"] for i in client.get("/api/investigations").json()["items"] if i["relevance"]}
    lunar = {i["acronym"]: i["relevance"]["score"]
             for i in client.get("/api/investigations", params={"scenario": "lunar_lander_max_o2"}).json()["items"] if i["relevance"]}
    assert iss["BASS-II"] > lunar["BASS-II"]
    custom = client.get("/api/investigations", params={"o2_fraction": 0.25, "pressure_kpa": 80}).json()
    assert custom["scenario"]["basis"] == "user"


def test_bad_scenarios_are_rejected(client, ingested):
    assert client.get("/api/investigations", params={"scenario": "mars_base"}).json()["error"]["code"] == "VALIDATION_ERROR"
    assert client.get("/api/investigations", params={"o2_fraction": 0.3}).status_code == 400
    missing = client.get("/api/investigations/FF-PSI-999")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "INVESTIGATION_NOT_FOUND"


def test_investigation_detail_has_nasa_summary_sections_and_insights(client, ingested):
    body = client.get("/api/investigations/FF-PSI-69", params={"scenario": "pre_eva"}).json()
    assert_contract_component(body, "InvestigationResponse")
    inv = body["investigation"]
    assert [s["heading"] for s in inv["summary_sections"]] == ["Objective", "Hypothesis", "Approach", "Research impacts"]
    assert any("ntrs.nasa.gov" in p for p in inv["publications"])
    assert {i["insight_id"] for i in inv["insights"]} >= {"flex_oxygen_vs_extinction", "scenario_flex_neighbours"}


def test_insights_are_computed_from_rows_and_cite_them(client, ingested):
    body = client.get("/api/insights", params={"scenario": "pre_eva"}).json()
    assert_contract_component(body, "InsightListResponse")
    by_id = {i["insight_id"]: i for i in body["items"]}
    oxygen = by_id["flex_oxygen_vs_extinction"]
    assert oxygen["numbers"]["low_o2"]["n"] == 48 and oxygen["numbers"]["low_o2"]["extinction_share"] > 0.9
    assert oxygen["numbers"]["high_o2"]["extinction_share"] < 0.2
    for item in oxygen["evidence"]:
        evidence = client.get(f"/api/evidence/{item['evidence_id']}").json()["evidence"]
        assert evidence["experiment_id"] == item["experiment_id"]
        assert evidence["excerpt"].startswith("Test end: ")
    assert by_id["bass_solid_oxygen_coverage"]["kind"] == "coverage_gap"
    assert "microgravity" in by_id["coverage_gaps"]["statement"]
    assert by_id["flex_model_scenario_estimate"]["kind"] == "model_estimate"


def test_flex_outcome_estimate_inside_and_outside_the_flight_envelope(client, ingested):
    inside = client.get("/api/insights/flex-outcome", params={"fuel": "Heptane", "o2_fraction": 0.21, "pressure_kpa": 101.3}).json()
    assert_contract_component(inside, "FlexOutcomeResponse")
    assert inside["applicability"]["in_domain"] is True
    assert sum(inside["probabilities"].values()) == pytest.approx(1, abs=1e-3)
    assert len(inside["similar_tests"]) == 8 and all(t["end_state_evidence_id"] for t in inside["similar_tests"])
    assert inside["model"]["primary_estimate"]["macro_f1"]["mean"] > inside["model"]["primary_estimate"]["majority_baseline_macro_f1"]["mean"]
    outside = client.get("/api/insights/flex-outcome", params={"o2_fraction": 0.5, "pressure_kpa": 30}).json()
    assert outside["probabilities"] is None and outside["predicted_end_state"] is None
    assert len(outside["applicability"]["reasons"]) >= 2
    assert client.get("/api/insights/flex-outcome", params={"o2_fraction": 0.6, "he_fraction": 0.5}).status_code == 400


def test_lower_oxygen_raises_the_estimated_extinction_probability(client, ingested):
    sweep = client.get("/api/insights/flex-outcome", params={"fuel": "Methanol", "pressure_kpa": 101.3}).json()["o2_sweep"]
    p = [pt["probabilities"]["Extinction"] for pt in sweep if pt["probabilities"]]
    assert len(p) >= 4 and p[0] > p[-1]


def test_api_features_match_training_features_for_every_flex_test(ingested):
    """The API rebuilds features from ingested rows; they must equal what the model was trained on."""
    session = ingested()
    _, by_source, _, _, _ = investigations._load(session)
    model = outcome_model.load()
    def key(test_id, f):
        return (test_id,) + tuple(round(f[name], 9) for name in flex.FEATURES)

    from_db = sorted(key(t.row.test_id, f) for t, f, _ in investigations._flex_training(by_source["FF-PSI-69"], model))
    from_csv = sorted(key(t.test_id, t.features) for t in flex.load_table() if t.features and t.outcome)
    # 261 usable rows; FLEX identifier 193F001 is published twice with different conditions, so compare multisets.
    assert len(from_db) == 261 and from_db == from_csv
    session.close()


def test_committed_artefact_matches_its_evaluation_report_and_training_table():
    artefact = json.loads(outcome_model.ARTIFACT.read_text(encoding="utf-8"))
    report = json.loads(outcome_model.ARTIFACT.with_name("flex_outcome_evaluation.json").read_text(encoding="utf-8"))
    assert artefact["model_version"] == report["model_version"]
    assert artefact["training_data"]["sha256"] == report["training_data"]["sha256"]
    import hashlib
    assert hashlib.sha256(flex.FLEX_TABLE.read_bytes()).hexdigest() == artefact["training_data"]["sha256"]
    assert report["numpy_vs_sklearn_max_abs_probability_difference"] < 1e-9
    model = outcome_model.load()
    probabilities = model.probabilities({"o2": 0.21, "pressure_atm": 1.0, "ppo2_atm": 0.21, "co2": 0.0, "he": 0.0, "d0_mm": 3.0,
                                         "heptane": 1.0})
    assert np.isclose(probabilities.sum(), 1.0)


def test_review_fixes_low_oxygen_scenario_and_evidence_semantics(client, ingested):
    """Code-review regressions (2026-11-07)."""
    # A scenario below BASS-II's lowest O2 is a coverage gap, not "inside the range".
    low = {i["insight_id"]: i for i in client.get("/api/insights", params={"o2_fraction": 0.10, "pressure_kpa": 101.3}).json()["items"]}
    assert low["bass_solid_oxygen_coverage"]["kind"] == "coverage_gap"
    # Shares of outcomes cite outcome cells, not the pressure cells.
    reduced = {i["insight_id"]: i for i in client.get("/api/insights").json()["items"]}["flex_reduced_pressure"]
    for item in reduced["evidence"]:
        assert client.get(f"/api/evidence/{item['evidence_id']}").json()["evidence"]["excerpt"].startswith("Test end: ")


def test_a_test_without_valid_pressure_is_never_a_pressure_neighbour():
    from ai.fire_safety import investigations as analytics
    from ai.fire_safety.scenarios import BY_ID

    def flex_test(test_id, o2, mmhg):
        conditions = {"o_initial_ambient_composition_mole_fraction": analytics.Condition(o2, None, o2, "e1"),
                      "ambient_pressure_mmhg": analytics.Condition(mmhg, None, None, "e2")}
        return analytics.canonical(analytics.TestRow("FF-PSI-69", test_id, test_id, "Heptane", conditions))

    tests = [flex_test("ok", 0.21, 760.0), flex_test("C11M201", 0.21, 0.0)]
    assert tests[1].pressure_kpa is None and "pressure_not_physical" in tests[1].flags
    assert [t.row.test_id for t in analytics.neighbours(tests, BY_ID["iss_nominal"])] == ["ok"]


def test_an_unrecorded_diluent_is_missing_not_zero():
    features, flags = flex.features_from_values({"o2": 0.21, "pressure_mmhg": 760, "d0_mm": 3.0, "co2": None, "he": 0.0}, "Heptane")
    assert features is None and "diluent_not_recorded" in flags


# ------------------------------------------------------------------ Apollo 1 historical scenario (contract 0.7.0, ADR-013)

def test_apollo1_pure_oxygen_atmosphere_is_covered_by_no_flight_test(client, ingested):
    body = client.get("/api/investigations", params={"scenario": "apollo1_pad_1967"}).json()
    assert_contract_component(body, "InvestigationListResponse")
    assert body["scenario"]["gravity"] == "earth" and body["scenario"]["kind"] == "historical"
    coverage = body["coverage"]
    assert coverage["verdict"] == "none"
    assert coverage["headline"] == "None of the 840 flight tests cover this atmosphere."
    assert coverage["neighbourhood_tests"] == 0 and coverage["gravity"]["covered"] is False
    # The closest real test is the richest FLEX oxygen (34%), and it is cited to its cells.
    nearest = coverage["nearest_test"]
    assert nearest["investigation_id"] == "FF-PSI-69" and nearest["o2_fraction"] == pytest.approx(0.34)
    for evidence_id in nearest["evidence"]:
        assert client.get(f"/api/evidence/{evidence_id}").status_code == 200
    assert coverage["gap"]["o2_ratio"] == pytest.approx(1 / 0.34, rel=1e-3)
    assert any("2.9× the highest O₂ flown" in r for r in coverage["reasons"])
    # The relevance ranking is unchanged (ADR-011); the verdict is what says "no coverage".
    assert [i["acronym"] for i in body["items"] if i["rank"]][0] == "FLEX"


def test_apollo1_gets_no_model_estimate_and_gravity_is_a_refusal_reason(client, ingested):
    items = {i["insight_id"]: i for i in client.get("/api/insights", params={"scenario": "apollo1_pad_1967"}).json()["items"]}
    estimate = items["flex_model_scenario_estimate"]
    assert estimate["kind"] == "coverage_gap"
    assert all(n["probabilities"] is None and not n["in_domain"] for n in estimate["numbers"].values())
    assert "1 g (Earth)" in estimate["statement"] and "O₂ mole fraction 1 is outside" in estimate["statement"]
    # ISS air at 1 g is inside every range, yet still refused: no flight test was flown in Earth gravity.
    earth_air = {i["insight_id"]: i for i in client.get(
        "/api/insights", params={"o2_fraction": 0.21, "pressure_kpa": 101.3, "gravity": "earth"}).json()["items"]}
    assert earth_air["flex_model_scenario_estimate"]["kind"] == "coverage_gap"
    assert client.get("/api/insights", params={"scenario": "iss_nominal", "gravity": "earth"}).status_code == 400


def test_the_data_covered_alternative_to_apollo1_is_orion_and_it_gets_an_estimate(client, ingested):
    history = client.get("/api/scenarios/apollo1_pad_1967/history").json()
    assert_contract_component(history, "ScenarioHistoryResponse")
    alternative = history["alternative"]["scenario"]["scenario_id"]
    assert alternative == "orion_max_o2" and "not mean safe" in history["alternative"]["rationale"]
    body = client.get("/api/investigations", params={"scenario": alternative}).json()
    assert body["coverage"]["verdict"] == "covered" and body["coverage"]["neighbourhood_tests"] >= 5
    estimate = {i["insight_id"]: i for i in client.get("/api/insights", params={"scenario": alternative}).json()["items"]}
    assert estimate["flex_model_scenario_estimate"]["kind"] == "model_estimate"


def test_apollo1_history_is_page_cited_and_only_historical_scenarios_have_one(client, ingested):
    history = client.get("/api/scenarios/apollo1_pad_1967/history").json()
    assert history["year"] == 1967 and history["claim_class"] == "cited_history"
    assert len(history["timeline"]) >= 6
    for event in history["timeline"]:
        assert event["sources"] and all(s["source_id"].startswith("FF-NTRS-") and s["page"] >= 1 for s in event["sources"])
        assert all(s["access_url"] and s["access_url"].startswith("https://ntrs.nasa.gov/citations/") for s in event["sources"])
    board = [s for s in history["lesson_sources"] if s["source_id"] == "FF-NTRS-19930078717"][0]
    assert board["page"] == 189 and "extremely hazardous" in board["quote"]
    missing = client.get("/api/scenarios/iss_nominal/history")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "SCENARIO_HISTORY_NOT_FOUND"
    assert client.get("/api/scenarios/Not-An-Id/history").status_code == 400


def test_the_oxygen_sweep_reaches_a_requested_atmosphere_outside_the_flight_data(client, ingested):
    sweep = client.get("/api/insights/flex-outcome", params={"o2_fraction": 1.0, "pressure_kpa": 115.14}).json()["o2_sweep"]
    assert sweep[-1]["o2_fraction"] == pytest.approx(1.0)
    beyond = [p for p in sweep if p["o2_fraction"] > 0.34 + 1e-9]
    assert len(beyond) == 6 and all(not p["in_domain"] and p["probabilities"] is None for p in beyond)
    # Inside the flight data the sweep is unchanged: the same 12 points as before.
    default = client.get("/api/insights/flex-outcome").json()["o2_sweep"]
    assert len(default) == 12 and default[0]["o2_fraction"] == pytest.approx(0.12) and default[-1]["o2_fraction"] == pytest.approx(0.34)


def test_mission_scenarios_keep_their_verdicts(client, ingested):
    verdicts = {sid: client.get("/api/investigations", params={"scenario": sid}).json()["coverage"]["verdict"]
                for sid in ("iss_nominal", "pre_eva", "orion_max_o2", "lunar_lander_max_o2")}
    assert verdicts == {"iss_nominal": "covered", "pre_eva": "covered", "orion_max_o2": "covered",
                        "lunar_lander_max_o2": "partial"}
