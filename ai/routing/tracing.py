"""Optional OpenTelemetry spans for the AI path (M12, L-9). Stdlib-only until enabled.

``flame_api.telemetry.setup`` calls ``enable(tracer)`` when FLAME_OTEL_ENABLED=true and the SDK is
installed; until then every ``span`` is a no-op, so the router has no hard dependency on OTel.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

_tracer: Any = None


def enable(tracer: Any) -> None:
    global _tracer
    _tracer = tracer


def disable() -> None:
    enable(None)


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[Any]:
    if _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(name) as current:
        for key, value in attributes.items():
            if value is not None:
                current.set_attribute(key, value if isinstance(value, (str, bool, int, float)) else str(value))
        yield current


def set_attributes(current: Any, **attributes: Any) -> None:
    if current is None:
        return
    for key, value in attributes.items():
        if value is not None:
            current.set_attribute(key, value if isinstance(value, (str, bool, int, float)) else str(value))
