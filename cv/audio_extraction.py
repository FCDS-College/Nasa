"""Audio extraction for the video pipeline: decode a media file's audio track with PyAV.

PyAV bundles FFmpeg's libraries, so no ``ffmpeg`` binary is needed. Everything here is local and
read-only on the input; the only file written is the 16 kHz mono WAV that ``extract_audio_wav`` is
asked to create.

Audibility matters because many flight videos carry an audio track that is digital silence. On the
17 NASA BASS-II clips, 6 peak below -57 dBFS while the 11 with operator speech peak above -29 dBFS, so a
threshold on the loudest one-second window separates them cleanly and keeps Whisper from hallucinating
text on silence.
"""
from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16_000            # what Whisper-family models expect
AUDIBLE_DBFS = -55.0            # loudest 1 s window RMS at or below this is treated as silence
_FLOOR = 1e-9


class AudioError(Exception):
    """The media could not be decoded. ``code`` is ``decode_failed`` (retrying will not help)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class AudioStats:
    has_track: bool
    duration_s: float = 0.0
    codec: str | None = None
    source_sample_rate: int | None = None
    channels: int | None = None
    rms_dbfs: float | None = None
    loudest_second_dbfs: float | None = None

    @property
    def audible(self) -> bool:
        return self.has_track and self.loudest_second_dbfs is not None and self.loudest_second_dbfs > AUDIBLE_DBFS


def _dbfs(value: float) -> float:
    return float(20.0 * np.log10(max(float(value), _FLOOR)))


def decode_audio(path: str | Path) -> tuple[np.ndarray | None, AudioStats]:
    """Decode the first audio stream to mono float32 at 16 kHz. ``(None, stats)`` when there is no track."""
    import av

    try:
        container = av.open(str(path))
    except (av.error.FFmpegError, OSError) as exc:
        raise AudioError("decode_failed", "The media file could not be opened.") from exc
    try:
        if not container.streams.audio:
            return None, AudioStats(has_track=False)
        stream = container.streams.audio[0]
        resampler = av.AudioResampler(format="flt", layout="mono", rate=SAMPLE_RATE)
        chunks: list[np.ndarray] = []
        try:
            for frame in container.decode(stream):
                for out in resampler.resample(frame):
                    chunks.append(out.to_ndarray().reshape(-1))
            for out in resampler.resample(None):
                chunks.append(out.to_ndarray().reshape(-1))
        except (av.error.FFmpegError, ValueError) as exc:
            raise AudioError("decode_failed", "The audio track could not be decoded.") from exc
        info = (stream.codec_context.name, int(stream.rate), int(stream.channels))
    finally:
        container.close()

    samples = np.concatenate(chunks).astype(np.float32) if chunks else np.zeros(0, np.float32)
    if samples.size == 0:
        return None, AudioStats(True, 0.0, *info)
    return samples, _stats(samples, info)


def _stats(samples: np.ndarray, info: tuple[str, int, int]) -> AudioStats:
    window = SAMPLE_RATE
    if len(samples) >= window:
        count = len(samples) // window
        blocks = samples[: count * window].reshape(count, window)
    else:
        blocks = samples[None, :]
    loudest = max(_dbfs(np.sqrt(np.mean(block.astype(np.float64) ** 2))) for block in blocks)
    return AudioStats(
        has_track=True, duration_s=round(len(samples) / SAMPLE_RATE, 3), codec=info[0], source_sample_rate=info[1],
        channels=info[2], rms_dbfs=round(_dbfs(np.sqrt(np.mean(samples.astype(np.float64) ** 2))), 1),
        loudest_second_dbfs=round(loudest, 1),
    )


def write_wav(samples: np.ndarray, destination: str | Path) -> Path:
    """16-bit PCM mono WAV at 16 kHz, so a provider receives an ordinary audio file."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(destination), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm.tobytes())
    return destination


def extract_audio_wav(media_path: str | Path, wav_path: str | Path) -> AudioStats:
    """Write the audio of ``media_path`` to ``wav_path`` when it has an audible track.

    Returns the stats either way. No file is written for a missing, empty or silent track, so the
    caller can skip transcription without opening anything.
    """
    samples, stats = decode_audio(media_path)
    if samples is not None and stats.audible:
        write_wav(samples, wav_path)
    return stats
