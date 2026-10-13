"""M6: GET /api/documents and GET /api/experiments (filters, pagination, contract shape)."""
from datetime import UTC, datetime

import pytest

from api_contract import assert_contract_component
from flame_api.models import DocumentRecord, ExperimentCondition, ExperimentRecord, FileRecord, SourceRecord


@pytest.fixture
def records(session_factory):
    now = datetime.now(UTC)
    with session_factory() as session:
        for source_id in ("FF-PSI-69", "FF-NTRS-20000034017"):
            session.add(SourceRecord(source_id=source_id, title=source_id, repository="NASA PSI", access_url="https://example.org"))
            session.add(FileRecord(file_id=f"f-{source_id}", source_id=source_id, sha256="0" * 64, original_filename="a.pdf",
                                   media_type="application/pdf", size_bytes=1, retrieved_at=now))
        for index, (source_id, title, kind) in enumerate([
            ("FF-PSI-69", "FLEX Final Report", "technical_report"),
            ("FF-PSI-69", "FLEX data dictionary", "data_dictionary"),
            ("FF-NTRS-20000034017", "Fire-Resistant Materials", "technical_report"),
        ]):
            session.add(DocumentRecord(document_id=f"01J9Z3M2A7D4F6H8K0N2Q4S6T{index}", source_id=source_id, file_id=f"f-{source_id}",
                                       title=title, document_type=kind, ingested_at=now))
        for index, (fuel, gravity) in enumerate([("n-heptane", "microgravity"), ("methanol", "microgravity"), ("n-heptane", "normal")]):
            experiment_id = f"01J9Z3N1W8X2Y4Z6A8C0E2G4J{index}"
            session.add(ExperimentRecord(experiment_id=experiment_id, source_id="FF-PSI-69", test_id=f"T{index}",
                                         investigation="FLEX", gravity_regime=gravity, fuel_or_material=fuel))
            for c in range(index + 1):
                session.add(ExperimentCondition(condition_id=f"01J9Z3P0000000000000000{index}{c:02d}", experiment_id=experiment_id,
                                                variable="pressure", origin="reported", evidence_id="E" * 26))
        session.commit()


def test_documents_are_listed_with_filters_and_pagination(client, records):
    body = client.get("/api/documents", params={"page_size": 2}).json()
    assert [d["title"] for d in body["items"]] == ["Fire-Resistant Materials", "FLEX data dictionary"]
    assert body["pagination"] == {"page": 1, "page_size": 2, "total_items": 3, "total_pages": 2}
    assert_contract_component(body, "DocumentListResponse")

    filtered = client.get("/api/documents", params={"source_id": "FF-PSI-69", "document_type": "technical_report"}).json()
    assert [d["title"] for d in filtered["items"]] == ["FLEX Final Report"]
    assert client.get("/api/documents", params={"q": "materials"}).json()["pagination"]["total_items"] == 1


def test_experiments_are_listed_with_filters_and_condition_counts(client, records):
    body = client.get("/api/experiments").json()
    assert [(e["test_id"], e["condition_count"]) for e in body["items"]] == [("T0", 1), ("T1", 2), ("T2", 3)]
    assert_contract_component(body, "ExperimentListResponse")

    micro = client.get("/api/experiments", params={"gravity_regime": "microgravity", "fuel_or_material": "HEPTANE"}).json()
    assert [e["test_id"] for e in micro["items"]] == ["T0"]


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 101}, {"page_size": 0}])
def test_list_pagination_is_validated(client, params):
    for path in ("/api/documents", "/api/experiments"):
        response = client.get(path, params=params)
        assert response.status_code == 400 and response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_endpoints_need_the_read_token(client):
    assert client.get("/api/documents", headers={"Authorization": ""}).status_code == 401
