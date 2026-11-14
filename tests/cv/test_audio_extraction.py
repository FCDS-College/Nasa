"""Audio extraction for the video pipeline (cv/audio_extraction.py). Synthetic audio only; PyAV, no ffmpeg binary."""
import wave

import cv2
import numpy as np
import pytest

av = pytest.importorskip("av")

from cv.audio_extraction import AUDIBLE_DBFS, SAMPLE_RATE, AudioError, decode_audio, extract_audio_wav  # noqa: E402


def tone(seconds=3.0, amplitude=0.3, rate=SAMPLE_RATE):
    t = np.arange(int(seconds * rate)) / rate
    return (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


def write_wav(path, samples, rate=SAMPLE_RATE):
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes((samples * 32767).astype("<i2").tobytes())
    return path


def aac_mp4(path, samples, rate=48_000):
    """An audio-only AAC MP4, encoded with PyAV, to exercise the real codec path."""
    with av.open(str(path), "w") as out:
        stream = out.add_stream("aac", rate=rate)
        stream.layout = "mono"
        for start in range(0, len(samples) - 1023, 1024):
            frame = av.AudioFrame.from_ndarray(samples[start:start + 1024][np.newaxis, :], format="fltp", layout="mono")
            frame.sample_rate = rate
            for packet in stream.encode(frame):
                out.mux(packet)
        for packet in stream.encode(None):
            out.mux(packet)
    return path


def test_a_loud_tone_is_audible_and_comes_back_mono_16k(tmp_path):
    samples, stats = decode_audio(write_wav(tmp_path / "tone.wav", tone()))
    assert stats.has_track and stats.audible
    assert samples.dtype == np.float32 and samples.ndim == 1
    assert stats.duration_s == pytest.approx(3.0, abs=0.05)
    assert -15.0 < stats.loudest_second_dbfs < -5.0   # 0.3 amplitude sine is about -13.5 dBFS RMS


def test_digital_silence_has_a_track_but_is_not_audible(tmp_path):
    samples, stats = decode_audio(write_wav(tmp_path / "silence.wav", np.zeros(SAMPLE_RATE * 3, np.float32)))
    assert stats.has_track and not stats.audible
    assert stats.loudest_second_dbfs <= AUDIBLE_DBFS


def test_a_faint_hum_counts_as_silent(tmp_path):
    # about -75 dBFS, like the BASS-II clips whose audio track carries only a noise floor
    _, stats = decode_audio(write_wav(tmp_path / "hum.wav", tone(amplitude=0.00025)))
    assert not stats.audible


def test_extract_writes_a_16k_mono_wav_only_for_audible_audio(tmp_path):
    loud = write_wav(tmp_path / "loud.wav", tone(), rate=SAMPLE_RATE)
    silent = write_wav(tmp_path / "quiet.wav", np.zeros(SAMPLE_RATE * 2, np.float32))
    out_loud, out_silent = tmp_path / "out" / "loud.wav", tmp_path / "out" / "quiet.wav"

    assert extract_audio_wav(loud, out_loud).audible
    assert not extract_audio_wav(silent, out_silent).audible

    with wave.open(str(out_loud)) as handle:
        assert (handle.getnchannels(), handle.getsampwidth(), handle.getframerate()) == (1, 2, SAMPLE_RATE)
        assert handle.getnframes() == pytest.approx(3 * SAMPLE_RATE, abs=SAMPLE_RATE // 20)
    assert not out_silent.exists(), "no file for a silent track, so the caller can skip transcription"


def test_aac_audio_in_an_mp4_is_decoded_and_resampled(tmp_path):
    samples, stats = decode_audio(aac_mp4(tmp_path / "speech.mp4", tone(rate=48_000), rate=48_000))
    assert stats.codec == "aac" and stats.source_sample_rate == 48_000
    assert stats.audible and stats.duration_s == pytest.approx(3.0, abs=0.2)
    assert len(samples) == pytest.approx(stats.duration_s * SAMPLE_RATE, abs=1)


def test_a_video_without_audio_has_no_track(tmp_path):
    path = tmp_path / "silent-movie.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (64, 48))
    for _ in range(5):
        writer.write(np.zeros((48, 64, 3), np.uint8))
    writer.release()
    samples, stats = decode_audio(path)
    assert samples is None and not stats.has_track and not stats.audible


def test_a_file_that_is_not_media_is_a_decode_error(tmp_path):
    bad = tmp_path / "nope.mp4"
    bad.write_bytes(b"definitely not a media file")
    with pytest.raises(AudioError) as err:
        decode_audio(bad)
    assert err.value.code == "decode_failed"
