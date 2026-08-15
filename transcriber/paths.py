"""Project directories, working both from source and from a frozen build.

Running from source keeps everything inside the repository, which is handy
while developing. A packaged build must never write into its own bundle: on
macOS the .app lives in a read-only location and writing there breaks the
signature, and on Windows Program Files is not user-writable either.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .config import OUTPUT_DIRNAME

APP_DIRNAME = "Transcriber"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def project_root() -> Path:
    """Repository root when running from source."""
    return Path(__file__).resolve().parent.parent


def resource_root() -> Path:
    """Base directory for bundled read-only assets such as fonts.

    PyInstaller unpacks them into ``sys._MEIPASS``, which is not the same as
    the executable folder.
    """
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        return Path(bundled)
    return Path(sys.executable).parent if is_frozen() else project_root()


def user_data_dir() -> Path:
    """Per-user writable directory, following each platform's convention."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIRNAME
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / APP_DIRNAME
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / APP_DIRNAME


def log_dir() -> Path:
    """Where the log file goes: the repository from source, the OS spot when frozen."""
    if not is_frozen():
        return project_root()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / APP_DIRNAME
    return user_data_dir()


def output_dir() -> Path:
    """Default folder suggested when saving TXT/SRT, created on demand.

    From source it is the repository's ``output/``; a packaged build suggests
    the user's Documents folder, because nobody looks for their transcripts
    inside an application bundle.
    """
    if is_frozen():
        documents = Path.home() / "Documents"
        path = (documents if documents.is_dir() else Path.home()) / APP_DIRNAME
    else:
        path = project_root() / OUTPUT_DIRNAME
    return _ensure(path)


def _ensure(path: Path) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return Path.home()
    return path
