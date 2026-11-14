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


def test_dense_only_hit_scores_only_its_dense_rank(client, session_factory, monkeypatch):
    _seed(session_factory)
    monkeypatch.setattr(main, "index_status", lambda session: {"state": "up", "version": "kv-test"})
    monkeypatch.setattr(main, "search_chunks", lambda session, query, limit=20, **_: [("c3", 0.9)])
    body = client.get("/api/search", params={"q": "flame", "type": "document", "page_size": 10}).json()
    by_id = {r["result_id"]: r["score"] for r in body["results"]}
    assert by_id["c3"] == round(1 / 61, 6), "dense rank 1 only; no phantom lexical rank"
    assert by_id["c0"] == round(1 / 61, 6)



def test_a_dense_only_hit_from_another_domain_is_dropped_under_domain_combustion(client, session_factory, monkeypatch):
    """The dense leg ranks every chunk; its hits must pass the same domain filter as lexical matches (audit finding 2)."""
    _seed(session_factory)
    now = datetime.now(UTC)
    with session_factory() as s:
        s.add(SourceRecord(source_id="bio", title="B", repository="NASA", access_url="https://example.org", domain="biology"))
        s.add(FileRecord(file_id="fb", source_id="bio", sha256="1" * 64, original_filename="b.pdf", media_type="application/pdf", size_bytes=1, retrieved_at=now))
        s.add(DocumentRecord(document_id="db", source_id="bio", file_id="fb", title="Bio", ingested_at=now))
        s.add(DocumentChunk(chunk_id="cbio", document_id="db", source_id="bio", file_id="fb", evidence_id="ebio", page=1, text="plant growth", ingested_at=now))
        s.commit()
    monkeypatch.setattr(main, "index_status", lambda session: {"state": "up", "version": "kv"})
    monkeypatch.setattr(main, "search_chunks", lambda session, query, limit=20, **_: [("cbio", 0.9), ("c3", 0.8)])
    combustion = client.get("/api/search", params={"q": "flame", "type": "document", "domain": "combustion"}).json()
    ids = [r["result_id"] for r in combustion["results"]]
    assert "cbio" not in ids and "c3" in ids, "a combustion dense-only hit stays; a biology one is dropped"
    assert combustion["pagination"]["total_items"] == len(ids)
    everything = client.get("/api/search", params={"q": "flame", "type": "document", "domain": "all"}).json()
    assert "cbio" in [r["result_id"] for r in everything["results"]]

def _seed_many(session_factory, n):
    """n chunks that all match "flame"; c00 has the most query terms in its first 400 characters."""
    now = datetime.now(UTC)
    with session_factory() as s:
        s.add(SourceRecord(source_id="src", title="S", repository="NASA", access_url="https://example.org", domain="combustion"))
        s.add(FileRecord(file_id="f1", source_id="src", sha256="0" * 64, original_filename="a.pdf", media_type="application/pdf", size_bytes=1, retrieved_at=now))
        s.add(DocumentRecord(document_id="d1", source_id="src", file_id="f1", title="Doc", ingested_at=now))
        for i in range(n):
            text = "flame spread" if i == 0 else f"flame passage {i}"
            s.add(DocumentChunk(chunk_id=f"c{i:02d}", document_id="d1", source_id="src", file_id="f1", evidence_id=f"e{i}", page=1, text=text, ingested_at=now))
        s.commit()


def test_lexical_candidates_are_capped_but_total_items_counts_every_match(client, session_factory, monkeypatch):
    from sqlalchemy import event

    _seed_many(session_factory, 12)
    monkeypatch.setattr(main, "_LEXICAL_CANDIDATES", 4)
    loaded = []

    def on_load(target, context):
        loaded.append(target.chunk_id)

    event.listen(DocumentChunk, "load", on_load)
    try:
        body = client.get("/api/search", params={"q": "flame spread", "type": "document", "page": 1, "page_size": 2}).json()
        everything = client.get("/api/search", params={"q": "flame", "type": "document", "page": 1, "page_size": 2}).json()
    finally:
        event.remove(DocumentChunk, "load", on_load)
    assert body["pagination"]["total_items"] == 1
    assert len(loaded) == 1 + 4, "at most max(_LEXICAL_CANDIDATES, 2 * page * page_size) chunks are loaded"
    assert everything["pagination"]["total_items"] == 12, "total_items is a COUNT, not the candidate count"
    assert everything["pagination"]["total_pages"] == 6
    assert [r["result_id"] for r in everything["results"]] == ["c00", "c01"]


