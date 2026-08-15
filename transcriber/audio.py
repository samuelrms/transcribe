"""Audio file validation and metadata, with no heavy dependencies."""

from __future__ import annotations

from pathlib import Path

from .config import SUPPORTED_EXTENSIONS
from .errors import AudioFileError, UnsupportedFormatError
from .i18n import t


def is_supported_audio(path: str | Path) -> bool:
    """True when the file extension is in the supported list."""
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def validate_audio_file(path: str | Path) -> Path:
    """Validate the file and return its absolute path.

    Raises :class:`AudioFileError` or :class:`UnsupportedFormatError`, both of
    which already carry a translated, user-readable message.
    """
    if not str(path).strip():
        raise AudioFileError("error.no_file")

    audio = Path(path).expanduser()

    if not audio.exists():
        raise AudioFileError("error.not_found", hint_key="error.not_found.hint", path=audio)
    if not audio.is_file():
        raise AudioFileError("error.not_a_file", path=audio)
    if not is_supported_audio(audio):
        raise UnsupportedFormatError(
            "error.unsupported",
            hint_key="error.unsupported.hint",
            suffix=audio.suffix or t("error.no_extension"),
            formats=", ".join(SUPPORTED_EXTENSIONS),
        )
    try:
        size = audio.stat().st_size
    except OSError as exc:
        raise AudioFileError("error.unreadable", path=audio) from exc
    if size == 0:
        raise AudioFileError("error.empty_file")

    return audio.resolve()


def filedialog_filetypes() -> list[tuple[str, str]]:
    """Filters for the Tkinter file chooser."""
    patterns = " ".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS)
    return [(t("dialog.audio_files"), patterns), (t("dialog.all_files"), "*.*")]


def format_duration(seconds: float | None) -> str:
    """Format seconds as ``mm:ss``, or ``h:mm:ss`` past one hour."""
    if seconds is None or seconds < 0:
        return "--:--"
    total = int(round(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
