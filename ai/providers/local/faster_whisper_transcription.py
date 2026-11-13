"""Local speech-to-text with faster-whisper (CTranslate2), runnable without internet once cached.

With ``offline=True`` the Hugging Face hub is never contacted: a model that is not in the cache is
reported as ``model_missing`` instead of being downloaded (the same rule as the fastembed provider).
Prepare the cache while connected with
``python -m ai.providers.local.faster_whisper_transcription prepare --cache-dir <dir> [--model small]``.

Why these decode settings: ``vad_filter`` keeps Whisper from inventing text on noise between spoken
phrases, ``condition_on_previous_text=False`` stops one bad segment from steering the next, and
``beam_size=1`` keeps CPU time near real time. Segment timestamps are only good to a few seconds
because VAD merges speech into long chunks; callers must not present them as precise.
"""
from __future__ import annotations

import hashlib
import importlib.util
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

from ai.providers.contracts.base import Capability, HealthStatus, Locality, ProviderInfo
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
from ai.providers.contracts.transcription import TranscriptionRequest, TranscriptionResponse

PROVIDER_NAME = "faster_whisper"
DEFAULT_MODEL = "small"          # Systran/faster-whisper-small, about 480 MB
BEAM_SIZE = 1
_DEPENDENCIES = ("faster_whisper", "av", "numpy")


class FasterWhisperProvider:
    def __init__(self, *, model_size: str = DEFAULT_MODEL, cache_dir: str | None = None,
                 offline: bool | Callable[[], bool] = False, device: str = "cpu", compute_type: str = "int8") -> None:
        """``offline`` may be a callable so the router's *current* mode decides (offline_only => cache-only)."""
        self._model_size = model_size
        self._cache_dir = cache_dir
        self._offline_source = offline
        self._device = device
        self._compute_type = compute_type
        self._model = None
        self._lock = threading.Lock()
        self.info = ProviderInfo(
            name=PROVIDER_NAME, runtime="ctranslate2", locality=Locality.LOCAL,
            capabilities=frozenset({Capability.TRANSCRIPTION}), model=f"faster-whisper-{model_size}",
            version=self._version(), modalities=frozenset({"audio"}),
        )

    @staticmethod
    def _version() -> str | None:
        try:
            import faster_whisper
        except ImportError:
            return None
        return getattr(faster_whisper, "__version__", None)

    @property
    def _offline(self) -> bool:
        source = self._offline_source
        return bool(source()) if callable(source) else bool(source)

    def _cached_model_path(self) -> str | None:
        """The cached model directory, or None. Never touches the network."""
        try:
            from faster_whisper.utils import download_model

            return download_model(self._model_size, local_files_only=True, cache_dir=self._cache_dir)
        except Exception:  # not cached, or faster-whisper missing
            return None

    def health(self, timeout_s: float) -> HealthStatus:
        started = time.perf_counter()
        if any(importlib.util.find_spec(name) is None for name in _DEPENDENCIES):
            return HealthStatus("down", 0.0, "dependency_missing", model_present=False)
        present = self._model is not None or self._cached_model_path() is not None
        latency = round((time.perf_counter() - started) * 1000, 1)
        if self._offline and not present:
            return HealthStatus("down", latency, ProviderErrorCode.MODEL_MISSING.value, model_present=False)
        return HealthStatus("up", latency, model_present=present)

    def _load(self):
        with self._lock:
            if self._model is not None:
                return self._model
            offline = self._offline
            if offline and self._cached_model_path() is None:
                raise ProviderError(ProviderErrorCode.MODEL_MISSING, "The speech model is not in the offline cache.",
                                    provider=PROVIDER_NAME, request_sent=False)
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise ProviderError(ProviderErrorCode.MODEL_MISSING, "faster-whisper is not installed.",
                                    provider=PROVIDER_NAME, request_sent=False) from exc
            try:
                self._model = WhisperModel(self._model_size, device=self._device, compute_type=self._compute_type,
                                           download_root=self._cache_dir, local_files_only=offline)
            except Exception as exc:  # download/IO/CTranslate2 load failures all mean "model not usable here"
                raise ProviderError(ProviderErrorCode.MODEL_MISSING, "The speech model could not be loaded.",
                                    provider=PROVIDER_NAME, request_sent=False) from exc
            return self._model

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResponse:
        try:
            from cv.audio_extraction import AudioError, decode_audio
        except ImportError as exc:
            raise ProviderError(ProviderErrorCode.MODEL_MISSING, "The audio decoder is not installed.",
                                provider=PROVIDER_NAME, request_sent=False) from exc
        model = self._load()
        try:
            samples, _stats = decode_audio(request.audio_path)
        except AudioError as exc:
            raise ProviderError(ProviderErrorCode.INVALID_REQUEST, exc.message, provider=PROVIDER_NAME) from exc
        if samples is None:
            return TranscriptionResponse(text="", segments=(), model=self.info.model or "", provider=PROVIDER_NAME,
                                         language=request.language)
        try:
            raw_segments, detected = model.transcribe(
                samples, language=request.language, vad_filter=True, beam_size=BEAM_SIZE,
                condition_on_previous_text=False,
            )
            segments = tuple(
                {"start_s": round(float(s.start), 2), "end_s": round(float(s.end), 2), "text": s.text.strip(),
                 "avg_logprob": round(float(s.avg_logprob), 3), "no_speech_prob": round(float(s.no_speech_prob), 3)}
                for s in raw_segments if s.text.strip()
            )
        except MemoryError as exc:
            raise ProviderError(ProviderErrorCode.RESOURCE_EXHAUSTED, "The audio is too long for local transcription.",
                                provider=PROVIDER_NAME) from exc
        return TranscriptionResponse(
            text=" ".join(segment["text"] for segment in segments), segments=segments,
            model=self.info.model or "", provider=PROVIDER_NAME, language=getattr(detected, "language", None),
        )

    def checksums(self) -> dict[str, str]:
        """sha256 of the cached model weights, for the model manifest."""
        path = self._cached_model_path()
        if path is None:
            return {}
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(path).glob("model.bin")}


def _main(argv: list[str]) -> int:
    if not argv or argv[0] not in {"prepare", "verify"}:
        print("usage: python -m ai.providers.local.faster_whisper_transcription prepare|verify "
              "[--cache-dir DIR] [--model SIZE]")
        return 2

    def option(name: str, default: str | None) -> str | None:
        return argv[argv.index(name) + 1] if name in argv else default

    provider = FasterWhisperProvider(model_size=option("--model", DEFAULT_MODEL) or DEFAULT_MODEL,
                                     cache_dir=option("--cache-dir", None), offline=argv[0] == "verify")
    provider._load()  # downloads on `prepare`; raises model_missing on `verify` when not cached
    for path, digest in provider.checksums().items():
        print(f"{digest}  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
