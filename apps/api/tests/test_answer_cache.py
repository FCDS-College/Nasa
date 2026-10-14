"""CAG on /api/chat: Flame's own cache_hit, version-keyed, never serving a stale knowledge version."""
from flame_api import answer_cache, knowledge_version, main
from ai.providers import http as provider_http

from test_chat import EVIDENCE_ID, FakeResponse, aura_reply, chat_settings, corpus  # noqa: F401


def _ask(client):
    return client.post("/api/chat", json={"query": "How does n-heptane behave in microgravity?"}).json()


def test_second_identical_question_is_served_from_flame_cache(client, corpus, monkeypatch):  # noqa: F811
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(1)
        return FakeResponse(aura_reply("A cool flame was simulated for n-heptane.", [EVIDENCE_ID]))

    monkeypatch.setattr(main, "settings", chat_settings())
    monkeypatch.setattr(provider_http, "urlopen", fake_urlopen)

    first = _ask(client)
    assert first["cache_hit"] is False and first["warnings"] == []
    calls_after_first = len(calls)
    second = _ask(client)

    assert second["cache_hit"] is True
    assert second["answer"] == first["answer"] and second["sources"] == first["sources"]
    assert second["request_id"] != first["request_id"]
    assert len(calls) == calls_after_first, "a cache hit must not call any model"
    assert answer_cache.metrics()["hits"] == 1


def test_publishing_a_new_knowledge_version_stops_stale_answers(client, corpus, session_factory, monkeypatch):  # noqa: F811
    monkeypatch.setattr(main, "settings", chat_settings())
    monkeypatch.setattr(provider_http, "urlopen", lambda request, timeout: FakeResponse(aura_reply("Cool flame.", [EVIDENCE_ID])))

    with session_factory() as session:
        knowledge_version.publish(session, "v1", trigger="manual")
    assert _ask(client)["cache_hit"] is False
    assert _ask(client)["cache_hit"] is True

    with session_factory() as session:
        knowledge_version.publish(session, "v2", trigger="manual")
    assert _ask(client)["cache_hit"] is False
    assert answer_cache.metrics()["entries"] == 1, "entries of the old version are removed"


def test_answers_with_warnings_are_not_cached(client, corpus, monkeypatch):  # noqa: F811
    monkeypatch.setattr(main, "settings", chat_settings())
    monkeypatch.setattr(provider_http, "urlopen", lambda request, timeout: FakeResponse(aura_reply("No evidence.", [])))

    _ask(client)
    assert _ask(client)["cache_hit"] is False
    assert answer_cache.metrics()["entries"] == 0
