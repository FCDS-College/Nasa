def test_dashboard_counts_are_database_counts(client):
    response = client.get("/api/dashboard/counts")

    assert response.status_code == 200
    assert response.json()["documents"] == 0
    assert response.json()["experiments"] == 0
    assert response.json()["analyses"] == 0
    assert response.json()["meta"]["request_id"] == response.headers["X-Request-ID"]
    from api_contract import assert_contract_component
    assert_contract_component(response.json(), "DashboardCountsResponse")


def test_empty_search_is_a_successful_lexical_search(client):
    response = client.get("/api/search", params={"q": "combustion"})
    body = response.json()

    assert response.status_code == 200
    assert body["results"] == []
    assert body["filters"]["domain"] == "combustion"
    assert body["retrieval"] == {
        "mode": "lexical",
        "knowledge_version": None,
        "index_version": None,
        "searched_but_empty": True,
        "stack_version": "flame-search-2.0.0",
        "query_rewrite": {"rewritten": body["query"], "changed": False, "rules_applied": [], "rewriter_version": "1.0.0",
                          "used_for": ["semantic"]},
        "reranking": {"status": "disabled", "model": None, "depth": None},
    }
    from api_contract import assert_contract_component
    assert_contract_component(body, "SearchResponse")


def test_unknown_resources_return_contract_errors(client):
    for path, code in (
        ("/api/documents/01J9Z3M2A7D4F6H8K0N2Q4S6T8", "DOCUMENT_NOT_FOUND"),
        ("/api/experiments/01J9Z3P7C2E4G6J8M0Q2S4V6X8", "EXPERIMENT_NOT_FOUND"),
        ("/api/evidence/01J9Z3N5B8C1E3G5J7M9P1R3T5", "EVIDENCE_NOT_FOUND"),
    ):
        response = client.get(path)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == code
        assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_openapi_endpoint_is_the_checked_in_contract(client):
    from pathlib import Path
    import json

    spec_path = Path(__file__).resolve().parents[3] / "docs" / "api" / "openapi.json"
    contract = json.loads(spec_path.read_text(encoding="utf-8"))
    assert client.get("/api/openapi.json").json() == contract
    for path_item in contract["paths"].values():
        for method, operation in path_item.items():
            if method in {"get", "post", "put", "patch", "delete"}:
                assert operation["security"] == [{"bearerAuth": []}]
                assert "401" in operation["responses"]


def test_api_docs_and_openapi_metadata_are_public(client):
    headers = {"Authorization": ""}

    assert client.get("/api/docs", headers=headers).status_code == 200
    assert client.get("/api/openapi.json", headers=headers).status_code == 200


def test_search_excludes_dsi_by_default_and_returns_contract_experiment_shape(client, session_factory):

    from datetime import UTC, datetime

    from flame_api.models import ExperimentRecord, SourceRecord

    ingested_at = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    with session_factory() as session:
        session.add_all([
            SourceRecord(source_id="FF-PSI-25", title="BASS-II", short_name="BASS-II", repository="NASA PSI", persistent_identifier="doi:10.60555/4qc4-de67", license="CC0-1.0", access_url="https://psi.nasa.gov/", domain="combustion"),
            SourceRecord(source_id="FF-PSI-DSI", title="DSI", short_name="DSI", repository="NASA PSI", persistent_identifier=None, license="CC0-1.0", access_url="https://psi.nasa.gov/", domain="non_combustion"),
        ])
        session.flush()
        session.add_all([
            ExperimentRecord(experiment_id="01J9Z3P7C2E4G6J8M0Q2S4V6X8", source_id="FF-PSI-25", test_id="FLEX-1", investigation="FLEX", gravity_regime="microgravity", fuel_or_material="Heptane", table_file_id=None, searchable_text="FLEX-1 heptane droplet extinction", payload={}, ingested_at=ingested_at, conditions=[]),
            ExperimentRecord(experiment_id="01J9Z3P7C2E4G6J8M0Q2S4V6X9", source_id="FF-PSI-DSI", test_id="DSI-1", investigation="DSI", gravity_regime="microgravity", fuel_or_material="Heptane", table_file_id=None, searchable_text="DSI-1 heptane", payload={}, ingested_at=ingested_at, conditions=[]),
        ])
        session.commit()

    default_domain = client.get("/api/search", params={"q": "heptane", "type": "experiment", "page_size": 1})
    all_domains = client.get("/api/search", params={"q": "heptane", "type": "experiment", "domain": "all"})
    body = default_domain.json()

    assert default_domain.status_code == 200
    assert body["pagination"]["total_items"] == 1
    assert body["results"][0]["source"]["source_id"] == "FF-PSI-25"
    assert body["results"][0]["experiment"] == {
        "test_id": "FLEX-1",
        "gravity_regime": "microgravity",
        "fuel_or_material": "Heptane",
    }
    assert body["results"][0]["ingested_at"] == "2026-10-01T12:00:00Z"
    assert all_domains.json()["pagination"]["total_items"] == 2