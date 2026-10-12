"""Model router behaviour (Phase 2 M1 / 2H Task 3). Fake providers; no network, no models."""
import pytest

from ai.providers.contracts.base import Capability, HealthStatus, Locality, ProviderInfo
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
from ai.routing import CircuitBreaker, ExecutionMode, HealthMonitor, NoCompatibleProvider, ProviderRegistry, Router
from ai.routing.registry import load_manifest


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class Fake:
    def __init__(self, name, locality, caps=(Capability.STRUCTURED,), modalities=("text",), fail=None, health="up"):
        self.info = ProviderInfo(name=name, runtime=name, locality=locality, capabilities=frozenset(caps),
                                 model=f"{name}-model", modalities=frozenset(modalities))
        self.fail = fail
        self.calls = 0
        self._health = health

    def health(self, timeout_s):
        return HealthStatus(self._health, 1.0, None if self._health == "up" else "model_missing")

    def run(self):
        self.calls += 1
        if self.fail:
            raise self.fail
        return f"answer from {self.info.name}"


LOCAL, EXTERNAL = Locality.LOCAL, Locality.EXTERNAL


def make(*providers, mode=ExecutionMode.LOCAL_FIRST, clock=None, threshold=3):
    registry = ProviderRegistry()
    for priority, provider in enumerate(providers):
        registry.register(provider, priority=priority)
    clock = clock or Clock()
    return Router(registry, mode=mode, breaker=CircuitBreaker(threshold=threshold, cooldown_s=30, clock=clock),
                  monitor=HealthMonitor(clock=clock))


def unavailable(sent=False):
    return ProviderError(ProviderErrorCode.UNAVAILABLE, "down", request_sent=sent)


def test_local_first_prefers_the_local_model():
    cloud, local = Fake("aura", EXTERNAL), Fake("ollama", LOCAL)
    routed = make(cloud, local).route("chat.answer", lambda p: p.run())
    assert routed.value == "answer from ollama"
    assert routed.metadata.locality == "local" and not routed.metadata.fallback_used and cloud.calls == 0


def test_cloud_preferred_uses_the_cloud_and_falls_back_to_local_when_it_fails():
    cloud, local = Fake("aura", EXTERNAL, fail=unavailable()), Fake("ollama", LOCAL)
    routed = make(cloud, local, mode=ExecutionMode.CLOUD_PREFERRED).route("chat.answer", lambda p: p.run())
    assert routed.value == "answer from ollama"
    assert routed.metadata.fallback_used and routed.metadata.attempts == ({"provider": "aura", "code": "unavailable"},)
    assert routed.metadata.routing_reason == "fallback_after:aura:unavailable"


def test_offline_only_never_calls_an_external_provider():
    cloud, local = Fake("aura", EXTERNAL), Fake("ollama", LOCAL, fail=unavailable())
    with pytest.raises(NoCompatibleProvider) as caught:
        make(cloud, local, mode=ExecutionMode.OFFLINE_ONLY).route("chat.answer", lambda p: p.run())
    assert cloud.calls == 0
    assert {"provider": "aura", "reason": "egress_blocked"} in caught.value.reasons


def test_offline_only_with_only_cloud_models_is_unavailable_not_silent():
    router = make(Fake("aura", EXTERNAL), mode=ExecutionMode.OFFLINE_ONLY)
    assert router.available("chat.answer") is False
    with pytest.raises(NoCompatibleProvider) as caught:
        router.route("chat.answer", lambda p: p.run())
    assert caught.value.to_dict()["mode"] == "offline_only"


def test_a_vision_task_never_falls_back_to_a_text_model():
    cv = Fake("hf_space", EXTERNAL, caps=(Capability.VISION,), modalities=("image",), fail=unavailable())
    llm = Fake("ollama", LOCAL, caps=(Capability.STRUCTURED, Capability.CHAT, Capability.VISION))  # claims vision, text only
    with pytest.raises(NoCompatibleProvider):
        make(cv, llm).route("vision.analyze", lambda p: p.run())
    assert llm.calls == 0


def test_vision_falls_back_from_the_hf_space_to_local_cv():
    remote = Fake("hf_space", EXTERNAL, caps=(Capability.VISION,), modalities=("image",), fail=unavailable())
    local = Fake("flame_cv", LOCAL, caps=(Capability.VISION,), modalities=("image",))
    routed = make(remote, local, mode=ExecutionMode.CLOUD_PREFERRED).route("vision.analyze", lambda p: p.run())
    assert routed.metadata.provider == "flame_cv"


