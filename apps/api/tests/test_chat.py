import json
from datetime import UTC, datetime
from urllib.error import URLError

import pytest
from pydantic import SecretStr

from flame_api import aura_integration, main
from flame_api.config import Settings
from flame_api.models import DocumentChunk, DocumentRecord, FileRecord, SourceRecord

AURA_TOKEN = "svc-flame-secret-that-is-not-a-real-credential"
READ_TOKEN = "test-read-token-0123456789abcdef0123456789"
WRITE_TOKEN = "test-write-token-0123456789abcdef0123456789"
DOCUMENT_ID = "01J9Z3M2A7D4F6H8K0N2Q4S6T8"
EVIDENCE_ID = "01J9Z3N5B8C1E3G5J7M9P1R3T5"
CHUNK_TEXT = "Evolution of flame temperature for n-heptane droplets shows a cool flame in microgravity."


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


def chat_settings(**overrides):
    options = {"aura_require_local": False, **overrides}
    return Settings(
        api_auth_enabled=True,
        read_api_token=SecretStr(READ_TOKEN),
        write_api_token=SecretStr(WRITE_TOKEN),
        aura_enabled=True,
        aura_service_token=SecretStr(AURA_TOKEN),
        **options,
    )


@pytest.fixture(autouse=True)
def fresh_limiter():
    main._chat_calls.clear()
    yield
    main._chat_calls.clear()


@pytest.fixture
def corpus(session_factory):
    now = datetime.now(UTC)
    with session_factory() as session:
        session.add(SourceRecord(source_id="nasa-psi", title="PSI", repository="NASA", access_url="https://example.org", domain="combustion"))
        session.add(FileRecord(file_id="file-1", source_id="nasa-psi", sha256="0" * 64, original_filename="a.pdf", media_type="application/pdf", size_bytes=1, retrieved_at=now))
        session.add(DocumentRecord(document_id=DOCUMENT_ID, source_id="nasa-psi", file_id="file-1", title="PSI-69 Cool Flames", ingested_at=now))
        session.add(DocumentChunk(chunk_id="chunk-1", document_id=DOCUMENT_ID, source_id="nasa-psi", file_id="file-1", evidence_id=EVIDENCE_ID, page=3, text=CHUNK_TEXT, ingested_at=now))
        session.commit()


def aura_reply(answer, evidence_ids, **extra):
    return {"data": {"answer": answer, "evidence_ids": evidence_ids}, "provider": "hfspace", "model": "Qwen/Qwen2.5-7B-Instruct-AWQ", "cached": False, **extra}


def test_answer_is_written_by_aura_from_flame_evidence_only(client, corpus, monkeypatch):
    sent = {}

    def fake_urlopen(request, timeout):
        sent["request"] = request
        sent["body"] = json.loads(request.data)
        return FakeResponse(aura_reply("A cool flame was simulated for n-heptane.", [EVIDENCE_ID, "01J9Z3Q9D3F5H7K9N1R3T5W7Y9"]))

    monkeypatch.setattr(main, "settings", chat_settings())
    monkeypatch.setattr(aura_integration, "urlopen", fake_urlopen)

    response = client.post("/api/chat", json={"query": "How does n-heptane behave in microgravity?"})
    body = response.json()

    assert response.status_code == 200
    assert body["answer"] == "A cool flame was simulated for n-heptane."
    assert [s["evidence_id"] for s in body["sources"]] == [EVIDENCE_ID]
    assert body["sources"][0]["document_id"] == DOCUMENT_ID
    assert body["model"] == {"provider": "hfspace", "name": "Qwen/Qwen2.5-7B-Instruct-AWQ", "version": "unknown"}
    assert body["warnings"] == ["citations_not_in_retrieved_evidence_removed"]
    assert body["request_id"] == response.headers["X-Request-ID"]

    aura = sent["body"]
    assert sent["request"].full_url.endswith("/api/v3/chat")
    assert sent["request"].headers["Authorization"] == f"Bearer {AURA_TOKEN}"
    assert [entry["id"] for entry in aura["context"]] == [EVIDENCE_ID]
    assert CHUNK_TEXT[:40] in aura["context"][0]["text"]
    assert CHUNK_TEXT[:40] not in aura["message"], "evidence must not travel on the USER channel"
    assert aura["use_tools"] is False and aura["use_knowledge"] is False and aura["use_memory"] is False
    assert aura["require_local"] is False and aura["response_schema"]["required"] == ["answer", "evidence_ids"]


