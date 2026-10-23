"""L-9: one request produces the documented span path, tied together by request_id."""
import pytest

pytest.importorskip("opentelemetry.sdk")

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter  # noqa: E402

from ai.routing import tracing  # noqa: E402
from flame_api import telemetry  # noqa: E402


@pytest.fixture
def spans():
    exporter = InMemorySpanExporter()
    assert telemetry.setup("flame-api-test", enabled=True, exporter=exporter)
    yield exporter
    tracing.disable()


def test_disabled_telemetry_is_a_no_op():
    assert telemetry.setup("x", enabled=False) is False
    with telemetry.span("anything", a=1) as current:
        assert current is None


def test_a_routed_call_produces_router_and_provider_spans(spans):
    from ai.providers.contracts.base import Capability, HealthStatus, Locality, ProviderInfo
    from ai.routing import ProviderRegistry, Router

    class Local:
        info = ProviderInfo(name="ollama", runtime="ollama", locality=Locality.LOCAL,
                            capabilities=frozenset({Capability.STRUCTURED}), model="m")

        def health(self, timeout_s):
            return HealthStatus("up")

    registry = ProviderRegistry()
    registry.register(Local())
    with telemetry.span("http.request", **{"flame.request_id": "req_1"}):
        Router(registry).route("chat.answer", lambda provider: "ok")

    finished = {s.name: s for s in spans.get_finished_spans()}
    assert {"http.request", "router.route", "provider.ollama"} <= set(finished)
    assert finished["router.route"].attributes["flame.provider"] == "ollama"
    assert finished["provider.ollama"].attributes["flame.locality"] == "local"
    trace_ids = {s.context.trace_id for s in finished.values()}
    assert len(trace_ids) == 1, "one request, one trace"


def test_http_requests_are_spanned_with_the_request_id(spans, client):
    response = client.get("/api/documents")
    names = {s.name: s for s in spans.get_finished_spans()}
    assert names["http.request"].attributes["flame.request_id"] == response.headers["X-Request-ID"]
    assert names["http.request"].attributes["http.status_code"] == 200
