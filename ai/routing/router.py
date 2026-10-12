"""The one router (M1 = 2H Task 3): pick a permitted, compatible, healthy provider and fall back safely.

Flow: task → required capability/modality → mode filter (egress guard) → circuit breaker and cached
health → call → on a fallback-eligible failure, the next candidate (each provider at most once per
request, so no loops) → ``Routed(value, ExecutionMetadata)`` or ``NoCompatibleProvider``.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Generic, TypeVar

from ai.providers.contracts.base import Provider
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
from ai.providers.contracts.metadata import ExecutionMetadata
from ai.routing.health import CircuitBreaker, HealthMonitor
from ai.routing.policies import TASKS, ExecutionMode, compatible, order, permitted
from ai.routing.registry import ProviderRegistry
from ai.routing.tracing import set_attributes, span

logger = logging.getLogger("flame_api")
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Routed(Generic[T]):
    value: T
    metadata: ExecutionMetadata


class NoCompatibleProvider(Exception):
    """No permitted, healthy provider could serve the task. ``reasons`` say why, per provider."""

    def __init__(self, task: str, mode: ExecutionMode, reasons: list[dict], *, last_error: ProviderError | None = None) -> None:
        super().__init__(f"No provider could serve {task} in {mode.value} mode.")
        self.task = task
        self.mode = mode
        self.reasons = reasons
        self.last_error = last_error

    @property
    def status_code(self) -> int | None:  # parity with the old AuraIntegrationError for log lines
        return self.last_error.status_code if self.last_error else None

    def to_dict(self) -> dict:
        return {"task": self.task, "mode": self.mode.value, "reasons": list(self.reasons)}


class Router:
    def __init__(
        self,
        registry: ProviderRegistry,
        *,
        mode: ExecutionMode = ExecutionMode.LOCAL_FIRST,
        breaker: CircuitBreaker | None = None,
        monitor: HealthMonitor | None = None,
        mode_source: Callable[[], ExecutionMode | None] | None = None,
    ) -> None:
        self.registry = registry
        self._mode = ExecutionMode(mode)
        self._mode_source = mode_source
        self.breaker = breaker or CircuitBreaker()
        self.monitor = monitor or HealthMonitor()
        self.stats: Counter[str] = Counter()
        self._lock = threading.Lock()

    # ----------------------------------------------------------------- mode
    @property
    def mode(self) -> ExecutionMode:
        if self._mode_source is not None:
            override = self._mode_source()
            if override is not None:
                return ExecutionMode(override)
        return self._mode

    def set_mode(self, mode: ExecutionMode) -> None:
        self._mode = ExecutionMode(mode)

    # ----------------------------------------------------------- inspection
    def candidates(self, task_name: str) -> list[Provider]:
        task = TASKS[task_name]
        return order([(p, prov) for p, prov in self.registry.all() if compatible(prov, task)], self.mode)

    def available(self, task_name: str) -> bool:
        """True when at least one compatible provider is permitted in the current mode."""
        mode = self.mode
        return any(permitted(p, mode) for p in self.candidates(task_name))

    def refresh_health(self, *, force: bool = True) -> None:
        providers = [p for _, p in self.registry.all()]
        if not providers:
            return
        mode = self.mode
        with ThreadPoolExecutor(max_workers=min(8, len(providers))) as pool:
            # Never probe an external provider in offline_only: a probe is egress too.
            list(pool.map(lambda p: self.monitor.probe(p, force=force) if permitted(p, mode) else None, providers))

    def status(self) -> dict:
        mode = self.mode
        providers = []
        for priority, provider in self.registry.all():
            info = provider.info
            allowed = permitted(provider, mode)
            health = self.monitor.cached(info.name) if allowed else None
            providers.append({
                "name": info.name,
                "runtime": info.runtime,
                "locality": info.locality.value,
                "capabilities": sorted(c.value for c in info.capabilities),
                "model": info.model,
                "version": info.version,
                "priority": priority,
                "permitted": allowed,
                "health": {"state": health.state, "latency_ms": health.latency_ms, "detail": health.detail,
                           "model_present": health.model_present} if health else {"state": "blocked", "latency_ms": None,
                                                                                   "detail": "egress_blocked", "model_present": None},
                "circuit": self.breaker.state(info.name),
            })
        with self._lock:
            counters = dict(self.stats)
        return {"mode": mode.value, "providers": providers, "decisions": counters}

    # --------------------------------------------------------------- route
    def _count(self, task: str, provider: str, outcome: str) -> None:
        with self._lock:
            self.stats[f"{task}|{provider}|{outcome}"] += 1

    def route(self, task_name: str, call: Callable[[Provider], T], *, idempotent: bool | None = None) -> Routed[T]:
        with span("router.route", **{"flame.task": task_name, "flame.mode": self.mode.value}) as current:
            routed = self._route(task_name, call, idempotent)
            set_attributes(current, **{"flame.provider": routed.metadata.provider, "flame.locality": routed.metadata.locality,
                                       "flame.fallback_used": routed.metadata.fallback_used})
            return routed

    def _route(self, task_name: str, call: Callable[[Provider], T], idempotent: bool | None) -> Routed[T]:
        task = TASKS[task_name]
        idempotent = task.idempotent if idempotent is None else idempotent
        mode = self.mode
        ordered = self.candidates(task_name)
        reasons: list[dict] = []
        attempts: list[dict] = []
        visited: set[str] = set()
        last_error: ProviderError | None = None
        if not ordered:
            reasons.append({"provider": None, "reason": "no_provider_for_capability"})

        for provider in ordered:
            name = provider.info.name
            if name in visited:          # loop guard: one try per provider per request
                continue
            visited.add(name)
            if not permitted(provider, mode):
                reasons.append({"provider": name, "reason": "egress_blocked"})
                continue
            if not self.breaker.allow(name):
                reasons.append({"provider": name, "reason": "circuit_open"})
                continue
            cached = self.monitor.cached(name)
            if cached.state == "down":
                reasons.append({"provider": name, "reason": f"health_down:{cached.detail or 'unknown'}"})
                continue

            started = time.perf_counter()
            try:
                with span(f"provider.{name}", **{"flame.provider": name, "flame.locality": provider.info.locality.value,
                                                 "flame.model": provider.info.model, "flame.task": task_name}):
                    value = call(provider)
            except ProviderError as exc:
                last_error = exc
                if exc.code is not ProviderErrorCode.INVALID_REQUEST:
                    self.breaker.record_failure(name)
                attempts.append({"provider": name, "code": exc.code.value})
                reasons.append({"provider": name, "reason": exc.code.value})
                self._count(task_name, name, exc.code.value)
                logger.warning("routing_attempt_failed task=%s mode=%s provider=%s code=%s status=%s",
                               task_name, mode.value, name, exc.code.value, exc.status_code)
                if not exc.fallback_eligible:
                    break
                if not idempotent and exc.request_sent:
                    reasons.append({"provider": name, "reason": "not_idempotent_after_send"})
                    break
                continue

            self.breaker.record_success(name)
            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            fallback_used = bool(attempts) or bool(reasons)
            routing_reason = "preferred" if not fallback_used else "fallback_after:" + ",".join(
                f"{r['provider']}:{r['reason']}" for r in reasons if r["provider"])
            metadata = ExecutionMetadata(
                task=task_name, provider=name, runtime=provider.info.runtime, model=provider.info.model,
                version=provider.info.version, locality=provider.info.locality.value, mode=mode.value,
                fallback_used=fallback_used, routing_reason=routing_reason, latency_ms=latency_ms,
                attempts=tuple(attempts),
            )
            self._count(task_name, name, "ok")
            logger.info("routing_decision task=%s mode=%s provider=%s locality=%s fallback=%s reason=%s latency_ms=%s",
                        task_name, mode.value, name, metadata.locality, fallback_used, routing_reason, latency_ms)
            return Routed(value=value, metadata=metadata)

        self._count(task_name, "-", "no_provider")
        logger.warning("routing_exhausted task=%s mode=%s reasons=%s", task_name, mode.value, reasons)
        raise NoCompatibleProvider(task_name, mode, reasons, last_error=last_error)
