"""Sub-phase 2H §8.8 scenarios at the API boundary (H-5). A fake HTTP layer stands in for Ollama and
AURA; a socket guard fails the test if anything tries to open a real connection."""
import json
import socket
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError

import pytest
from pydantic import SecretStr

from ai.providers import http as provider_http
from flame_api import main
from flame_api.config import Settings
from flame_api.models import AuditEvent, DocumentChunk, DocumentRecord, FileRecord, SourceRecord

READ_TOKEN = "test-read-token-0123456789abcdef0123456789"
WRITE_TOKEN = "test-write-token-0123456789abcdef0123456789"
EVIDENCE_ID = "01J9Z3N5B8C1E3G5J7M9P1R3T5"
DOCUMENT_ID = "01J9Z3M2A7D4F6H8K0N2Q4S6T8"
OLLAMA = "http://ollama.internal:11434"
AURA_HOST = "aura.example"


class Reply:
    status = 200

    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size=-1):
        return self.body[:size] if size and size > 0 else self.body


class FakeNet:
    """Routes urlopen by URL. ``aura`` / ``ollama_chat`` are callables or reply bodies."""

    def __init__(self, *, aura=None, ollama_chat=None, ollama_models=("qwen2.5:3b-instruct-q4_K_M",)):
        self.aura = aura
        self.ollama_chat = ollama_chat
        self.ollama_models = ollama_models
        self.hosts: list[str] = []

    def __call__(self, request, timeout):
        url = request.full_url
        self.hosts.append(url.split("/")[2])
        if url.startswith(OLLAMA + "/api/tags"):
            return Reply({"models": [{"name": m} for m in self.ollama_models]})
        if url.startswith(OLLAMA + "/api/chat"):
            return self._answer(self.ollama_chat, request)
        if AURA_HOST in url:
            return self._answer(self.aura, request)
        raise AssertionError(f"unexpected request to {url}")

    @staticmethod
    def _answer(handler, request):
        if handler is None:
            raise URLError("connection refused")
        if callable(handler):
            return handler(request)
        return Reply(handler)


def ollama_answer(answer="A cool flame was observed.", evidence_ids=(EVIDENCE_ID,)):
    return {"model": "qwen2.5:3b-instruct-q4_K_M", "message": {"role": "assistant",
            "content": json.dumps({"answer": answer, "evidence_ids": list(evidence_ids)})}, "eval_count": 20}


def aura_answer():
    return {"data": {"answer": "From AURA.", "evidence_ids": [EVIDENCE_ID]}, "provider": "hfspace", "model": "qwen-7b", "cached": False}


def settings_for(mode, *, aura=True, ollama=True):
    return Settings(
        api_auth_enabled=True, read_api_token=SecretStr(READ_TOKEN), write_api_token=SecretStr(WRITE_TOKEN),
        aura_enabled=aura, aura_service_token=SecretStr("svc-flame-not-a-real-credential") if aura else None,
        aura_base_url=f"https://{AURA_HOST}", aura_require_local=False,
        ollama_base_url=OLLAMA if ollama else None, ai_execution_mode=mode,
    )


