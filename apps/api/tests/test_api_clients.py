"""Per-client API keys (P2-1) and per-client rate limits (P2-2)."""

import logging
import os

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from flame_api import clients, main, rate_limit
from flame_api.models import ApiClient, AuditEvent

READ_TOKEN = os.environ["FLAME_READ_API_TOKEN"]
WRITE_TOKEN = os.environ["FLAME_WRITE_API_TOKEN"]


def bearer(key):
    return {"Authorization": f"Bearer {key}"}


@pytest.fixture
def make_client(session_factory):
    def make(name, scopes=("read",)):
        with session_factory() as session:
            _, key = clients.create_client(session, name, list(scopes))
        return key

    return make


def stored(session_factory, name):
    with session_factory() as session:
        return session.scalar(select(ApiClient).where(ApiClient.name == name))


# --- P2-1: keys, scopes, revocation -------------------------------------------------------------


def test_a_key_is_stored_only_as_its_hash(session_factory, make_client):
    key = make_client("web")
    record = stored(session_factory, "web")

    assert key.startswith("flk_") and len(key) > 40
    assert record.key_hash == clients.hash_key(key) and key not in record.key_hash
    assert record.scopes == ["read"] and record.revoked_at is None and record.last_used_at is None


def test_names_and_scopes_are_validated(session_factory, make_client):
    make_client("web")
    with session_factory() as session:
        for name, scopes in (("web", ["read"]), ("Web Server", ["read"]), ("legacy-read", ["read"]),
                             ("anonymous", ["read"]), ("aura", []), ("aura", ["admin"])):
            with pytest.raises(clients.ClientError):
                clients.create_client(session, name, scopes)


def test_a_read_key_reads_and_cannot_write(client, make_client):
    key = make_client("web")

    assert client.get("/api/documents", headers=bearer(key)).status_code == 200
    forbidden = client.post("/api/analyses", headers=bearer(key))
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"


def test_a_write_key_writes_and_cannot_read(client, make_client):
    key = make_client("ops", scopes=("write",))

    assert client.get("/api/documents", headers=bearer(key)).status_code == 403
    # Past auth: the empty upload is a validation error, not 401/403.
    assert client.post("/api/analyses", headers=bearer(key)).status_code == 400


def test_unknown_and_revoked_keys_are_refused(client, session_factory, make_client):
    key = make_client("aura")
    assert client.get("/api/documents", headers=bearer(key)).status_code == 200

    with session_factory() as session:
        clients.revoke_client(session, "aura")

    for supplied in (key, key + "x", "flk_not-a-key", ""):
        response = client.get("/api/documents", headers=bearer(supplied))
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
        assert response.headers["WWW-Authenticate"] == "Bearer"


def test_legacy_tokens_still_work_with_their_old_scopes(client):
    assert client.get("/api/documents", headers=bearer(READ_TOKEN)).status_code == 200
    assert client.get("/api/documents", headers=bearer(WRITE_TOKEN)).status_code == 401
    assert client.post("/api/analyses", headers=bearer(READ_TOKEN)).status_code == 401
    assert client.post("/api/analyses", headers=bearer(WRITE_TOKEN)).status_code == 400


def test_the_client_name_is_in_the_request_log(client, make_client, caplog):
    key = make_client("web")
    with caplog.at_level(logging.INFO, logger="flame_api"):
        client.get("/api/documents", headers=bearer(key))
        client.get("/api/documents", headers=bearer(READ_TOKEN))
        client.get("/api/documents", headers=bearer("wrong"))

    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("request_id=") and "path=/api/documents" in r.getMessage()]
    assert [line.split(" ")[1] for line in lines] == ["client=web", "client=legacy-read", "client=-"]
    assert key not in caplog.text


def test_last_used_at_is_written_at_most_once_a_minute(client, session_factory, make_client, monkeypatch):
    key = make_client("web")
    client.get("/api/documents", headers=bearer(key))
    first = stored(session_factory, "web").last_used_at
    assert first is not None

    client.get("/api/documents", headers=bearer(key))
    assert stored(session_factory, "web").last_used_at == first

    monkeypatch.setattr(clients, "TOUCH_INTERVAL_S", 0.0)
    client.get("/api/documents", headers=bearer(key))
    assert stored(session_factory, "web").last_used_at > first


def test_a_client_key_needs_the_database_but_legacy_tokens_do_not(client, monkeypatch):
    def unavailable(key):
        raise OperationalError("SELECT", {}, Exception("down"))

    monkeypatch.setattr(main, "_lookup_client", unavailable)

    response = client.get("/api/documents", headers=bearer("flk_anything"))
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert client.get("/api/documents", headers=bearer(READ_TOKEN)).status_code == 200


def test_the_audit_actor_is_the_client_name(client, session_factory, make_client):
    key = make_client("ops", scopes=("write",))

    assert client.put("/api/admin/ai/mode", json={"mode": "offline_only"}, headers=bearer(key)).status_code == 200
    assert client.put("/api/admin/ai/mode", json={"mode": "local_first"}, headers=bearer(WRITE_TOKEN)).status_code == 200

    with session_factory() as session:
        actors = list(session.scalars(select(AuditEvent.actor).order_by(AuditEvent.occurred_at)))
    assert actors == ["ops", "write-token"]


def test_the_cli_creates_lists_and_revokes(session_factory, monkeypatch, capsys):
    from flame_api import database

    monkeypatch.setattr(database, "SessionLocal", session_factory)

    assert clients.main(["create", "aura", "--scopes", "read"]) == 0
    key = capsys.readouterr().out.strip().splitlines()[-1]
    assert stored(session_factory, "aura").key_hash == clients.hash_key(key)

    assert clients.main(["list"]) == 0
    listing = capsys.readouterr().out
    assert "aura" in listing and key not in listing and clients.hash_key(key) not in listing

    assert clients.main(["revoke", "aura"]) == 0
    assert stored(session_factory, "aura").revoked_at is not None
    assert clients.main(["revoke", "nobody"]) == 2
    assert clients.main(["create", "aura"]) == 2


