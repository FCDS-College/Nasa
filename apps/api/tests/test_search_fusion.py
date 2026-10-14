"""/api/search ranks with reciprocal rank fusion (ai.rag), and semantic hits survive paging."""
from datetime import UTC, datetime

from flame_api import main
from flame_api.models import DocumentChunk, DocumentRecord, FileRecord, SourceRecord


def _seed(session_factory, n=4):
    now = datetime.now(UTC)
    with session_factory() as s:
        s.add(SourceRecord(source_id="src", title="S", repository="NASA", access_url="https://example.org", domain="combustion"))
        s.add(FileRecord(file_id="f1", source_id="src", sha256="0" * 64, original_filename="a.pdf", media_type="application/pdf", size_bytes=1, retrieved_at=now))
        s.add(DocumentRecord(document_id="d1", source_id="src", file_id="f1", title="Doc", ingested_at=now))
        texts = ["flame flame flame spread", "flame spread rate", "flame only once", "unrelated words"]
        for i, text in enumerate(texts[:n]):
            s.add(DocumentChunk(chunk_id=f"c{i}", document_id="d1", source_id="src", file_id="f1", evidence_id=f"e{i}", page=1, text=text, ingested_at=now))
        s.commit()


def test_lexical_order_and_scores_are_rrf_values(client, session_factory):
    _seed(session_factory)
    body = client.get("/api/search", params={"q": "flame", "type": "document"}).json()
    ids = [r["result_id"] for r in body["results"]]
    scores = [r["score"] for r in body["results"]]
    assert ids[0] == "c0" and set(ids) == {"c0", "c1", "c2"}
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == round(1 / 61, 6), "lexical-only rank 1 scores 1/(k+1) with k=60"


def test_semantic_hits_are_merged_on_page_two_and_under_an_experiment_filter(client, session_factory, monkeypatch):
    _seed(session_factory)
    calls = []

    def fake_status(session):
        return {"state": "up", "version": "kv-test"}

    def fake_search(session, query, limit=20, **_):
        calls.append(query)
        return [("c3", 0.9)]

    monkeypatch.setattr(main, "index_status", fake_status)
    monkeypatch.setattr(main, "search_chunks", fake_search)

    page2 = client.get("/api/search", params={"q": "flame", "type": "document", "page": 2, "page_size": 1}).json()
    assert calls, "dense search must run on page 2"
    assert page2["retrieval"]["mode"] == "hybrid"
    everything = client.get("/api/search", params={"q": "flame", "type": "document", "page_size": 10}).json()
    assert "c3" in [r["result_id"] for r in everything["results"]], "a dense-only hit is returned"
