"""Shared configuration constants.

User-facing text lives in :mod:`transcriber.i18n`; this module only holds
values and identifiers.
"""

from __future__ import annotations

from typing import Final

LOG_FILENAME: Final = "transcriber.log"
OUTPUT_DIRNAME: Final = "output"
FONTS_DIRNAME: Final = "assets/fonts"

# Accepted extensions, always lowercase and dotted.
SUPPORTED_EXTENSIONS: Final[tuple[str, ...]] = (
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
    ".opus",
    ".aac",
    ".flac",
)

# Translation key -> Whisper language code (``None`` means auto-detect).
LANGUAGE_CHOICES: Final[tuple[tuple[str, str | None], ...]] = (
    ("language.pt", "pt"),
    ("language.auto", None),
    ("language.en", "en"),
    ("language.es", "es"),
)
DEFAULT_LANGUAGE_KEY: Final = "language.pt"

MODEL_CHOICES: Final[tuple[str, ...]] = ("tiny", "base", "small", "medium", "large-v3")
DEFAULT_MODEL: Final = "medium"

# Approximate download size, shown to the user before the first run.
MODEL_DOWNLOAD_SIZES: Final[dict[str, str]] = {
    "tiny": "~75 MB",
    "base": "~145 MB",
    "small": "~480 MB",
    "medium": "~1,5 GB",
    "large-v3": "~3,1 GB",
}

# How many files may be transcribed at the same time. One is the default:
# CTranslate2 already uses every core on a single file, so running in parallel
# multiplies memory use without improving throughput on CPU.
WORKER_CHOICES: Final[tuple[int, ...]] = (1, 2, 3)
DEFAULT_WORKERS: Final = 1

# Above this size, running in parallel tends to exhaust memory.
HEAVY_MODELS: Final[frozenset[str]] = frozenset({"medium", "large-v3"})

BEAM_SIZE: Final = 5
VAD_FILTER: Final = True
# Silences longer than this (ms) are dropped by the VAD.
VAD_MIN_SILENCE_MS: Final = 800

# Portuguese/English names for the most common Whisper language codes.
LANGUAGE_LABELS: Final[dict[str, dict[str, str]]] = {
    "pt": {"pt-BR": "Português", "en": "Portuguese"},
    "en": {"pt-BR": "Inglês", "en": "English"},
    "es": {"pt-BR": "Espanhol", "en": "Spanish"},
    "fr": {"pt-BR": "Francês", "en": "French"},
    "de": {"pt-BR": "Alemão", "en": "German"},
    "it": {"pt-BR": "Italiano", "en": "Italian"},
    "nl": {"pt-BR": "Holandês", "en": "Dutch"},
    "ru": {"pt-BR": "Russo", "en": "Russian"},
    "ja": {"pt-BR": "Japonês", "en": "Japanese"},
    "zh": {"pt-BR": "Chinês", "en": "Chinese"},
    "ko": {"pt-BR": "Coreano", "en": "Korean"},
    "ar": {"pt-BR": "Árabe", "en": "Arabic"},
    "gl": {"pt-BR": "Galego", "en": "Galician"},
    "ca": {"pt-BR": "Catalão", "en": "Catalan"},
}
