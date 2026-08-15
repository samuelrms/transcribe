"""Application errors.

Every error derived from :class:`AppError` carries translation keys instead of
literal text, so the message always follows the interface language selected at
display time. Technical tracebacks stay in the log file.
"""

from __future__ import annotations

from .i18n import t


class AppError(Exception):
    """Error with a user-facing, translated message."""

    def __init__(self, key: str, *, hint_key: str | None = None, **params: object) -> None:
        super().__init__(key)
        self.key = key
        self.hint_key = hint_key
        self.params = params

    @property
    def message(self) -> str:
        return t(self.key, **self.params)

    @property
    def hint(self) -> str | None:
        return t(self.hint_key, **self.params) if self.hint_key else None

    def display(self) -> str:
        hint = self.hint
        return f"{self.message}\n\n{hint}" if hint else self.message


class AudioFileError(AppError):
    """Missing, unreadable or empty file."""


class UnsupportedFormatError(AudioFileError):
    """Audio extension outside the supported list."""


class ModelLoadError(AppError):
    """Failure downloading or loading the Whisper model."""


class OutOfMemoryError(AppError):
    """Not enough RAM or VRAM for the chosen model."""


class NoSpeechError(AppError):
    """The VAD found no speech in the audio."""


class TranscriptionFailedError(AppError):
    """Generic failure while decoding the audio."""


class TranscriptionCancelled(AppError):
    """The user cancelled the running transcription."""