def test_the_candidate_cut_is_ranked_in_sql_not_by_id(client, session_factory, monkeypatch):
    _seed_many(session_factory, 0)
    now = datetime.now(UTC)
    with session_factory() as s:
        # SQLite scoring: query terms inside the snippet (first 400 characters) rank first
        for i in range(6):
            s.add(DocumentChunk(chunk_id=f"c{i:02d}", document_id="d1", source_id="src", file_id="f1", evidence_id=f"e{i}", page=1,
                                text="x" * 450 + " flame", ingested_at=now))
        s.add(DocumentChunk(chunk_id="c99", document_id="d1", source_id="src", file_id="f1", evidence_id="e99", page=2,
                            text="flame spread rate", ingested_at=now))
        s.commit()
    monkeypatch.setattr(main, "_LEXICAL_CANDIDATES", 2)
    body = client.get("/api/search", params={"q": "flame", "type": "document", "page_size": 1}).json()
    assert body["pagination"]["total_items"] == 7
    assert body["results"][0]["result_id"] == "c99", "the best-scoring match is inside the cut even with the highest id"


def test_paging_through_a_capped_candidate_set_is_stable(client, session_factory, monkeypatch):
    _seed_many(session_factory, 12)
    full = client.get("/api/search", params={"q": "flame", "type": "document", "page_size": 50}).json()["results"]
    monkeypatch.setattr(main, "_LEXICAL_CANDIDATES", 2)
    paged = []
    for page in range(1, 5):
        paged += client.get("/api/search", params={"q": "flame", "type": "document", "page": page, "page_size": 3}).json()["results"]
    assert [r["result_id"] for r in paged] == [r["result_id"] for r in full]
    assert [r["rank"] for r in paged] == list(range(1, 13))
    assert [r["score"] for r in paged] == [r["score"] for r in full]
    assert len({r["result_id"] for r in paged}) == 12, "no hit repeats or goes missing across pages"


def test_a_dense_hit_below_the_lexical_cut_keeps_its_exact_lexical_rank(client, session_factory, monkeypatch):
    _seed_many(session_factory, 12)
    monkeypatch.setattr(main, "index_status", lambda session: {"state": "up", "version": "kv-test"})
    monkeypatch.setattr(main, "search_chunks", lambda session, query, limit=20, **_: [("c10", 0.9)])
    uncapped = client.get("/api/search", params={"q": "flame", "type": "document", "page_size": 50}).json()
    monkeypatch.setattr(main, "_LEXICAL_CANDIDATES", 2)
    capped = client.get("/api/search", params={"q": "flame", "type": "document", "page_size": 1}).json()
    assert capped["results"][0]["result_id"] == "c10"
    assert capped["results"][0]["score"] == uncapped["results"][0]["score"] == round(1 / 61 + 1 / 71, 6)
    assert capped["pagination"]["total_items"] == uncapped["pagination"]["total_items"] == 12, "a deep lexical match is not counted twice"


# --- ADR-006: one stack (ai/rag), reranking through the router, query rewrite ------------------------------


def _router_with_reranker(scorer, seen):
    from types import SimpleNamespace

    from ai.providers.contracts.reranking import RerankResponse

    class Provider:
        def rerank(self, request):
            seen.append(request)
            scores = [(doc_id, scorer(text)) for doc_id, text in request.documents]
            return RerankResponse(scores=tuple(sorted(scores, key=lambda pair: -pair[1])), model="fake-cross-encoder")

    class Router:
        def route(self, task, call, idempotent=None):
            assert task == "rerank"
            return SimpleNamespace(value=call(Provider()))

    return Router()


