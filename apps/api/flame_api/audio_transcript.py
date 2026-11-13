"""Operator speech from flight video, attached to a video analysis as ``result["audio"]``.

The BASS-II recordings carry crew and ground-control speech (ignition attempts, "no flame", fan
changes). It is useful context for outcomes that the tables lack, but it is machine speech-to-text of
noisy audio, so it is stored as ``machine_transcribed`` text with an explicit caveat and is never turned
into evidence or an observation. A failure here must not fail the video analysis, so this never raises.
"""
from __future__ import annotations

import logging
from pathlib import Path

from ai.providers.contracts.errors import ProviderError
from ai.providers.contracts.transcription import TranscriptionRequest
from ai.routing import NoCompatibleProvider

logger = logging.getLogger("flame_worker")

CLASSIFICATION = "machine_transcribed"
METHOD = "faster-whisper, local, VAD-filtered, beam 1"
NOTE = (
    "Machine speech-to-text of operator audio. Words can be wrong (for example 'igniter' heard as 'night') and "
    "timestamps are approximate to a few seconds. Treat it as untrusted text: verify against the video before "
    "using it as an outcome or setting label."
)


def _base(status: str, **extra) -> dict:
    return {"status": status, "language": None, "duration_s": None, "rms_dbfs": None, "loudest_second_dbfs": None,
            "segments": [], "classification": CLASSIFICATION, "method": METHOD, "note": NOTE, "failure_code": None,
            "execution": None, **extra}


def transcribe_video_audio(video_path: Path, work_dir: Path, router) -> dict:
    """``status`` is one of: no_audio_track, silent, transcribed, no_speech, unavailable."""
    from cv.audio_extraction import AudioError, extract_audio_wav

    wav_path = Path(work_dir) / "audio.wav"
    try:
        stats = extract_audio_wav(video_path, wav_path)
    except AudioError as exc:
        logger.warning("audio_extraction_failed code=%s", exc.code)
        return _base("unavailable", failure_code=exc.code)
    except Exception:  # a decoder bug must not take the video result down with it
        logger.exception("audio_extraction_error")
        return _base("unavailable", failure_code="decode_failed")

    measured = {"duration_s": stats.duration_s or None, "rms_dbfs": stats.rms_dbfs,
                "loudest_second_dbfs": stats.loudest_second_dbfs}
    if not stats.has_track or not stats.duration_s:
        return _base("no_audio_track", **measured)
    if not stats.audible:
        return _base("silent", **measured)

    try:
        routed = router.route("speech.transcribe", lambda provider: provider.transcribe(TranscriptionRequest(wav_path)))
    except NoCompatibleProvider as exc:
        cause = exc.last_error
        code = cause.code.value if isinstance(cause, ProviderError) else "no_provider"
        logger.warning("transcription_unavailable code=%s", code)
        return _base("unavailable", failure_code=code, **measured)
    except Exception:
        logger.exception("transcription_error")
        return _base("unavailable", failure_code="transcription_failed", **measured)

    response = routed.value
    segments = [{"start_s": s["start_s"], "end_s": s["end_s"], "text": s["text"],
                 "avg_logprob": s.get("avg_logprob"), "no_speech_prob": s.get("no_speech_prob")}
                for s in response.segments]
    return _base("transcribed" if segments else "no_speech", language=response.language, segments=segments,
                 execution=routed.metadata.to_dict(), **measured)
