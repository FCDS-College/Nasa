"""Suppression Advisor API (contract 0.8.0, ADR-014) over the committed PSI tables."""
import pytest
from sqlalchemy import or_

from api_contract import assert_contract_component
from flame_api import investigations
from flame_api.ingest import ingest_file
from flame_api.models import FileRecord
from flame_api.seed import seed_files, seed_sources


@pytest.fixture
def ingested(session_factory):
    """Same ingestion as test_fire_safety_api.py: the FLEX rows feed the CO₂ flight-data estimate."""
    investigations.reset_cache()
    session = session_factory()
    seed_sources(session)
    session.commit()
    seed_files(session)
    session.commit()
    files = session.query(FileRecord).filter(or_(
        FileRecord.original_filename.like("%Experimental table%"), FileRecord.original_filename.like("%metadata%.zip"),
    )).all()
    for record in files:
        if record.source_id != "FF-PSI-DSI":
            ingest_file(session, record)
    session.commit()
    session.close()
    yield session_factory
    investigations.reset_cache()


def test_suppression_advice_for_a_flex_fuel_carries_the_flight_estimate(client, ingested):
    body = client.get("/api/insights/suppression-advice", params={"fire_type": "heptane"}).json()
    assert_contract_component(body, "SuppressionAdviceResponse")
    co2 = body["agents"]["co2"]
    assert co2["flex_estimate"]["claim_class"] == "estimated"
    assert 0 <= co2["flex_estimate"]["p_extinction"] <= 1
    assert len(co2["flex_estimate"]["similar_tests"]) == 5
    assert all(t["end_state_evidence_id"] for t in co2["flex_estimate"]["similar_tests"])
    assert body["agents"]["water_mist"]["flex_estimate"] is None          # water is not a FLEX input
    assert 0 < body["crossover_delivery_fraction"]["value"] < 1
    assert body["disclaimer"] and body["scope"]


def test_suppression_advice_vetoes_co2_in_a_small_cabin(client, ingested):
    body = client.get("/api/insights/suppression-advice", params={"cabin_volume_m3": 31}).json()
    assert_contract_component(body, "SuppressionAdviceResponse")
    assert body["agents"]["co2"]["hazard_level"] == "red"
    assert body["recommended_agent"] == "water_mist" and body["basis"] == "hazard_veto"


@pytest.mark.parametrize("fire_type", ["other_liquid", "electrical_battery", "solid"])
def test_suppression_advice_non_flex_fire_types_never_carry_probabilities(client, ingested, fire_type):
    body = client.get("/api/insights/suppression-advice", params={"fire_type": fire_type}).json()
    assert_contract_component(body, "SuppressionAdviceResponse")
    for agent in body["agents"].values():
        assert agent["flex_estimate"] is None and agent["thermal_estimate"] is None


def test_suppression_advice_rejects_bad_input(client, ingested):
    assert client.get("/api/insights/suppression-advice", params={"o2_fraction": 0.6, "co2_fraction": 0.5}).status_code == 400
    assert client.get("/api/insights/suppression-advice", params={"fire_type": "plasma"}).status_code in (400, 422)
    assert client.get("/api/insights/suppression-advice", params={"delivery_fraction": 1.5}).status_code in (400, 422)
