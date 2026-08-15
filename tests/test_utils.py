"""Tests for the pure helpers: timestamps, SRT and file validation.

No test here downloads or loads a Whisper model.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from transcriber.audio import format_duration, is_supported_audio, validate_audio_file
from transcriber.config import SUPPORTED_EXTENSIONS
from transcriber.errors import AudioFileError, UnsupportedFormatError
from transcriber.srt import build_srt, normalize_text, seconds_to_srt_timestamp


@dataclass
class FakeSegment:
    start: float
    end: float
    text: str


# --------------------------------------------------- seconds_to_srt_timestamp


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "00:00:00,000"),
        (0.5, "00:00:00,500"),
        (4.5, "00:00:04,500"),
        (8.2, "00:00:08,200"),
        (59.999, "00:00:59,999"),
        (60, "00:01:00,000"),
        (3600, "01:00:00,000"),
        (3661.007, "01:01:01,007"),
        (7325.5, "02:02:05,500"),
    ],
)
def test_timestamp_formats_expected_values(seconds: float, expected: str) -> None:
    assert seconds_to_srt_timestamp(seconds) == expected


def test_timestamp_always_has_srt_shape() -> None:
    assert len(seconds_to_srt_timestamp(12.3456)) == len("00:00:00,000")


def test_timestamp_rounds_to_nearest_millisecond() -> None:
    assert seconds_to_srt_timestamp(1.00049) == "00:00:01,000"
    assert seconds_to_srt_timestamp(1.0006) == "00:00:01,001"
    assert seconds_to_srt_timestamp(59.9999) == "00:01:00,000"


def test_timestamp_clamps_negative_values_to_zero() -> None:
    assert seconds_to_srt_timestamp(-3.2) == "00:00:00,000"


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_timestamp_rejects_invalid_numbers(value: float) -> None:
    with pytest.raises(ValueError):
        seconds_to_srt_timestamp(value)


# ------------------------------------------------------------------- build_srt


def test_build_srt_matches_expected_layout() -> None:
    segments = [
        FakeSegment(0.0, 4.5, "Olá, tudo bem?"),
        FakeSegment(4.5, 8.2, "Estou enviando esse áudio..."),
    ]
    assert build_srt(segments) == (
        "1\n"
        "00:00:00,000 --> 00:00:04,500\n"
        "Olá, tudo bem?\n"
        "\n"
        "2\n"
        "00:00:04,500 --> 00:00:08,200\n"
        "Estou enviando esse áudio...\n"
    )


def test_build_srt_returns_empty_string_without_segments() -> None:
    assert build_srt([]) == ""


def test_build_srt_skips_blank_segments_and_keeps_numbering_sequential() -> None:
    segments = [
        FakeSegment(0.0, 1.0, "first"),
        FakeSegment(1.0, 2.0, "   "),
        FakeSegment(2.0, 3.0, "second"),
    ]
    srt = build_srt(segments)
    assert srt.splitlines()[0] == "1"
    assert "\n2\n" in srt
    assert srt.count("-->") == 2


def test_build_srt_normalizes_internal_whitespace() -> None:
    srt = build_srt([FakeSegment(0.0, 1.0, "  texto\n  com   espaços  ")])
    assert "texto com espaços" in srt


def test_build_srt_fixes_end_before_start() -> None:
    srt = build_srt([FakeSegment(5.0, 2.0, "reversed")])
    assert "00:00:05,000 --> 00:00:05,000" in srt


def test_normalize_text_collapses_whitespace() -> None:
    assert normalize_text("  a \n b\t c ") == "a b c"


# ------------------------------------------------------- extensions and files


@pytest.mark.parametrize("extension", SUPPORTED_EXTENSIONS)
def test_all_declared_extensions_are_supported(extension: str) -> None:
    assert is_supported_audio(f"audio{extension}")


def test_supported_extensions_cover_common_voice_formats() -> None:
    assert {".mp3", ".wav", ".m4a", ".ogg", ".opus", ".aac", ".flac"} <= set(SUPPORTED_EXTENSIONS)


@pytest.mark.parametrize("name", ["AUDIO.MP3", "note.Ogg", "voice.OpUs"])
def test_extension_check_is_case_insensitive(name: str) -> None:
    assert is_supported_audio(name)


@pytest.mark.parametrize("name", ["video.mp4", "doc.pdf", "no_extension", "audio.mp3.txt"])
def test_rejects_unsupported_extensions(name: str) -> None:
    assert not is_supported_audio(name)


def test_validate_accepts_existing_audio_file(tmp_path) -> None:
    audio = tmp_path / "note.mp3"
    audio.write_bytes(b"\x00\x01\x02")
    assert validate_audio_file(audio) == audio.resolve()


def test_validate_rejects_missing_file(tmp_path) -> None:
    with pytest.raises(AudioFileError):
        validate_audio_file(tmp_path / "missing.mp3")


def test_validate_rejects_empty_selection() -> None:
    with pytest.raises(AudioFileError):
        validate_audio_file("   ")


def test_validate_rejects_directory(tmp_path) -> None:
    with pytest.raises(AudioFileError):
        validate_audio_file(tmp_path)


def test_validate_rejects_empty_file(tmp_path) -> None:
    audio = tmp_path / "empty.wav"
    audio.write_bytes(b"")
    with pytest.raises(AudioFileError):
        validate_audio_file(audio)


def test_validate_rejects_unsupported_extension(tmp_path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"\x00")
    with pytest.raises(UnsupportedFormatError) as info:
        validate_audio_file(video)
    assert ".mp4" in info.value.message


# -------------------------------------------------------------------- duration


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0, "00:00"), (9.4, "00:09"), (65, "01:05"), (3725, "1:02:05"), (None, "--:--")],
)
def test_format_duration(seconds: float | None, expected: str) -> None:
    assert format_duration(seconds) == expected
