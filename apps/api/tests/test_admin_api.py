"""P2-8: audited admin data operations (ADMIN_DATA_OPERATIONS.md procedures 3, 4, 5, 7)."""
import json
from datetime import UTC, datetime

import pytest

from ai.providers import http as provider_http
from api_contract import CONTRACT_PATH, assert_contract_component
from flame_api import main
from flame_api.models import (
    AuditEvent, DocumentChunk, DocumentRecord, EvidenceRecord, ExperimentCondition, ExperimentRecord, FileRecord,
    IngestionRun, SourceRecord,
)

READ_TOKEN = "test-read-token-0123456789abcdef0123456789"
WRITE_TOKEN = "test-write-token-0123456789abcdef0123456789"
WRITE = {"Authorization": f"Bearer {WRITE_TOKEN}"}
QUARANTINED = "sha256:aaaaaaaaaaaaaaaa"
ACTIVE = "sha256:bbbbbbbbbbbbbbbb"
DOCUMENT_ID = "01J9Z3M2A7D4F6H8K0N2Q4S6T8"
KEPT_EVIDENCE = "01J9Z3N5B8C1E3G5J7M9P1R3T5"
REJECTED_EVIDENCE = "01J9Z3N5B8C1E3G5J7M9P1R3T6"
EXPERIMENT_ID = "01J9Z3P7C2E4G6J8M0Q2S4V6X8"
CONDITION_EVIDENCE = ["01J9Z3N5B8C1E3G5J7M9P1R3T7", "01J9Z3N5B8C1E3G5J7M9P1R3T8"]


def _evidence(evidence_id, *, kind="document_passage", experiment_id=None, document_id=DOCUMENT_ID, file_id=ACTIVE):
    return EvidenceRecord(
        evidence_id=evidence_id, source_id="FF-PSI-25", file_id=file_id, document_id=document_id, experiment_id=experiment_id,
        kind=kind, origin="source_evidence", excerpt="excerpt", locator=None,
        payload={"review_status": "machine_extracted", "extraction_method": "verbatim_text"}, created_at=datetime.now(UTC),
    )


@pytest.fixture
def corpus(session_factory):
    now = datetime.now(UTC)
    with session_factory() as session:
        session.add(SourceRecord(source_id="FF-PSI-25", title="BASS-II", short_name="BASS-II", repository="NASA PSI",
                                 access_url="https://psi.nasa.gov/", domain="combustion"))
        session.flush()
        session.add_all([
            FileRecord(file_id=QUARANTINED, source_id="FF-PSI-25", sha256="a" * 64, original_filename="bad.pdf",
                       media_type="application/pdf", size_bytes=10, retrieved_at=now, status="quarantined",
                       quarantine_reason="checksum_mismatch"),
            FileRecord(file_id=ACTIVE, source_id="FF-PSI-25", sha256="b" * 64, original_filename="good.pdf",
                       media_type="application/pdf", size_bytes=10, retrieved_at=now),
        ])
        session.flush()
        session.add(IngestionRun(run_id="01J9Z3R1A2B3C4D5E6F7G8H9J0", source_id="FF-PSI-25", file_id=QUARANTINED,
                                 transformation_id="quarantine", input_sha256="a" * 64, started_at=now, finished_at=now,
                                 counts={"reason": "checksum_mismatch"}))
        session.add(DocumentRecord(document_id=DOCUMENT_ID, source_id="FF-PSI-25", file_id=ACTIVE, title="Cool flames", ingested_at=now))
        session.flush()
        session.add_all([
            _evidence(KEPT_EVIDENCE), _evidence(REJECTED_EVIDENCE),
            DocumentChunk(chunk_id="chunk-kept", document_id=DOCUMENT_ID, source_id="FF-PSI-25", file_id=ACTIVE,
                          evidence_id=KEPT_EVIDENCE, page=1, text="Heptane droplet cool flame extinction.", ingested_at=now),
            DocumentChunk(chunk_id="chunk-rejected", document_id=DOCUMENT_ID, source_id="FF-PSI-25", file_id=ACTIVE,
                          evidence_id=REJECTED_EVIDENCE, page=2, text="Heptane garbled OCR table.", ingested_at=now),
            ExperimentRecord(experiment_id=EXPERIMENT_ID, source_id="FF-PSI-25", test_id="FLEX-1", investigation="FLEX",
                             gravity_regime="microgravity", fuel_or_material="Heptane", searchable_text="FLEX-1 heptane", payload={}),
        ])
        session.flush()
        session.add_all([
            *(_evidence(e, kind="experiment_condition", experiment_id=EXPERIMENT_ID, document_id=None) for e in CONDITION_EVIDENCE),
            *(ExperimentCondition(condition_id=f"01J9Z3S{i}A2B3C4D5E6F7G8H9J0", experiment_id=EXPERIMENT_ID, variable=f"v{i}",
                                  value_numeric=1.0, origin="reported", evidence_id=e) for i, e in enumerate(CONDITION_EVIDENCE)),
        ])
        session.commit()