@pytest.fixture(autouse=True)
def no_real_sockets(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("a test tried to open a real network connection")

    monkeypatch.setattr(socket, "create_connection", refuse)
    main._chat_calls.clear()


@pytest.fixture
def corpus(session_factory):
    now = datetime.now(UTC)
    with session_factory() as session:
        session.add(SourceRecord(source_id="nasa-psi", title="PSI", repository="NASA", access_url="https://example.org", domain="combustion"))
        session.add(FileRecord(file_id="file-1", source_id="nasa-psi", sha256="0" * 64, original_filename="a.pdf", media_type="application/pdf", size_bytes=1, retrieved_at=now))
        session.add(DocumentRecord(document_id=DOCUMENT_ID, source_id="nasa-psi", file_id="file-1", title="PSI-69 Cool Flames", ingested_at=now))
        session.add(DocumentChunk(chunk_id="chunk-1", document_id=DOCUMENT_ID, source_id="nasa-psi", file_id="file-1",
                                  evidence_id=EVIDENCE_ID, page=3, text="n-heptane droplets show a cool flame in microgravity.", ingested_at=now))
        session.commit()


def test_offline_only_answers_locally_and_makes_no_external_request(client, corpus, monkeypatch):
    net = FakeNet(aura=aura_answer(), ollama_chat=ollama_answer())
    monkeypatch.setattr(provider_http, "urlopen", net)
    monkeypatch.setattr(main, "settings", settings_for("offline_only"))

    body = client.post("/api/chat", json={"query": "n-heptane"}).json()

    assert body["execution"]["provider"] == "ollama" and body["execution"]["locality"] == "local"
    assert body["execution"]["mode"] == "offline_only"
    assert [s["evidence_id"] for s in body["sources"]] == [EVIDENCE_ID]
    assert AURA_HOST not in net.hosts, "offline_only must never contact an external provider"


def test_internet_drops_during_a_cloud_request_and_the_local_model_answers(client, corpus, monkeypatch):
    def timed_out(request):
        raise URLError(TimeoutError("timed out"))

    net = FakeNet(aura=timed_out, ollama_chat=ollama_answer())
    monkeypatch.setattr(provider_http, "urlopen", net)
    monkeypatch.setattr(main, "settings", settings_for("cloud_preferred"))

    body = client.post("/api/chat", json={"query": "n-heptane"}).json()

    assert body["answer"] == "A cool flame was observed."
    assert body["execution"]["provider"] == "ollama" and body["execution"]["fallback_used"] is True
    assert body["execution"]["attempts"] == [{"provider": "aura", "code": "timeout"}]
    assert "model_fallback_used" in body["warnings"]
    assert net.hosts.index(AURA_HOST) < net.hosts.index("ollama.internal:11434")


def test_a_local_model_out_of_memory_is_a_controlled_degraded_answer(client, corpus, monkeypatch):
    def oom(request):
        raise HTTPError(request.full_url, 500, "error", {}, _Body(b'{"error":"model requires more system memory (5.1 GiB) than is available (2.0 GiB)"}'))

    monkeypatch.setattr(provider_http, "urlopen", FakeNet(ollama_chat=oom))
    monkeypatch.setattr(main, "settings", settings_for("offline_only", aura=False))

    response = client.post("/api/chat", json={"query": "n-heptane"})
    body = response.json()

    assert response.status_code == 200
    assert body["warnings"] == ["generation_unavailable"]
    assert body["execution"]["reasons"] == [{"provider": "ollama", "reason": "resource_exhausted"}]
    assert [s["evidence_id"] for s in body["sources"]] == [EVIDENCE_ID]


def test_a_missing_local_model_is_reported_by_health_with_an_actionable_reason(client, monkeypatch):
    monkeypatch.setattr(provider_http, "urlopen", FakeNet(ollama_models=("llama3:8b",)))
    monkeypatch.setattr(main, "settings", settings_for("offline_only", aura=False))

    providers = {p["name"]: p for p in client.get("/api/ai/providers").json()["providers"]}

    assert providers["ollama"]["health"] == {"state": "down", "latency_ms": providers["ollama"]["health"]["latency_ms"],
                                             "detail": "model_missing", "model_present": False}


def test_a_missing_model_found_by_health_is_skipped_without_a_call(client, corpus, monkeypatch):
    net = FakeNet(ollama_models=(), ollama_chat=ollama_answer())
    monkeypatch.setattr(provider_http, "urlopen", net)
    monkeypatch.setattr(main, "settings", settings_for("offline_only", aura=False))
    client.get("/api/ai/providers")          # refresh health

    body = client.post("/api/chat", json={"query": "n-heptane"}).json()

    assert body["execution"]["reasons"] == [{"provider": "ollama", "reason": "health_down:model_missing"}]
    assert not any("/api/chat" in h for h in net.hosts)


def test_chat_without_any_model_in_offline_only_is_a_clear_503(client, corpus, monkeypatch):
    monkeypatch.setattr(main, "settings", settings_for("offline_only", ollama=False))

    response = client.post("/api/chat", json={"query": "n-heptane"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CHAT_UNAVAILABLE"
    assert "offline_only" in response.json()["error"]["message"]


def test_the_mode_change_needs_the_write_token_and_is_audited(client, session_factory, monkeypatch):
    monkeypatch.setattr(provider_http, "urlopen", FakeNet())
    monkeypatch.setattr(main, "settings", settings_for("cloud_preferred"))

    assert client.put("/api/admin/ai/mode", json={"mode": "offline_only"}).status_code == 401
    response = client.put("/api/admin/ai/mode", json={"mode": "offline_only"}, headers={"Authorization": f"Bearer {WRITE_TOKEN}"})

    assert response.status_code == 200
    assert response.json()["previous_mode"] == "cloud_preferred" and response.json()["mode"] == "offline_only"
    assert client.get("/api/ai/providers").json()["mode"] == "offline_only"
    with session_factory() as session:
        event = session.query(AuditEvent).one()
    assert (event.action, event.before, event.after) == ("ai.mode.changed", {"mode": "cloud_preferred"}, {"mode": "offline_only"})
    bad = client.put("/api/admin/ai/mode", json={"mode": "anything"}, headers={"Authorization": f"Bearer {WRITE_TOKEN}"})
    assert bad.status_code == 400


def test_local_and_cloud_answers_both_carry_their_provenance(client, corpus, monkeypatch):
    net = FakeNet(aura=aura_answer(), ollama_chat=ollama_answer(answer="From the local model."))
    monkeypatch.setattr(provider_http, "urlopen", net)
    answers = {}
    for mode in ("cloud_preferred", "local_first"):
        monkeypatch.setattr(main, "settings", settings_for(mode))
        body = client.post("/api/chat", json={"query": "n-heptane"}).json()
        answers[body["execution"]["provider"]] = body
    assert set(answers) == {"aura", "ollama"}
    assert answers["aura"]["model"]["name"] == "qwen-7b" and answers["ollama"]["model"]["name"] == "qwen2.5:3b-instruct-q4_K_M"
    assert answers["aura"]["sources"] == answers["ollama"]["sources"], "evidence is the same whichever model wrote the text"


def test_offline_embeddings_never_download_a_missing_model(tmp_path):
    from ai.providers.contracts.embeddings import EmbeddingRequest
    from ai.providers.contracts.errors import ProviderError
    from ai.providers.local.fastembed_embeddings import FastEmbedProvider

    provider = FastEmbedProvider(cache_dir=str(tmp_path), offline=True)

    assert provider.health(1.0).state == "down"
    with pytest.raises(ProviderError) as caught:
        provider.embed(EmbeddingRequest(texts=("flame",)))
    assert caught.value.code.value == "model_missing" and caught.value.request_sent is False


class _Body:
    def __init__(self, data):
        self.data = data

    def read(self, size=-1):
        return self.data

    def close(self):
        pass


def test_switching_to_offline_only_makes_embeddings_cache_only(tmp_path, monkeypatch):
    """Even with FLAME_EMBEDDING_OFFLINE=false, offline_only must never download model weights."""
    from ai.providers.contracts.embeddings import EmbeddingRequest
    from ai.providers.contracts.errors import ProviderError
    from flame_api import ai_runtime

    monkeypatch.setattr(main, "settings", settings_for("local_first", aura=False))
    monkeypatch.setattr(main.settings, "embedding_cache_dir", str(tmp_path))
    router = ai_runtime.get_router(main.settings)
    fastembed = router.registry.get("fastembed")
    assert fastembed._offline is False
    router.set_mode(__import__("ai.routing", fromlist=["ExecutionMode"]).ExecutionMode.OFFLINE_ONLY)
    assert fastembed._offline is True
    with pytest.raises(ProviderError) as caught:
        fastembed.embed(EmbeddingRequest(texts=("flame",)))
    assert caught.value.code.value == "model_missing"
