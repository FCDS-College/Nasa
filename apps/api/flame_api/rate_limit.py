"""Per-client token buckets for /api/* (P2-2).

Each client identity (a client name, `legacy-read`, `legacy-write`, or `anonymous` when auth is
off) has its own bucket per class of request: `read`, `write` and `chat`. A bucket holds up to one
minute's allowance and refills continuously, so a burst is allowed but the sustained rate is the
configured per-minute limit. State lives in Redis so every API process shares it.

Redis being unreachable must not take the API down: `check` then returns None (fail open), and the
caller applies the in-process chat limit instead. After a failure Redis is not retried for a few
seconds, so an outage costs one connect timeout per window, not one per request.
"""

from __future__ import annotations

import logging
import math
import time
from threading import Lock
from typing import Protocol

logger = logging.getLogger("flame_api.rate_limit")

KEY_PREFIX = "flame:ratelimit"
RETRY_REDIS_AFTER_S = 5.0
WARN_EVERY_S = 60.0

# KEYS[1] = bucket; ARGV = capacity, refill tokens/s, now (s). Returns {allowed, wait_s as string}
# (a Lua number would be truncated to an integer on the way out).
_TOKEN_BUCKET = """
local capacity = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local state = redis.call('HMGET', KEYS[1], 'tokens', 'ts')
local tokens = tonumber(state[1])
local ts = tonumber(state[2])
if tokens == nil or ts == nil then
  tokens = capacity
  ts = now
end
tokens = math.min(capacity, tokens + math.max(0, now - ts) * rate)
local allowed = 0
local wait = 0
if tokens >= 1 then
  tokens = tokens - 1
  allowed = 1
else
  wait = (1 - tokens) / rate
end
redis.call('HSET', KEYS[1], 'tokens', tostring(tokens), 'ts', tostring(now))
redis.call('EXPIRE', KEYS[1], math.ceil(capacity / rate) + 1)
return {allowed, tostring(wait)}
"""


class Backend(Protocol):
    def take(self, key: str, capacity: int, rate_per_s: float, now: float) -> float:
        """Take one token. Returns 0.0 if allowed, otherwise the seconds until one is available."""


class RedisBackend:
    def __init__(self, url: str):
        from redis import Redis

        self._redis = Redis.from_url(url, socket_connect_timeout=0.25, socket_timeout=0.25, retry_on_timeout=False)
        self._script = self._redis.register_script(_TOKEN_BUCKET)

    def take(self, key: str, capacity: int, rate_per_s: float, now: float) -> float:
        allowed, wait = self._script(keys=[key], args=[capacity, rate_per_s, now])
        return 0.0 if int(allowed) == 1 else max(float(wait), 0.0)


class MemoryBackend:
    """The same bucket arithmetic in process. Used by tests; not shared between API processes."""

    def __init__(self):
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = Lock()

    def take(self, key: str, capacity: int, rate_per_s: float, now: float) -> float:
        with self._lock:
            tokens, ts = self._buckets.get(key, (float(capacity), now))
            tokens = min(capacity, tokens + max(0.0, now - ts) * rate_per_s)
            if tokens >= 1:
                self._buckets[key] = (tokens - 1, now)
                return 0.0
            self._buckets[key] = (tokens, now)
            return (1 - tokens) / rate_per_s


_backend: Backend | None = None
_backend_url: str | None = None
_down_until = 0.0
_last_warning = 0.0
_state_lock = Lock()


def set_backend(backend: Backend | None) -> None:
    """Inject a backend (tests). None goes back to Redis at the configured URL."""
    global _backend, _backend_url, _down_until, _last_warning
    with _state_lock:
        _backend, _backend_url, _down_until, _last_warning = backend, None if backend is None else "injected", 0.0, 0.0


def _get_backend(redis_url: str) -> Backend:
    global _backend, _backend_url
    with _state_lock:
        if _backend is None or (_backend_url != "injected" and _backend_url != redis_url):
            _backend, _backend_url = RedisBackend(redis_url), redis_url
        return _backend


def check(identity: str, bucket: str, per_minute: int, *, redis_url: str) -> int | None:
    """0 if the request may proceed, else whole seconds for Retry-After; None if Redis is unavailable."""
    global _down_until, _last_warning
    now = time.time()
    if now < _down_until:
        return None
    try:
        wait = _get_backend(redis_url).take(f"{KEY_PREFIX}:{bucket}:{identity}", per_minute, per_minute / 60.0, now)
    except Exception as error:  # redis.RedisError, OSError, a bad URL: all mean "no shared limiter"
        with _state_lock:
            _down_until = now + RETRY_REDIS_AFTER_S
            warn = now - _last_warning >= WARN_EVERY_S
            if warn:
                _last_warning = now
        if warn:
            logger.warning("rate_limit_backend_unavailable error=%s action=fail_open", type(error).__name__)
        return None
    return 0 if wait <= 0 else max(1, math.ceil(wait))