def _audit_rows(session_factory):
    with session_factory() as session:
        return session.query(AuditEvent).order_by(AuditEvent.occurred_at).all()


def test_admin_routes_need_the_write_token_for_reads_and_writes(client, corpus):
    for method, path, body in (
        ("GET", "/api/admin/files", None),
        ("GET", "/api/admin/ingestion-runs", None),
        ("GET", "/api/admin/audit", None),
        ("POST", f"/api/admin/files/{QUARANTINED}/reprocess", None),
        ("PUT", f"/api/admin/evidence/{KEPT_EVIDENCE}/review", {"review_status": "rejected"}),
    ):
        response = client.request(method, path, json=body)   # the client fixture sends the read token
        assert response.status_code == 401, (method, path)
        assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
    # Reads outside /api/admin/ keep working with the read token, including the AI status.
    assert client.get("/api/ai/providers").status_code == 200
    assert client.get("/api/admin/files", headers=WRITE).status_code == 200


def test_the_router_refuses_a_request_the_middleware_did_not_authorise_with_the_write_token(client):
    from flame_api import admin

    class State:
        token_scope = "read"

    class Fake:
        state = State()

    with pytest.raises(admin.WriteTokenRequired):
        admin.require_write_token(Fake())


def test_files_are_listed_with_their_quarantine_reason(client, corpus):
    response = client.get("/api/admin/files", params={"status": "quarantined"}, headers=WRITE)
    body = response.json()

    assert response.status_code == 200
    assert [(f["file_id"], f["status"], f["quarantine_reason"]) for f in body["items"]] == [(QUARANTINED, "quarantined", "checksum_mismatch")]
    assert body["pagination"]["total_items"] == 1
    assert_contract_component(body, "AdminFileListResponse")
    assert client.get("/api/admin/files", headers=WRITE).json()["pagination"]["total_items"] == 2
    assert client.get("/api/admin/files", params={"status": "deleted"}, headers=WRITE).status_code == 400


def test_failed_ingestion_runs_are_listed(client, corpus):
    response = client.get("/api/admin/ingestion-runs", params={"transformation_id": "quarantine"}, headers=WRITE)
    body = response.json()

    assert response.status_code == 200
    assert [(r["file_id"], r["counts"]) for r in body["items"]] == [(QUARANTINED, {"reason": "checksum_mismatch"})]
    assert_contract_component(body, "IngestionRunListResponse")


def test_reprocess_clears_the_quarantine_and_audits_it(client, corpus, session_factory):
    response = client.post(f"/api/admin/files/{QUARANTINED}/reprocess", json={"note": "re-mirrored"},
                           headers={**WRITE, "X-Request-ID": "req-reprocess-1"})
    body = response.json()

    assert response.status_code == 200
    assert (body["file"]["status"], body["file"]["quarantine_reason"]) == ("active", None)
    assert_contract_component(body, "FileReprocessResponse")
    with session_factory() as session:
        record = session.get(FileRecord, QUARANTINED)
        assert (record.status, record.quarantine_reason) == ("active", None)
        assert session.query(IngestionRun).count() == 1   # history is kept; ingestion is not run inline
    [event] = _audit_rows(session_factory)
    assert (event.action, event.target_type, event.target_id, event.actor, event.request_id) == (
        "file.reprocess", "file_record", QUARANTINED, "write-token", "req-reprocess-1")
    assert event.before == {"status": "quarantined", "quarantine_reason": "checksum_mismatch"}
    assert event.after == {"status": "active", "quarantine_reason": None, "note": "re-mirrored"}
    assert body["audit_event"]["event_id"] == event.event_id

    again = client.post(f"/api/admin/files/{QUARANTINED}/reprocess", headers=WRITE)
    assert again.status_code == 409 and again.json()["error"]["code"] == "FILE_NOT_QUARANTINED"
    missing = client.post("/api/admin/files/sha256:cccccccccccccccc/reprocess", headers=WRITE)
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "FILE_NOT_FOUND"
    assert len(_audit_rows(session_factory)) == 1   # refused calls change nothing and audit nothing