def test_reranking_goes_through_the_router_and_reorders_the_window(client, session_factory, monkeypatch):
    from api_contract import assert_contract_component

    _seed(session_factory)
    plain = client.get("/api/search", params={"q": "flame", "type": "document"}).json()
    assert [r["result_id"] for r in plain["results"]] == ["c0", "c1", "c2"]
    assert plain["retrieval"]["reranking"] == {"status": "disabled", "model": None, "depth": None}

    seen = []
    monkeypatch.setattr(main.settings, "reranker_enabled", True)
    monkeypatch.setattr(main.ai_runtime, "get_router", lambda *_: _router_with_reranker(lambda text: float("once" in text), seen))
    body = client.get("/api/search", params={"q": "flame", "type": "document"}).json()

    assert_contract_component(body["retrieval"], "RetrievalInfo")   # this fixture's IDs are not contract-shaped
    assert [r["result_id"] for r in body["results"]] == ["c2", "c0", "c1"]
    assert [r["rank"] for r in body["results"]] == [1, 2, 3]
    assert [r["score"] for r in body["results"]] == [r["score"] for r in plain["results"]], "the window keeps its score slots"
    assert body["retrieval"]["reranking"] == {"status": "applied", "model": "fake-cross-encoder", "depth": 10}
    assert seen[0].query == "flame" and [doc_id for doc_id, _ in seen[0].documents] == ["c0", "c1", "c2"]
    assert seen[0].documents[0][1] == "flame flame flame spread", "the reranker scores the chunk text"


def test_a_reranker_the_router_cannot_reach_leaves_the_fused_order(client, session_factory, monkeypatch, caplog):
    from ai.routing import ExecutionMode, NoCompatibleProvider

    class Router:
        def route(self, task, call, idempotent=None):
            raise NoCompatibleProvider(task, ExecutionMode.LOCAL_FIRST, [{"provider": "cross_encoder", "reason": "model_missing"}])

    _seed(session_factory)
    monkeypatch.setattr(main.settings, "reranker_enabled", True)
    monkeypatch.setattr(main.ai_runtime, "get_router", lambda *_: Router())
    response = client.get("/api/search", params={"q": "flame", "type": "document"})

    assert response.status_code == 200
    assert [r["result_id"] for r in response.json()["results"]] == ["c0", "c1", "c2"]
    assert response.json()["retrieval"]["reranking"] == {"status": "unavailable", "model": None, "depth": 10}
    assert "rerank=unavailable" in caplog.text


def test_reranked_pages_are_slices_of_one_order(client, session_factory, monkeypatch):
    _seed_many(session_factory, 12)
    monkeypatch.setattr(main.settings, "reranker_enabled", True)
    monkeypatch.setattr(main.settings, "rerank_depth", 5)
    monkeypatch.setattr(main.ai_runtime, "get_router", lambda *_: _router_with_reranker(lambda text: float(len(text)), []))

    whole = [r["result_id"] for r in client.get("/api/search", params={"q": "flame", "type": "document", "page_size": 12}).json()["results"]]
    paged = [r["result_id"] for page in (1, 2, 3)
             for r in client.get("/api/search", params={"q": "flame", "type": "document", "page": page, "page_size": 4}).json()["results"]]
    assert paged == whole and len(set(whole)) == 12


def test_the_rewritten_query_is_embedded_and_reported_next_to_the_original(client, session_factory, monkeypatch):
    _seed(session_factory)
    embedded = []
    monkeypatch.setattr(main, "index_status", lambda session: {"state": "up", "version": "kv-test"})
    monkeypatch.setattr(main, "search_chunks", lambda session, query, limit=20, **_: embedded.append(query) or [("c3", 0.9)])

    body = client.get("/api/search", params={"q": "ISS flame", "type": "document"}).json()

    assert body["query"] == "ISS flame"
    assert embedded == ["ISS (international space station) flame"]
    assert body["retrieval"]["query_rewrite"] == {
        "rewritten": "ISS (international space station) flame", "changed": True, "rules_applied": ["expand:iss"],
        "rewriter_version": "1.0.1", "used_for": ["semantic"]}
    assert body["retrieval"]["stack_version"] == "flame-search-2.0.0"
