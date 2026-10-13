"""OpenTelemetry setup (M12, docs/operations/OBSERVABILITY.md).

Off by default. With FLAME_OTEL_ENABLED=true and the ``observability`` extra installed, spans are
exported over OTLP/HTTP to OTEL_EXPORTER_OTLP_ENDPOINT (standard OTel variable), or printed to the
console when no endpoint is set. Span path: http.request → chat.retrieve / chat.generate →
router.route → provider.<name>; retrieval.vector for semantic search.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from ai.routing import tracing

logger = logging.getLogger("flame_api")
span = tracing.span
set_attributes = tracing.set_attributes


def setup(service_name: str, *, enabled: bool, exporter: Any = None) -> bool:
    """Install a tracer provider. Returns False (and stays a no-op) when disabled or not installed."""
    if not enabled:
        return False
    try:
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor
    except ImportError:
        logger.warning("otel_requested_but_not_installed install apps/api[observability]")
        return False
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    if exporter is not None:
        provider.add_span_processor(SimpleSpanProcessor(exporter))
    elif os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    tracing.enable(provider.get_tracer("flame_api"))
    logger.info("otel_enabled service=%s", service_name)
    return True
