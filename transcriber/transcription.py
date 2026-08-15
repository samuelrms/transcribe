"""Transcription core: model loading, caching, decoding and error mapping.

``faster_whisper`` is imported lazily so the interface opens fast and the test
suite runs without any model on disk. The import itself must happen on the
main thread - see :func:`preload`.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Sequence

from .audio import format_duration, validate_audio_file
from .config import BEAM_SIZE, LANGUAGE_LABELS, VAD_FILTER, VAD_MIN_SILENCE_MS
from .device import CPU, DeviceChoice, resolve_device
from .errors import (
    AppError,
    ModelLoadError,
    NoSpeechError,
    OutOfMemoryError,
    TranscriptionCancelled,
    TranscriptionFailedError,
)
from .i18n import get_language, t
from .srt import build_srt

if TYPE_CHECKING:  # pragma: no cover - typing only
    from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float, str], None]
CancelCheck = Callable[[], bool]

_whisper_model_cls: type | None = None
_import_lock = threading.Lock()


def preload() -> None:
    """Import ``faster_whisper`` ahead of time, from the calling thread.

    Its import chain ends up creating a Tk root. On macOS, building one off the
    main thread makes AppKit abort the whole process with "NSWindow should only
    be instantiated on the main thread", so the GUI calls this on the main
    thread before any worker starts.
    """
    _whisper_model()


def _whisper_model() -> type:
    """Import ``WhisperModel`` once and cache the class."""
    global _whisper_model_cls
    with _import_lock:
        if _whisper_model_cls is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise ModelLoadError(
                    "error.missing_library", hint_key="error.missing_library.hint"
                ) from exc
            _whisper_model_cls = WhisperModel
        return _whisper_model_cls


def language_display_name(code: str | None) -> str:
    """Turn ``pt`` into ``Português (pt)``; unknown codes stay as-is."""
    if not code:
        return t("summary.unknown_language")
    label = LANGUAGE_LABELS.get(code.lower(), {}).get(get_language())
    return f"{label} ({code})" if label else code


@dataclass(frozen=True, slots=True)
class Segment:
    """A spoken chunk with its timing, in seconds."""

    start: float
    end: float
    text: str


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    """Everything one transcription produced."""

    file_path: Path
    text: str
    segments: Sequence[Segment]
    language: str | None
    language_probability: float
    audio_duration: float
    elapsed: float
    model_size: str
    device_label: str

    def to_txt(self) -> str:
        """Clean text, newline-terminated."""
        return self.text.strip() + "\n" if self.text.strip() else ""

    def to_srt(self) -> str:
        return build_srt(self.segments)

    def summary(self) -> str:
        """Metadata block shown in the interface."""
        confidence = (
            t("summary.confidence", value=f"{self.language_probability:.0%}")
            if self.language_probability
            else ""
        )
        return "\n".join(
            (
                t("summary.file", name=self.file_path.name),
                t("summary.language", language=language_display_name(self.language)) + confidence,
                t("summary.model", model=self.model_size),
                t("summary.device", device=self.device_label),
                t("summary.duration", duration=format_duration(self.audio_duration)),
                t("summary.elapsed", seconds=f"{self.elapsed:.1f}"),
            )
        )

    def short_summary(self) -> str:
        """One-line version for tight spaces."""
        return t(
            "summary.short",
            duration=format_duration(self.audio_duration),
            seconds=f"{self.elapsed:.1f}",
            model=self.model_size,
            device=self.device_label,
        )


class _RetryOnCpu(Exception):
    """Internal signal that the GPU attempt failed and the CPU should take over."""

    def __init__(self, cause: Exception) -> None:
        super().__init__(str(cause))
        self.cause = cause


@dataclass(frozen=True, slots=True)
class _ModelKey:
    model_size: str
    device: str
    compute_type: str
    num_workers: int


class Transcriber:
    """Keeps one Whisper model in memory across transcriptions.

    The model is only reloaded when the user changes its size, the device or
    the number of concurrent workers, which saves several seconds per run.
    """

    def __init__(self, num_workers: int = 1) -> None:
        self._model: "WhisperModel | None" = None
        self._key: _ModelKey | None = None
        self._lock = threading.Lock()
        self._num_workers = max(1, int(num_workers))

    # ------------------------------------------------------------------ model

    @property
    def loaded_model(self) -> str | None:
        return self._key.model_size if self._key else None

    @property
    def num_workers(self) -> int:
        return self._num_workers

    def set_num_workers(self, value: int) -> None:
        """How many transcriptions may share the model at the same time.

        CTranslate2 needs this declared when the model is loaded, so changing
        it invalidates the cache.
        """
        value = max(1, int(value))
        if value != self._num_workers:
            self._num_workers = value
            self.unload()

    def unload(self) -> None:
        """Drop the cached model (used by the GPU to CPU fallback)."""
        with self._lock:
            self._model = None
            self._key = None

    def _get_model(
        self, model_size: str, device: DeviceChoice, progress: ProgressCallback | None
    ) -> "WhisperModel":
        key = _ModelKey(model_size, device.device, device.compute_type, self._num_workers)
        with self._lock:
            if self._model is not None and self._key == key:
                logger.debug("Reusing cached model: %s", key)
                return self._model

            _notify(progress, 0.03, t("status.loading_model", model=model_size, device=device.label))
            logger.info("Loading model %s on %s", model_size, device.device)
            self._model = _load_model(model_size, device, self._num_workers)
            self._key = key
            return self._model

    # ---------------------------------------------------------- transcription

    def transcribe(
        self,
        audio_path: str | Path,
        *,
        model_size: str,
        language: str | None,
        prefer_gpu: bool = True,
        progress: ProgressCallback | None = None,
        should_cancel: CancelCheck | None = None,
    ) -> TranscriptionResult:
        """Transcribe one file and return text, segments and metadata.

        Any GPU failure is automatically retried on the CPU.
        """
        path = validate_audio_file(audio_path)
        device = resolve_device(prefer_gpu)

        try:
            return self._attempt(path, model_size, language, device, progress, should_cancel)
        except _RetryOnCpu as retry:
            logger.warning("GPU failure (%s). Retrying on CPU.", retry.cause, exc_info=True)
            self.unload()
            _notify(progress, 0.0, t("status.gpu_fallback"))
            return self._attempt(path, model_size, language, CPU, progress, should_cancel)

    def _attempt(
        self,
        path: Path,
        model_size: str,
        language: str | None,
        device: DeviceChoice,
        progress: ProgressCallback | None,
        should_cancel: CancelCheck | None,
    ) -> TranscriptionResult:
        """One attempt on one device, with errors already translated.

        GPU failures become :class:`_RetryOnCpu` so the caller can fall back.
        """
        try:
            return self._run(path, model_size, language, device, progress, should_cancel)
        except (TranscriptionCancelled, NoSpeechError):
            raise
        except Exception as exc:
            if device.device != CPU.device:
                raise _RetryOnCpu(exc) from exc
            if isinstance(exc, AppError):
                raise  # already carries a user-facing message
            raise _friendly_error(exc, model_size, device) from exc

    def _run(
        self,
        path: Path,
        model_size: str,
        language: str | None,
        device: DeviceChoice,
        progress: ProgressCallback | None,
        should_cancel: CancelCheck | None,
    ) -> TranscriptionResult:
        model = self._get_model(model_size, device, progress)
        started = time.perf_counter()

        _notify(progress, 0.08, t("status.analyzing"))
        # ``language=None`` lets Whisper detect the language on its own.
        segment_iter, info = model.transcribe(
            str(path),
            language=language,
            beam_size=BEAM_SIZE,
            vad_filter=VAD_FILTER,
            vad_parameters={"min_silence_duration_ms": VAD_MIN_SILENCE_MS},
        )

        duration = float(getattr(info, "duration", 0.0) or 0.0)
        segments = _collect_segments(segment_iter, duration, progress, should_cancel)
        elapsed = time.perf_counter() - started

        if not segments:
            raise NoSpeechError("error.no_speech", hint_key="error.no_speech.hint")

        text = " ".join(segment.text.strip() for segment in segments).strip()
        _notify(progress, 1.0, t("status.finished"))
        logger.info(
            "Transcription finished: %s (%d segments, %.1fs of processing)",
            path.name,
            len(segments),
            elapsed,
        )
        return TranscriptionResult(
            file_path=path,
            text=text,
            segments=segments,
            language=getattr(info, "language", None),
            language_probability=float(getattr(info, "language_probability", 0.0) or 0.0),
            audio_duration=duration,
            elapsed=elapsed,
            model_size=model_size,
            device_label=device.label,
        )


# --------------------------------------------------------------------- helpers


def _notify(progress: ProgressCallback | None, fraction: float, message: str) -> None:
    if progress is not None:
        progress(fraction, message)


def _collect_segments(
    segment_iter,
    duration: float,
    progress: ProgressCallback | None,
    should_cancel: CancelCheck | None,
) -> list[Segment]:
    """Drain the faster-whisper generator while reporting progress.

    Decoding only happens while iterating, so cancellation and the progress
    bar are handled here.
    """
    segments: list[Segment] = []
    for raw in segment_iter:
        if should_cancel is not None and should_cancel():
            raise TranscriptionCancelled("error.cancelled")

        text = str(raw.text).strip()
        if text:
            segments.append(Segment(start=float(raw.start), end=float(raw.end), text=text))

        if duration > 0:
            fraction = min(0.99, max(0.1, float(raw.end) / duration))
            _notify(progress, fraction, t("status.transcribing_pct", percent=f"{fraction:.0%}"))
        else:
            _notify(progress, 0.5, t("status.transcribing_count", count=len(segments)))
    return segments


def _load_model(model_size: str, device: DeviceChoice, num_workers: int = 1) -> "WhisperModel":
    """Instantiate ``WhisperModel``, translating the usual failures."""
    whisper_model = _whisper_model()
    try:
        return whisper_model(
            model_size,
            device=device.device,
            compute_type=device.compute_type,
            num_workers=num_workers,
        )
    except AppError:
        raise
    except Exception as exc:
        raise _friendly_error(exc, model_size, device, loading=True) from exc


_OOM_MARKERS = ("out of memory", "cannot allocate", "bad_alloc", "cuda_error_out_of_memory")
_NETWORK_MARKERS = (
    "connection",
    "timed out",
    "timeout",
    "temporary failure in name resolution",
    "max retries exceeded",
    "offline mode",
    "couldn't connect",
    "network",
)
_NOT_FOUND_MARKERS = ("repository not found", "404", "is not a valid", "not a local folder")
_CUDA_MARKERS = ("cuda", "cudnn", "cublas", "no gpu", "libcudart")


def _friendly_error(
    exc: Exception, model_size: str, device: DeviceChoice, *, loading: bool = False
) -> AppError:
    """Map a technical exception onto a translated, actionable message."""
    logger.exception("Transcription error (%s, %s)", model_size, device.device)
    text = f"{type(exc).__name__}: {exc}".lower()

    if isinstance(exc, MemoryError) or any(marker in text for marker in _OOM_MARKERS):
        return OutOfMemoryError(
            "error.out_of_memory", hint_key="error.out_of_memory.hint", model=model_size
        )
    if any(marker in text for marker in _NETWORK_MARKERS):
        return ModelLoadError("error.download", hint_key="error.download.hint", model=model_size)
    if any(marker in text for marker in _NOT_FOUND_MARKERS):
        return ModelLoadError(
            "error.model_not_found", hint_key="error.model_not_found.hint", model=model_size
        )
    if any(marker in text for marker in _CUDA_MARKERS):
        return ModelLoadError("error.cuda", hint_key="error.cuda.hint")
    if isinstance(exc, (FileNotFoundError, PermissionError, OSError)) and not loading:
        return TranscriptionFailedError(
            "error.audio_decode", hint_key="error.audio_decode.hint"
        )

    key = "error.load_failed" if loading else "error.transcribe_failed"
    return TranscriptionFailedError(key, hint_key="error.log_hint", kind=type(exc).__name__)