# --- P2-2: per-client rate limits ---------------------------------------------------------------


def test_one_client_cannot_exhaust_another_clients_budget(client, make_client, monkeypatch):
    monkeypatch.setattr(main.settings, "read_rate_limit_per_minute", 3)
    noisy, quiet = make_client("noisy"), make_client("quiet")

    assert [client.get("/api/documents", headers=bearer(noisy)).status_code for _ in range(3)] == [200, 200, 200]
    limited = client.get("/api/documents", headers=bearer(noisy))

    assert limited.status_code == 429
    assert 1 <= int(limited.headers["Retry-After"]) <= 20
    error = limited.json()["error"]
    assert error["code"] == "RATE_LIMITED" and error["retryable"] is True and error["request_id"] == limited.headers["X-Request-ID"]
    assert error["details"]["limit_per_minute"] == 3
    # Another client key and the legacy token each have their own bucket.
    assert [client.get("/api/documents", headers=bearer(quiet)).status_code for _ in range(3)] == [200, 200, 200]
    assert client.get("/api/documents", headers=bearer(READ_TOKEN)).status_code == 200


def test_reads_writes_and_chat_have_separate_budgets(client, make_client, monkeypatch):
    monkeypatch.setattr(main.settings, "read_rate_limit_per_minute", 1)
    monkeypatch.setattr(main.settings, "write_rate_limit_per_minute", 1)
    key = make_client("both", scopes=("read", "write"))

    assert client.get("/api/documents", headers=bearer(key)).status_code == 200
    assert client.get("/api/documents", headers=bearer(key)).status_code == 429
    assert client.post("/api/analyses", headers=bearer(key)).status_code == 400
    assert client.post("/api/analyses", headers=bearer(key)).status_code == 429
    # Chat has its own bucket (it fails later for want of a model, but it is not rate-limited).
    assert client.post("/api/chat", json={"query": "n-heptane"}, headers=bearer(key)).status_code != 429


def test_health_is_never_rate_limited(client, monkeypatch):
    monkeypatch.setattr(main.settings, "read_rate_limit_per_minute", 1)

    assert {client.get("/api/health").status_code for _ in range(3)} <= {200, 503}
    assert client.get("/health/live").status_code == 200
    assert client.get("/api/documents").status_code == 200
    assert client.get("/api/documents").status_code == 429


def test_the_bucket_refills(monkeypatch):
    backend = rate_limit.MemoryBackend()
    rate_limit.set_backend(backend)
    clock = [1000.0]
    monkeypatch.setattr(rate_limit.time, "time", lambda: clock[0])

    assert rate_limit.check("web", "read", 60, redis_url="unused") == 0
    assert rate_limit.check("web", "read", 1, redis_url="unused") == 0
    assert rate_limit.check("web", "chat", 1, redis_url="unused") == 0
    assert rate_limit.check("web", "chat", 1, redis_url="unused") == 60
    clock[0] += 30
    assert rate_limit.check("web", "chat", 1, redis_url="unused") == 30
    clock[0] += 31
    assert rate_limit.check("web", "chat", 1, redis_url="unused") == 0


class _DownBackend:
    calls = 0

    def take(self, *args):
        type(self).calls += 1
        raise ConnectionError("redis is down")


def test_an_unreachable_redis_fails_open_with_a_warning(client, monkeypatch, caplog):
    monkeypatch.setattr(main.settings, "read_rate_limit_per_minute", 1)
    _DownBackend.calls = 0
    rate_limit.set_backend(_DownBackend())

    with caplog.at_level(logging.WARNING, logger="flame_api.rate_limit"):
        statuses = [client.get("/api/documents").status_code for _ in range(5)]

    assert statuses == [200] * 5
    warnings = [r for r in caplog.records if "rate_limit_backend_unavailable" in r.getMessage()]
    assert len(warnings) == 1
    # Redis is not retried on every request while it is down.
    assert _DownBackend.calls == 1


def test_rate_limits_apply_without_auth_as_one_anonymous_client(client, monkeypatch):
    monkeypatch.setattr(main.settings, "api_auth_enabled", False)
    monkeypatch.setattr(main.settings, "read_rate_limit_per_minute", 1)

    assert client.get("/api/documents", headers={"Authorization": ""}).status_code == 200
    assert client.get("/api/documents", headers={"Authorization": ""}).status_code == 429


@pytest.mark.skipif(not os.environ.get("FLAME_TEST_REDIS_URL"), reason="set FLAME_TEST_REDIS_URL (e.g. redis://localhost:6379/1) to run the Lua bucket against Redis")
def test_the_redis_bucket_matches_the_in_process_one():
    from redis import Redis

    url = os.environ["FLAME_TEST_REDIS_URL"]
    backend = rate_limit.RedisBackend(url)
    key = "flame:ratelimit:test:redis-bucket"
    Redis.from_url(url).delete(key)
    try:
        assert [backend.take(key, 2, 2 / 60, 1000.0) for _ in range(2)] == [0.0, 0.0]
        assert backend.take(key, 2, 2 / 60, 1000.0) == pytest.approx(30.0)
        assert backend.take(key, 2, 2 / 60, 1031.0) == 0.0
        assert 0 < Redis.from_url(url).ttl(key) <= 61
    finally:
        Redis.from_url(url).delete(key)
