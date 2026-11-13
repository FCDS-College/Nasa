"""/api/chat must hand the model the part of a page that answers the question, not the page's first 400 characters."""
import json
from datetime import UTC, datetime

import pytest
from pydantic import SecretStr

from ai.providers import http as provider_http
from flame_api import main
from flame_api.config import Settings
from flame_api.models import DocumentChunk, DocumentRecord, FileRecord, SourceRecord

DOCUMENT_ID = "01J9Z3M2A7D4F6H8K0N2Q4S6T8"
EVIDENCE_ID = "01J9Z3N5B8C1E3G5J7M9P1R3T5"
ANSWER = "Extinction of PMMA occurred at an oxygen concentration of 14 percent."
FILLER = "The apparatus description continues with unrelated mounting details and calibration remarks. "
PAGE_TEXT = (FILLER * 20)[:1500] + " " + ANSWER + " " + (FILLER * 20)[:1500]


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


def _settings():
    return Settings(
        api_auth_enabled=True,
        read_api_token=SecretStr("test-read-token-0123456789abcdef0123456789"),
        write_api_token=SecretStr("test-write-token-0123456789abcdef0123456789"),
        aura_enabled=True,
        aura_service_token=SecretStr("svc-flame-secret-that-is-not-a-real-credential"),
        aura_require_local=False,
    )


@pytest.fixture(autouse=True)
def fresh_limiter():
    main._chat_calls.clear()
    yield
    main._chat_calls.clear()


@pytest.fixture
def long_page(session_factory):
    now = datetime.now(UTC)
    with session_factory() as session:
        session.add(SourceRecord(source_id="nasa-ntrs", title="NTRS", repository="NASA", access_url="https://example.org", domain="combustion"))
        session.add(FileRecord(file_id="file-1", source_id="nasa-ntrs", sha256="0" * 64, original_filename="a.pdf", media_type="application/pdf", size_bytes=1, retrieved_at=now))
        session.add(DocumentRecord(document_id=DOCUMENT_ID, source_id="nasa-ntrs", file_id="file-1", title="PMMA extinction report", ingested_at=now))
        session.add(DocumentChunk(chunk_id="chunk-1", document_id=DOCUMENT_ID, source_id="nasa-ntrs", file_id="file-1", evidence_id=EVIDENCE_ID, page=7, text=PAGE_TEXT, ingested_at=now))
        session.commit()


def test_the_model_receives_the_passage_that_answers_the_question(client, long_page, monkeypatch):
    sent = {}

    def fake_urlopen(request, timeout):
        sent["body"] = json.loads(request.data)
        return FakeResponse({"data": {"answer": "14 percent.", "evidence_ids": [EVIDENCE_ID]}, "provider": "hfspace", "model": "m", "cached": False})

    monkeypatch.setattr(main, "settings", _settings())
    monkeypatch.setattr(provider_http, "urlopen", fake_urlopen)
    assert PAGE_TEXT.index(ANSWER) > 400, "the fixture must put the answer beyond the old 400-character prefix"

    response = client.post("/api/chat", json={"query": "At what oxygen concentration did PMMA extinction occur?"})

    assert response.status_code == 200 and [s["evidence_id"] for s in response.json()["sources"]] == [EVIDENCE_ID]
    passage_text = sent["body"]["context"][0]["text"]
    assert ANSWER in passage_text, "the answer sentence never reached the model"
    assert len(passage_text) <= 1500
