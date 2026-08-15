"""Runtime registration of the brand fonts.

The fonts ship in ``assets/fonts`` and are registered for this process only,
so nothing is installed into the user's system. If registration fails the
application keeps working with the fallback families.
"""

from __future__ import annotations

import ctypes
import logging
import os
import sys
from pathlib import Path

from .config import FONTS_DIRNAME
from .paths import resource_root

logger = logging.getLogger(__name__)

# Families expected after registration, in order of preference.
DISPLAY_CANDIDATES = ("Fraunces", "Georgia", "Times New Roman")
SANS_CANDIDATES = ("Instrument Sans", "InstrumentSans", "Helvetica Neue", "Segoe UI", "DejaVu Sans")


def font_files() -> list[Path]:
    directory = resource_root() / FONTS_DIRNAME
    return sorted(directory.glob("*.ttf")) if directory.is_dir() else []


def register_bundled_fonts() -> int:
    """Register the bundled fonts for this process. Returns how many loaded."""
    files = font_files()
    if not files:
        logger.info("No bundled fonts in %s - falling back to system fonts.", FONTS_DIRNAME)
        return 0

    register = _registrar_for_platform()
    registered = 0
    for path in files:
        try:
            if register(path):
                registered += 1
        except Exception:
            logger.warning("Could not register the font %s", path.name, exc_info=True)
    logger.info("Fonts registered: %d of %d", registered, len(files))
    return registered


def _registrar_for_platform():
    if sys.platform == "darwin":
        return _register_macos
    if os.name == "nt":
        return _register_windows
    return _register_linux


def _register_macos(path: Path) -> bool:
    """CTFontManagerRegisterFontsForURL, scoped to the current process."""
    from ctypes import util

    core = ctypes.cdll.LoadLibrary(util.find_library("CoreText"))
    foundation = ctypes.cdll.LoadLibrary(util.find_library("CoreFoundation"))

    foundation.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
    foundation.CFURLCreateFromFileSystemRepresentation.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_long,
        ctypes.c_bool,
    ]
    core.CTFontManagerRegisterFontsForURL.restype = ctypes.c_bool
    core.CTFontManagerRegisterFontsForURL.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]

    raw = str(path).encode("utf-8")
    url = foundation.CFURLCreateFromFileSystemRepresentation(None, raw, len(raw), False)
    if not url:
        return False
    try:
        # 1 = kCTFontManagerScopeProcess
        return bool(core.CTFontManagerRegisterFontsForURL(url, 1, None))
    finally:
        foundation.CFRelease.argtypes = [ctypes.c_void_p]
        foundation.CFRelease(url)


def _register_windows(path: Path) -> bool:
    """AddFontResourceEx with FR_PRIVATE: visible to this process only."""
    gdi = ctypes.WinDLL("gdi32")  # type: ignore[attr-defined]
    return bool(gdi.AddFontResourceExW(ctypes.c_wchar_p(str(path)), 0x10, 0))


def _register_linux(path: Path) -> bool:
    """On Linux Tk reads the user fontconfig directory, so copy the file there."""
    target_dir = Path.home() / ".local/share/fonts"
    target = target_dir / path.name
    if target.exists():
        return True
    target_dir.mkdir(parents=True, exist_ok=True)
    target.write_bytes(path.read_bytes())
    os.system("fc-cache -f >/dev/null 2>&1")
    return True


def resolve_family(candidates: tuple[str, ...], available: set[str], fallback: str) -> str:
    """First available family from the preference list."""
    for name in candidates:
        if name in available:
            return name
    return fallback
