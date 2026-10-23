"""Provider health: bounded cached probes and a per-provider circuit breaker.

Probes never run on the request path. ``/api/health`` and ``/api/ai/providers`` refresh them;
requests consult only the cached state and the breaker, so a dead provider costs at most one
failed call per cooldown window, not a timeout on every request.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from ai.providers.contracts.base import HealthStatus, Provider

Clock = Callable[[], float]


@dataclass
class _BreakerState:
    failures: int = 0
    opened_at: float | None = None
    trial_in_flight: bool = False


class CircuitBreaker:
    """closed → (threshold consecutive failures) → open → (cooldown) → half-open → one trial call."""

    def __init__(self, *, threshold: int = 3, cooldown_s: float = 30.0, clock: Clock = time.monotonic) -> None:
        self.threshold = max(1, threshold)
        self.cooldown_s = cooldown_s
        self._clock = clock
        self._state: dict[str, _BreakerState] = {}
        self._lock = threading.Lock()

    def state(self, name: str) -> str:
        with self._lock:
            entry = self._state.get(name)
            if entry is None or entry.opened_at is None:
                return "closed"
            return "half_open" if self._clock() - entry.opened_at >= self.cooldown_s else "open"

    def allow(self, name: str) -> bool:
        """closed → True. open → False. half-open → True for exactly one caller (the trial) until it reports."""
        with self._lock:
            entry = self._state.get(name)
            if entry is None or entry.opened_at is None:
                return True
            if self._clock() - entry.opened_at < self.cooldown_s or entry.trial_in_flight:
                return False
            entry.trial_in_flight = True
            return True

    def release(self, name: str) -> None:
        """Give back a half-open trial that ended without a verdict (our own bad request, an unexpected error)."""
        with self._lock:
            entry = self._state.get(name)
            if entry is not None:
                entry.trial_in_flight = False

    def record_success(self, name: str) -> None:
        with self._lock:
            self._state[name] = _BreakerState()

    def record_failure(self, name: str) -> None:
        with self._lock:
            entry = self._state.setdefault(name, _BreakerState())
            entry.trial_in_flight = False
            entry.failures += 1
            if entry.failures >= self.threshold or entry.opened_at is not None:
                entry.opened_at = self._clock()   # (re)open; a failed half-open trial restarts the cooldown

    def snapshot(self) -> dict[str, dict]:
        with self._lock:
            names = list(self._state)
        return {name: {"state": self.state(name), "failures": self._state[name].failures} for name in names}


class HealthMonitor:
    def __init__(self, *, probe_timeout_s: float = 2.0, ttl_s: float = 15.0, clock: Clock = time.monotonic) -> None:
        self.probe_timeout_s = min(probe_timeout_s, 5.0)
        self.ttl_s = ttl_s
        self._clock = clock
        self._cache: dict[str, tuple[float, HealthStatus]] = {}
        self._lock = threading.Lock()

    def cached(self, name: str) -> HealthStatus:
        with self._lock:
            entry = self._cache.get(name)
        if entry is None or self._clock() - entry[0] > self.ttl_s:
            return HealthStatus("unknown")
        return entry[1]

    def probe(self, provider: Provider, *, force: bool = False) -> HealthStatus:
        name = provider.info.name
        if not force:
            with self._lock:
                entry = self._cache.get(name)
            if entry is not None and self._clock() - entry[0] <= self.ttl_s:
                return entry[1]
        try:
            status = provider.health(self.probe_timeout_s)
        except Exception:  # a probe must never take the caller down with it
            status = HealthStatus("down", None, "probe_failed")
        with self._lock:
            self._cache[name] = (self._clock(), status)
        return status

    def mark(self, name: str, status: HealthStatus) -> None:
        with self._lock:
            self._cache[name] = (self._clock(), status)
