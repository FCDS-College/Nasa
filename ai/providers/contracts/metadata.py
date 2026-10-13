"""Execution metadata attached to every routed response (2H Task 3, H-4)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True, slots=True)
class ExecutionMetadata:
    task: str
    provider: str
    runtime: str
    model: str | None
    version: str | None
    locality: str                # "local" | "external"
    mode: str                    # execution mode in force when the request ran
    fallback_used: bool
    routing_reason: str          # e.g. "preferred", "fallback_after:aura:unavailable"
    latency_ms: float
    attempts: tuple[dict, ...] = field(default_factory=tuple)   # [{"provider","code"}] of earlier failures

    def to_dict(self) -> dict:
        data = asdict(self)
        data["attempts"] = [dict(a) for a in self.attempts]
        return data