def test_review_sets_the_status_and_audits_before_and_after(client, corpus, session_factory):
    response = client.put(f"/api/admin/evidence/{KEPT_EVIDENCE}/review",
                          json={"review_status": "human_verified", "note": "checked against p. 1"}, headers=WRITE)
    body = response.json()

    assert response.status_code == 200
    assert (body["previous_review_status"], body["review_status"]) == ("machine_extracted", "human_verified")
    assert_contract_component(body, "EvidenceReviewResponse")
    with session_factory() as session:
        evidence = session.get(EvidenceRecord, KEPT_EVIDENCE)
        assert evidence.payload == {"review_status": "human_verified", "extraction_method": "verbatim_text"}
    [event] = _audit_rows(session_factory)
    assert (event.action, event.target_type, event.target_id) == ("evidence.review", "evidence", KEPT_EVIDENCE)
    assert (event.before, event.after) == ({"review_status": "machine_extracted"}, {"review_status": "human_verified", "note": "checked against p. 1"})
    assert client.get(f"/api/evidence/{KEPT_EVIDENCE}").json()["evidence"]["review_status"] == "human_verified"

    for bad in ({"review_status": "raw"}, {"review_status": "approved"}, {}):
        assert client.put(f"/api/admin/evidence/{KEPT_EVIDENCE}/review", json=bad, headers=WRITE).status_code == 400
    missing = client.put("/api/admin/evidence/01J9Z3N5B8C1E3G5J7M9P1R3T9/review", json={"review_status": "rejected"}, headers=WRITE)
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "EVIDENCE_NOT_FOUND"
    assert len(_audit_rows(session_factory)) == 1


def test_the_review_values_are_the_contracts(client):
    from typing import get_args

    from flame_api.admin import ReviewBody

    schemas = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))["components"]["schemas"]
    allowed = set(get_args(ReviewBody.model_fields["review_status"].annotation))
    assert allowed == set(schemas["AdminReviewStatus"]["enum"])
    assert allowed <= set(schemas["ReviewStatus"]["enum"])


def test_rejected_evidence_is_not_returned_by_search(client, corpus):
    def hits():
        body = client.get("/api/search", params={"q": "heptane", "domain": "all"}).json()
        assert_contract_component(body, "SearchResponse")
        return body

    before = hits()
    assert {r["evidence_id"] for r in before["results"]} == {KEPT_EVIDENCE, REJECTED_EVIDENCE, CONDITION_EVIDENCE[0]}

    assert client.put(f"/api/admin/evidence/{REJECTED_EVIDENCE}/review", json={"review_status": "rejected"}, headers=WRITE).status_code == 200
    assert client.put(f"/api/admin/evidence/{CONDITION_EVIDENCE[0]}/review", json={"review_status": "rejected"}, headers=WRITE).status_code == 200
    after = hits()
    # The rejected passage is gone; the experiment now cites its remaining, unrejected condition.
    assert {r["evidence_id"] for r in after["results"]} == {KEPT_EVIDENCE, CONDITION_EVIDENCE[1]}
    assert after["pagination"]["total_items"] == 2

    assert client.put(f"/api/admin/evidence/{CONDITION_EVIDENCE[1]}/review", json={"review_status": "rejected"}, headers=WRITE).status_code == 200
    assert {r["result_type"] for r in hits()["results"]} == {"document"}   # nothing left to cite for the experiment