def test_a_natural_language_question_is_matched_by_its_distinctive_words(client, corpus, monkeypatch):
    monkeypatch.setattr(main, "settings", chat_settings())
    monkeypatch.setattr(aura_integration, "urlopen", lambda request, timeout: FakeResponse(aura_reply("ok", [EVIDENCE_ID])))

    response = client.post("/api/chat", json={"query": "How does microgravity alter a cool flame?"})

    assert response.status_code == 200
    assert [s["evidence_id"] for s in response.json()["sources"]] == [EVIDENCE_ID]


def test_no_matching_evidence_never_calls_aura(client, corpus, monkeypatch):
    def forbidden(request, timeout):
        raise AssertionError("AURA must not be asked when there is nothing to ground an answer on")

    monkeypatch.setattr(main, "settings", chat_settings())
    monkeypatch.setattr(aura_integration, "urlopen", forbidden)

    response = client.post("/api/chat", json={"query": "zeppelin"})
    body = response.json()

    assert response.status_code == 200
    assert body["sources"] == [] and body["warnings"] == ["no_matching_evidence"]
    assert body["model"]["provider"] == "flame"


def test_an_answer_that_cites_nothing_is_flagged(client, corpus, monkeypatch):
    monkeypatch.setattr(main, "settings", chat_settings())
    monkeypatch.setattr(aura_integration, "urlopen", lambda request, timeout: FakeResponse(aura_reply("Not enough evidence.", [])))

    body = client.post("/api/chat", json={"query": "n-heptane"}).json()

    assert body["sources"] == [] and body["warnings"] == ["answer_cites_no_evidence"]


def test_aura_failure_is_a_retryable_502_without_internals(client, corpus, monkeypatch):
    def down(request, timeout):
        raise URLError("connection refused: https://internal.example")

    monkeypatch.setattr(main, "settings", chat_settings())
    monkeypatch.setattr(aura_integration, "urlopen", down)

    response = client.post("/api/chat", json={"query": "n-heptane"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "AURA_UNAVAILABLE"
    assert response.json()["error"]["retryable"] is True
    assert "internal.example" not in response.text


def test_malformed_aura_output_is_rejected(client, corpus, monkeypatch):
    monkeypatch.setattr(main, "settings", chat_settings())
    monkeypatch.setattr(aura_integration, "urlopen", lambda request, timeout: FakeResponse(aura_reply("x" * 5000, [EVIDENCE_ID])))

    assert client.post("/api/chat", json={"query": "n-heptane"}).status_code == 502


def test_chat_is_unavailable_when_aura_is_disabled(client, corpus):
    response = client.post("/api/chat", json={"query": "n-heptane"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CHAT_UNAVAILABLE"


def test_chat_needs_the_read_token_and_not_the_write_token(client, corpus, monkeypatch):
    monkeypatch.setattr(main, "settings", chat_settings())
    monkeypatch.setattr(aura_integration, "urlopen", lambda request, timeout: FakeResponse(aura_reply("ok", [EVIDENCE_ID])))

    assert client.post("/api/chat", json={"query": "n-heptane"}, headers={"Authorization": ""}).status_code == 401
    assert client.post("/api/chat", json={"query": "n-heptane"}, headers={"Authorization": f"Bearer {WRITE_TOKEN}"}).status_code == 401
    assert client.post("/api/chat", json={"query": "n-heptane"}).status_code == 200


def test_other_post_routes_still_need_the_write_token(client):
    response = client.post("/api/analyses", headers={"Authorization": f"Bearer {READ_TOKEN}"})

    assert response.status_code == 401


def test_requests_are_rate_limited(client, corpus, monkeypatch):
    monkeypatch.setattr(main, "settings", chat_settings(chat_rate_limit_per_minute=1))
    monkeypatch.setattr(aura_integration, "urlopen", lambda request, timeout: FakeResponse(aura_reply("ok", [EVIDENCE_ID])))

    assert client.post("/api/chat", json={"query": "n-heptane"}).status_code == 200
    limited = client.post("/api/chat", json={"query": "n-heptane"})

    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "10"
    assert limited.json()["error"]["retryable"] is True


def test_invalid_bodies_are_contract_validation_errors(client):
    for payload in ({}, {"query": ""}, {"query": "x" * 501}):
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_chat_is_not_part_of_the_aura_facing_contract(client):
    assert "/api/chat" not in client.get("/api/openapi.json").json()["paths"]


def test_the_interpreter_honours_the_require_local_setting(monkeypatch):
    sent = {}

    def fake_urlopen(request, timeout):
        sent.update(json.loads(request.data))
        return FakeResponse({"data": {"statements": []}})

    monkeypatch.setattr(aura_integration, "urlopen", fake_urlopen)
    for value in (True, False):
        aura_integration.interpret_analysis(
            chat_settings(aura_require_local=value), analysis_id="01J9Z3Q9D3F5H7K9N1R3T5W7Y9", context=[], allowed_evidence_ids=set()
        )
        assert sent["require_local"] is value
