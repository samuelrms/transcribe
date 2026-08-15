"""SRT timestamp conversion and subtitle assembly.

Pure module: it imports neither ``faster_whisper`` nor Tkinter, so it can be
tested without downloading any model.
"""

from __future__ import annotations

import math
from typing import Iterable, Protocol, runtime_checkable

MILLIS_PER_HOUR = 3_600_000
MILLIS_PER_MINUTE = 60_000
MILLIS_PER_SECOND = 1_000


@runtime_checkable
class TimedText(Protocol):
    """Anything with a start, an end and some text can become a subtitle."""

    start: float
    end: float
    text: str


def seconds_to_srt_timestamp(seconds: float) -> str:
    """Convert seconds into ``HH:MM:SS,mmm``.

    >>> seconds_to_srt_timestamp(4.5)
    '00:00:04,500'
    >>> seconds_to_srt_timestamp(3661.007)
    '01:01:01,007'
    """
    value = float(seconds)
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"Invalid timestamp: {seconds!r}")

    total_ms = int(round(max(0.0, value) * MILLIS_PER_SECOND))
    hours, rest = divmod(total_ms, MILLIS_PER_HOUR)
    minutes, rest = divmod(rest, MILLIS_PER_MINUTE)
    secs, millis = divmod(rest, MILLIS_PER_SECOND)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def normalize_text(text: str) -> str:
    """Collapse repeated whitespace and stray line breaks in a segment."""
    return " ".join(text.split())


def build_srt(segments: Iterable[TimedText]) -> str:
    """Build the full contents of an ``.srt`` file.

    Empty segments are skipped and numbering is always sequential from 1. An
    ``end`` earlier than ``start`` is clamped to ``start``.
    """
    blocks: list[str] = []
    for segment in segments:
        text = normalize_text(segment.text)
        if not text:
            continue
        start = max(0.0, float(segment.start))
        end = max(start, float(segment.end))
        blocks.append(
            f"{len(blocks) + 1}\n"
            f"{seconds_to_srt_timestamp(start)} --> {seconds_to_srt_timestamp(end)}\n"
            f"{text}\n"
        )
    return "\n".join(blocks)