def test_rejected_evidence_never_reaches_chat(client, corpus, session_factory, monkeypatch):
    from pydantic import SecretStr

    from flame_api.config import Settings

    class FakeResponse:
        status = 200

        def __init__(self, body):
            self.body = json.dumps(body).encode()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, size=-1):
            return self.body[:size]

    chat_settings = Settings(api_auth_enabled=True, read_api_token=SecretStr(READ_TOKEN), write_api_token=SecretStr(WRITE_TOKEN),
                             aura_enabled=True, aura_service_token=SecretStr("svc-flame-secret-that-is-not-a-real-credential"),
                             aura_require_local=False)
    for evidence_id in (KEPT_EVIDENCE, REJECTED_EVIDENCE, *CONDITION_EVIDENCE):
        client.put(f"/api/admin/evidence/{evidence_id}/review", json={"review_status": "rejected"}, headers=WRITE)

    def forbidden(request, timeout):
        raise AssertionError("no model may be asked: every matching passage was rejected")

    main._chat_calls.clear()
    monkeypatch.setattr(main, "settings", chat_settings)
    monkeypatch.setattr(provider_http, "urlopen", forbidden)
    body = client.post("/api/chat", json={"query": "heptane"}).json()
    assert body["sources"] == [] and body["warnings"] == ["no_matching_evidence"]

    client.put(f"/api/admin/evidence/{KEPT_EVIDENCE}/review", json={"review_status": "human_verified"}, headers=WRITE)
    sent = {}

    def fake_urlopen(request, timeout):
        sent["body"] = json.loads(request.data)
        return FakeResponse({"data": {"answer": "Cool flame extinction.", "evidence_ids": [KEPT_EVIDENCE, REJECTED_EVIDENCE]},
                             "provider": "hfspace", "model": "Qwen/Qwen2.5-7B-Instruct-AWQ", "cached": False})

    monkeypatch.setattr(provider_http, "urlopen", fake_urlopen)
    body = client.post("/api/chat", json={"query": "heptane"}).json()
    assert [s["evidence_id"] for s in body["sources"]] == [KEPT_EVIDENCE]
    assert REJECTED_EVIDENCE not in json.dumps(sent["body"])
    main._chat_calls.clear()


def test_the_audit_log_is_readable_and_filterable(client, corpus):
    client.post(f"/api/admin/files/{QUARANTINED}/reprocess", headers=WRITE)
    client.put(f"/api/admin/evidence/{KEPT_EVIDENCE}/review", json={"review_status": "rejected"}, headers=WRITE)

    everything = client.get("/api/admin/audit", headers=WRITE).json()
    reviews = client.get("/api/admin/audit", params={"action": "evidence.review"}, headers=WRITE).json()

    assert [e["action"] for e in everything["items"]] == ["evidence.review", "file.reprocess"]   # newest first
    assert [e["target_id"] for e in reviews["items"]] == [KEPT_EVIDENCE]
    assert_contract_component(everything, "AuditEventListResponse")


def test_a_reingest_keeps_the_administrators_review(tmp_path, monkeypatch):
    import fitz
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from flame_api.ingest import _create_document
    from flame_api.models import Base

    monkeypatch.setattr("flame_api.ingest._ocr_page", lambda page: None)
    pdf_path = tmp_path / "report.pdf"
    pdf = fitz.open()
    pdf.new_page().insert_text((72, 72), "Microgravity flame spread.")
    pdf.save(pdf_path)
    pdf.close()
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(SourceRecord(source_id="FF-PSI-25", title="BASS-II", repository="NASA PSI", access_url="https://psi.nasa.gov/"))
        file_record = FileRecord(file_id="sha256:1234567890abcdef", source_id="FF-PSI-25", sha256="1234567890abcdef" * 4,
                                 original_filename=pdf_path.name, media_type="application/pdf", size_bytes=1,
                                 retrieved_at=datetime.now(UTC), local_path=str(pdf_path))
        session.add(file_record)
        session.commit()
        _create_document(session, file_record)
        session.commit()
        evidence = session.query(EvidenceRecord).one()
        evidence.payload = {**evidence.payload, "review_status": "rejected"}
        session.commit()

        _create_document(session, file_record)
        session.commit()
        session.expire_all()
        assert session.query(EvidenceRecord).one().payload["review_status"] == "rejected"
    engine.dispose()


def test_admin_operations_are_in_the_contract_and_excluded_from_aura():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    admin_ops = [(m, p, op) for p, item in contract["paths"].items() if p.startswith("/api/admin/") for m, op in item.items()]
    assert {(m.upper(), p) for m, p, _ in admin_ops} >= {
        ("GET", "/api/admin/files"), ("GET", "/api/admin/ingestion-runs"), ("POST", "/api/admin/files/{file_id}/reprocess"),
        ("PUT", "/api/admin/evidence/{evidence_id}/review"), ("GET", "/api/admin/audit"),
    }
    for _, _, op in admin_ops:
        assert op["x-aura-exclude"] is True and op["tags"] == ["Admin"]
        assert op["responses"]["200"]["content"]["application/json"]["examples"]
    for method, path, op in admin_ops:
        if path == "/api/admin/ai/mode":
            continue
        schema = op["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].rsplit("/", 1)[-1]
        for example in op["responses"]["200"]["content"]["application/json"]["examples"].values():
            assert_contract_component(example["value"], schema)