def test_a_non_idempotent_call_is_not_resent_after_it_may_have_arrived():
    first, second = Fake("vllm", LOCAL, fail=ProviderError(ProviderErrorCode.TIMEOUT, "slow")), Fake("ollama", LOCAL)
    with pytest.raises(NoCompatibleProvider) as caught:
        make(first, second).route("chat.answer", lambda p: p.run(), idempotent=False)
    assert second.calls == 0 and caught.value.reasons[-1]["reason"] == "not_idempotent_after_send"


def test_a_non_idempotent_call_may_move_on_when_the_request_never_left():
    first, second = Fake("vllm", LOCAL, fail=unavailable(sent=False)), Fake("ollama", LOCAL)
    assert make(first, second).route("chat.answer", lambda p: p.run(), idempotent=False).metadata.provider == "ollama"


def test_our_own_bad_request_is_not_retried_elsewhere_or_blamed_on_the_provider():
    first, second = Fake("vllm", LOCAL, fail=ProviderError(ProviderErrorCode.INVALID_REQUEST, "bad")), Fake("ollama", LOCAL)
    router = make(first, second, threshold=1)
    with pytest.raises(NoCompatibleProvider):
        router.route("chat.answer", lambda p: p.run())
    assert second.calls == 0 and router.breaker.state("vllm") == "closed"


def test_the_circuit_opens_skips_the_dead_provider_then_half_opens_after_cooldown():
    clock = Clock()
    cloud, local = Fake("aura", EXTERNAL, fail=unavailable()), Fake("ollama", LOCAL)
    router = make(cloud, local, mode=ExecutionMode.CLOUD_PREFERRED, clock=clock, threshold=2)
    for _ in range(2):
        router.route("chat.answer", lambda p: p.run())
    assert router.breaker.state("aura") == "open" and cloud.calls == 2
    router.route("chat.answer", lambda p: p.run())
    assert cloud.calls == 2, "an open circuit is skipped without a call"
    clock.now += 31
    cloud.fail = None                       # connectivity returns
    routed = router.route("chat.answer", lambda p: p.run())
    assert routed.metadata.provider == "aura" and router.breaker.state("aura") == "closed"


def test_a_provider_whose_health_is_down_is_skipped_with_the_reason():
    broken, good = Fake("ollama", LOCAL, health="down"), Fake("vllm", LOCAL)
    router = make(broken, good)
    router.refresh_health()
    routed = router.route("chat.answer", lambda p: p.run())
    assert routed.metadata.provider == "vllm" and broken.calls == 0
    assert "ollama:health_down:model_missing" in routed.metadata.routing_reason


def test_offline_only_does_not_even_probe_external_providers():
    class Exploding(Fake):
        def health(self, timeout_s):
            raise AssertionError("probe is egress too")

    router = make(Exploding("aura", EXTERNAL), Fake("ollama", LOCAL), mode=ExecutionMode.OFFLINE_ONLY)
    router.refresh_health()
    status = {p["name"]: p for p in router.status()["providers"]}
    assert status["aura"]["permitted"] is False and status["aura"]["health"]["state"] == "blocked"


def test_each_provider_is_tried_at_most_once_and_registration_is_unique():
    failing = Fake("ollama", LOCAL, fail=unavailable())
    router = make(failing)
    with pytest.raises(NoCompatibleProvider):
        router.route("chat.answer", lambda p: p.run())
    assert failing.calls == 1
    with pytest.raises(ValueError):
        router.registry.register(Fake("ollama", LOCAL))


def test_mode_can_change_at_runtime_and_decisions_are_counted():
    cloud, local = Fake("aura", EXTERNAL), Fake("ollama", LOCAL)
    router = make(cloud, local, mode=ExecutionMode.CLOUD_PREFERRED)
    assert router.route("chat.answer", lambda p: p.run()).metadata.provider == "aura"
    router.set_mode(ExecutionMode.OFFLINE_ONLY)
    assert router.route("chat.answer", lambda p: p.run()).metadata.provider == "ollama"
    assert router.status()["decisions"] == {"chat.answer|aura|ok": 1, "chat.answer|ollama|ok": 1}


def test_the_model_manifest_is_valid_and_complete():
    entries = load_manifest()
    capabilities = {e["capability"] for e in entries if e["locality"] == "local"}
    assert {"structured", "embeddings", "vision"} <= capabilities, "one local model per critical capability"
    assert all(e["status"] in {"approved", "candidate", "retired"} for e in entries)
