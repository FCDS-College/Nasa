"""The local transcription provider and its routing (faster-whisper). A fake model; one optional real-model test."""
import wave
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("faster_whisper")
pytest.importorskip("av")

from ai.providers.contracts.base import Capability  # noqa: E402
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode  # noqa: E402
from ai.providers.contracts.transcription import TranscriptionProvider, TranscriptionRequest  # noqa: E402
from ai.providers.local.faster_whisper_transcription import FasterWhisperProvider  # noqa: E402
from ai.routing import CircuitBreaker, ExecutionMode, HealthMonitor, ProviderRegistry, Router  # noqa: E402


def write_wav(path, samples, rate=16_000):
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes((samples * 32767).astype("<i2").tobytes())
    return path


def tone_wav(path, seconds=3.0):
    t = np.arange(int(seconds * 16_000)) / 16_000
    return write_wav(path, (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32))


class FakeModel:
    def __init__(self):
        self.calls = []

    def transcribe(self, audio, **kwargs):
        self.calls.append((len(audio), kwargs))
        segments = [
            SimpleNamespace(start=1.004, end=2.5, text=" Fan to zero. ", avg_logprob=-0.2, no_speech_prob=0.05),
            SimpleNamespace(start=3.0, end=4.0, text="   ", avg_logprob=-1.0, no_speech_prob=0.9),
        ]
        return iter(segments), SimpleNamespace(language="en")


def provider_with_fake_model(**kwargs):
    provider = FasterWhisperProvider(**kwargs)
    provider._model = FakeModel()
    return provider


def router(provider):
    registry = ProviderRegistry()
    registry.register(provider)
    return Router(registry, mode=ExecutionMode.OFFLINE_ONLY, breaker=CircuitBreaker(threshold=3, cooldown_s=30),
                  monitor=HealthMonitor())


def test_provider_satisfies_the_contract_and_is_local():
    provider = FasterWhisperProvider()
    assert isinstance(provider, TranscriptionProvider)
    assert provider.info.capabilities == frozenset({Capability.TRANSCRIPTION})
    assert "audio" in provider.info.modalities and provider.info.locality.value == "local"


def test_offline_without_a_cached_model_reports_model_missing_and_never_downloads(tmp_path):
    provider = FasterWhisperProvider(cache_dir=str(tmp_path / "empty-cache"), offline=True)
    health = provider.health(1.0)
    assert health.state == "down" and health.detail == "model_missing" and health.model_present is False
    with pytest.raises(ProviderError) as err:
        provider.transcribe(TranscriptionRequest(tone_wav(tmp_path / "a.wav")))
    assert err.value.code is ProviderErrorCode.MODEL_MISSING and err.value.request_sent is False
    assert not (tmp_path / "empty-cache").exists() or not any((tmp_path / "empty-cache").rglob("*.bin"))


def test_segments_are_mapped_and_blank_ones_dropped(tmp_path):
    provider = provider_with_fake_model()
    response = provider.transcribe(TranscriptionRequest(tone_wav(tmp_path / "a.wav")))

    assert response.text == "Fan to zero." and response.language == "en"
    assert response.provider == "faster_whisper" and response.model == "faster-whisper-small"
    assert response.segments == ({"start_s": 1.0, "end_s": 2.5, "text": "Fan to zero.",
                                  "avg_logprob": -0.2, "no_speech_prob": 0.05},)
    (samples, kwargs), = provider._model.calls
    assert samples == 3 * 16_000
    assert kwargs["vad_filter"] is True and kwargs["condition_on_previous_text"] is False and kwargs["language"] is None


def test_a_requested_language_is_passed_through(tmp_path):
    provider = provider_with_fake_model()
    provider.transcribe(TranscriptionRequest(tone_wav(tmp_path / "a.wav"), language="ar"))
    assert provider._model.calls[0][1]["language"] == "ar"


def test_a_file_that_is_not_audio_is_an_invalid_request(tmp_path):
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"not audio at all")
    with pytest.raises(ProviderError) as err:
        provider_with_fake_model().transcribe(TranscriptionRequest(bad))
    assert err.value.code is ProviderErrorCode.INVALID_REQUEST


def test_speech_task_routes_offline_to_the_local_provider(tmp_path):
    provider = provider_with_fake_model(offline=True)
    audio = tone_wav(tmp_path / "a.wav")
    routed = router(provider).route("speech.transcribe", lambda p: p.transcribe(TranscriptionRequest(audio)))
    assert routed.metadata.provider == "faster_whisper" and routed.metadata.locality == "local"
    assert routed.value.text == "Fan to zero."


@pytest.mark.skipif(FasterWhisperProvider()._cached_model_path() is None, reason="Whisper model is not cached")
def test_the_real_model_finds_no_speech_in_a_pure_tone(tmp_path):
    provider = FasterWhisperProvider(offline=True)   # cache-only: this test never downloads
    response = provider.transcribe(TranscriptionRequest(tone_wav(tmp_path / "tone.wav")))
    assert response.segments == () and response.text == ""
