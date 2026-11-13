"""Speech attached to a video analysis (flame_api/audio_transcript.py): every status, and it never raises."""
import wave

import cv2
import numpy as np
import pytest

pytest.importorskip("av")

from ai.providers.contracts.base import Capability, HealthStatus, Locality, ProviderInfo  # noqa: E402
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode  # noqa: E402
from ai.providers.contracts.transcription import TranscriptionResponse  # noqa: E402
from ai.routing import CircuitBreaker, ExecutionMode, HealthMonitor, ProviderRegistry, Router  # noqa: E402
from flame_api.audio_transcript import CLASSIFICATION, NOTE, transcribe_video_audio  # noqa: E402

RATE = 16_000


class FakeTranscriber:
    def __init__(self, *, fail=None, segments=()):
        self.info = ProviderInfo(name="fake_stt", runtime="fake", locality=Locality.LOCAL,
                                 capabilities=frozenset({Capability.TRANSCRIPTION}), model="fake-small",
                                 modalities=frozenset({"audio"}))
        self.fail, self.segments, self.calls = fail, segments, 0

    def health(self, timeout_s):
        return HealthStatus("up", 1.0)

    def transcribe(self, request):
        self.calls += 1
        if self.fail:
            raise self.fail
        assert request.audio_path.suffix == ".wav" and request.audio_path.exists()
        return TranscriptionResponse(text=" ".join(s["text"] for s in self.segments), segments=tuple(self.segments),
                                     model="fake-small", provider="fake_stt", language="en")


def router_for(provider):
    registry = ProviderRegistry()
    registry.register(provider)
    return Router(registry, mode=ExecutionMode.OFFLINE_ONLY, breaker=CircuitBreaker(threshold=3, cooldown_s=30),
                  monitor=HealthMonitor())


def write_wav(path, samples):
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes((samples * 32767).astype("<i2").tobytes())
    return path


def loud(path, seconds=3):
    t = np.arange(seconds * RATE) / RATE
    return write_wav(path, (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32))


SEGMENT = {"start_s": 1.0, "end_s": 2.5, "text": "Fan to zero.", "avg_logprob": -0.2, "no_speech_prob": 0.05}


def test_audible_speech_is_transcribed_with_the_caveat_attached(tmp_path):
    provider = FakeTranscriber(segments=[SEGMENT])
    audio = transcribe_video_audio(loud(tmp_path / "v.wav"), tmp_path / "job", router_for(provider))

    assert audio["status"] == "transcribed" and audio["language"] == "en"
    assert audio["segments"] == [SEGMENT]
    assert audio["classification"] == CLASSIFICATION == "machine_transcribed" and audio["note"] == NOTE
    assert audio["execution"]["provider"] == "fake_stt" and audio["execution"]["locality"] == "local"
    assert audio["duration_s"] == pytest.approx(3.0, abs=0.05) and audio["loudest_second_dbfs"] > -55


def test_audible_audio_without_speech_is_no_speech(tmp_path):
    audio = transcribe_video_audio(loud(tmp_path / "v.wav"), tmp_path / "job", router_for(FakeTranscriber()))
    assert audio["status"] == "no_speech" and audio["segments"] == []


def test_a_silent_track_is_skipped_without_calling_the_model(tmp_path):
    provider = FakeTranscriber(segments=[SEGMENT])
    silent = write_wav(tmp_path / "v.wav", np.zeros(3 * RATE, np.float32))
    audio = transcribe_video_audio(silent, tmp_path / "job", router_for(provider))
    assert audio["status"] == "silent" and audio["segments"] == [] and provider.calls == 0
    assert audio["loudest_second_dbfs"] <= -55


def test_a_video_with_no_audio_track(tmp_path):
    video = tmp_path / "v.avi"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (64, 48))
    for _ in range(5):
        writer.write(np.zeros((48, 64, 3), np.uint8))
    writer.release()
    provider = FakeTranscriber(segments=[SEGMENT])
    audio = transcribe_video_audio(video, tmp_path / "job", router_for(provider))
    assert audio["status"] == "no_audio_track" and provider.calls == 0


def test_a_missing_model_is_unavailable_not_an_error(tmp_path):
    provider = FakeTranscriber(fail=ProviderError(ProviderErrorCode.MODEL_MISSING, "not cached", request_sent=False))
    audio = transcribe_video_audio(loud(tmp_path / "v.wav"), tmp_path / "job", router_for(provider))
    assert audio["status"] == "unavailable" and audio["failure_code"] == "model_missing" and audio["segments"] == []


def test_no_transcription_provider_at_all_is_unavailable(tmp_path):
    empty = Router(ProviderRegistry(), mode=ExecutionMode.OFFLINE_ONLY, breaker=CircuitBreaker(threshold=3, cooldown_s=30),
                   monitor=HealthMonitor())
    audio = transcribe_video_audio(loud(tmp_path / "v.wav"), tmp_path / "job", empty)
    assert audio["status"] == "unavailable" and audio["failure_code"] == "no_provider"


def test_an_undecodable_file_is_unavailable_not_an_error(tmp_path):
    bad = tmp_path / "v.mp4"
    bad.write_bytes(b"not media")
    audio = transcribe_video_audio(bad, tmp_path / "job", router_for(FakeTranscriber(segments=[SEGMENT])))
    assert audio["status"] == "unavailable" and audio["failure_code"] == "decode_failed"


def test_every_status_conforms_to_the_published_contract(tmp_path):
    from api_contract import assert_contract_component

    cases = {
        "transcribed": (loud(tmp_path / "a.wav"), FakeTranscriber(segments=[SEGMENT])),
        "no_speech": (loud(tmp_path / "b.wav"), FakeTranscriber()),
        "silent": (write_wav(tmp_path / "c.wav", np.zeros(3 * RATE, np.float32)), FakeTranscriber()),
        "unavailable": (loud(tmp_path / "d.wav"), FakeTranscriber(
            fail=ProviderError(ProviderErrorCode.MODEL_MISSING, "not cached", request_sent=False))),
    }
    for status, (media, provider) in cases.items():
        audio = transcribe_video_audio(media, tmp_path / f"job-{status}", router_for(provider))
        assert audio["status"] == status
        assert_contract_component(audio, "VideoAudioTranscript")
    junk = tmp_path / "e.mp4"
    junk.write_bytes(b"not media")
    assert_contract_component(transcribe_video_audio(junk, tmp_path / "job-junk", router_for(FakeTranscriber())),
                              "VideoAudioTranscript")


def test_an_unexpected_provider_crash_never_propagates(tmp_path):
    provider = FakeTranscriber(fail=RuntimeError("boom"))
    audio = transcribe_video_audio(loud(tmp_path / "v.wav"), tmp_path / "job", router_for(provider))
    assert audio["status"] == "unavailable" and audio["failure_code"] == "transcription_failed"
