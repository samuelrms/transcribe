"""Tests for the transcription core using doubles - no model is ever loaded."""

from __future__ import annotations

from pathlib import Path

import pytest

from transcriber.device import CPU, CUDA, resolve_device
from transcriber.errors import (
    ModelLoadError,
    NoSpeechError,
    OutOfMemoryError,
    TranscriptionCancelled,
    TranscriptionFailedError,
)
from transcriber.srt import seconds_to_srt_timestamp
from transcriber.transcription import (
    Segment,
    Transcriber,
    TranscriptionResult,
    _collect_segments,
    _friendly_error,
)


def make_result(**overrides) -> TranscriptionResult:
    defaults = dict(
        file_path=Path("/tmp/audio_whatsapp.mp3"),
        text="Olá, tudo bem?",
        segments=[Segment(0.0, 4.5, "Olá, tudo bem?")],
        language="pt",
        language_probability=0.99,
        audio_duration=8.2,
        elapsed=14.2,
        model_size="small",
        device_label="CPU",
    )
    defaults.update(overrides)
    return TranscriptionResult(**defaults)


class FakeRaw:
    def __init__(self, start: float, end: float, text: str) -> None:
        self.start, self.end, self.text = start, end, text


class FakeInfo:
    duration = 8.2
    language = "pt"
    language_probability = 0.98


class FakeModel:
    """Fake model that optionally raises, to simulate a GPU failure."""

    def __init__(self, fail_with: Exception | None = None) -> None:
        self.fail_with = fail_with
        self.calls = 0

    def transcribe(self, *_args, **_kwargs):
        self.calls += 1
        if self.fail_with is not None:
            raise self.fail_with
        return iter([FakeRaw(0.0, 4.5, "Olá"), FakeRaw(4.5, 8.2, "tudo bem")]), FakeInfo()


def build_transcriber(monkeypatch, models: dict[str, FakeModel], cuda: bool = True):
    monkeypatch.setattr("transcriber.device.cuda_device_count", lambda: 1 if cuda else 0)
    transcriber = Transcriber()
    used: list[str] = []

    def fake_get_model(model_size, device, progress):
        used.append(device.device)
        return models[device.device]

    monkeypatch.setattr(transcriber, "_get_model", fake_get_model)
    return transcriber, used


# -------------------------------------------------------------------- result


def test_summary_lists_all_required_fields() -> None:
    summary = make_result().summary()
    assert "Arquivo: audio_whatsapp.mp3" in summary
    assert "Idioma detectado: Português (pt)" in summary
    assert "Modelo: small" in summary
    assert "Dispositivo: CPU" in summary
    assert "Duração do áudio: 00:08" in summary
    assert "Tempo de processamento: 14.2 segundos" in summary


def test_summary_follows_the_interface_language() -> None:
    from transcriber import i18n

    i18n.set_language(i18n.EN)
    try:
        summary = make_result().summary()
        assert "File: audio_whatsapp.mp3" in summary
        assert "Detected language: Portuguese (pt)" in summary
    finally:
        i18n.set_language(i18n.DEFAULT_LANGUAGE)


def test_to_txt_has_clean_text_and_trailing_newline() -> None:
    assert make_result(text="  Olá  ").to_txt() == "Olá\n"


def test_to_txt_is_empty_when_there_is_no_text() -> None:
    assert make_result(text="   ").to_txt() == ""


def test_to_srt_uses_result_segments() -> None:
    result = make_result(
        segments=[Segment(0.0, 4.5, "Olá, tudo bem?"), Segment(4.5, 8.2, "Tudo certo.")]
    )
    srt = result.to_srt()
    assert srt.startswith("1\n00:00:00,000 --> 00:00:04,500\n")
    assert srt.rstrip().endswith("Tudo certo.")
    assert seconds_to_srt_timestamp(8.2) in srt


def test_summary_handles_unknown_language() -> None:
    assert "não identificado" in make_result(language=None, language_probability=0.0).summary()


def test_short_summary_is_single_line() -> None:
    short = make_result().short_summary()
    assert "\n" not in short
    assert "small" in short and "CPU" in short


# ------------------------------------------------------------------ progress


def test_collect_segments_reports_progress_and_drops_blanks() -> None:
    events: list[tuple[float, str]] = []
    segments = _collect_segments(
        [FakeRaw(0.0, 5.0, " oi "), FakeRaw(5.0, 10.0, "  "), FakeRaw(5.0, 10.0, "tudo bem")],
        duration=10.0,
        progress=lambda fraction, message: events.append((fraction, message)),
        should_cancel=None,
    )
    assert [segment.text for segment in segments] == ["oi", "tudo bem"]
    assert events[0][0] == pytest.approx(0.5)
    assert events[-1][0] == pytest.approx(0.99)  # never reaches 100% before the end


def test_collect_segments_stops_when_cancelled() -> None:
    with pytest.raises(TranscriptionCancelled):
        _collect_segments(
            [FakeRaw(0.0, 1.0, "oi")], duration=10.0, progress=None, should_cancel=lambda: True
        )


# ------------------------------------------------------------ friendly errors


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (MemoryError("out of memory"), OutOfMemoryError),
        (RuntimeError("CUDA failed with error out of memory"), OutOfMemoryError),
        (OSError("Max retries exceeded with url"), ModelLoadError),
        (ValueError("Repository Not Found for url"), ModelLoadError),
        (RuntimeError("Library libcudart.so is not found"), ModelLoadError),
        (RuntimeError("something completely unexpected"), TranscriptionFailedError),
    ],
)
def test_friendly_error_maps_known_failures(exc: Exception, expected: type) -> None:
    friendly = _friendly_error(exc, "small", CPU)
    assert isinstance(friendly, expected)
    assert friendly.message
    assert "Traceback" not in friendly.display()


def test_friendly_error_always_returns_display_text() -> None:
    friendly = _friendly_error(Exception("boom"), "small", CPU, loading=True)
    assert "carregar o modelo" in friendly.display()


# ------------------------------------------------------ device and fallback


def test_resolve_device_returns_cpu_when_gpu_not_requested() -> None:
    assert resolve_device(prefer_gpu=False) == CPU


def test_resolve_device_falls_back_to_cpu_without_cuda(monkeypatch) -> None:
    monkeypatch.setattr("transcriber.device.cuda_device_count", lambda: 0)
    assert resolve_device(prefer_gpu=True) == CPU


def test_resolve_device_uses_cuda_when_available(monkeypatch) -> None:
    monkeypatch.setattr("transcriber.device.cuda_device_count", lambda: 1)
    assert resolve_device(prefer_gpu=True) == CUDA


def test_cpu_profile_uses_int8() -> None:
    assert (CPU.device, CPU.compute_type) == ("cpu", "int8")


def test_gpu_failure_falls_back_to_cpu(monkeypatch, tmp_path) -> None:
    audio = tmp_path / "note.ogg"
    audio.write_bytes(b"\x00")
    models = {
        "cuda": FakeModel(RuntimeError("CUDA driver version is insufficient")),
        "cpu": FakeModel(),
    }
    transcriber, used = build_transcriber(monkeypatch, models)

    result = transcriber.transcribe(audio, model_size="small", language="pt", prefer_gpu=True)

    assert used == ["cuda", "cpu"]
    assert result.device_label == "CPU"
    assert result.text == "Olá tudo bem"


def test_cpu_failure_keeps_friendly_message(monkeypatch, tmp_path) -> None:
    audio = tmp_path / "note.mp3"
    audio.write_bytes(b"\x00")
    transcriber, _ = build_transcriber(
        monkeypatch, {"cpu": FakeModel(MemoryError("out of memory"))}, cuda=False
    )
    with pytest.raises(OutOfMemoryError):
        transcriber.transcribe(audio, model_size="large-v3", language=None, prefer_gpu=True)


def test_already_friendly_errors_are_not_rewrapped(monkeypatch, tmp_path) -> None:
    audio = tmp_path / "note.mp3"
    audio.write_bytes(b"\x00")
    original = ModelLoadError("error.missing_library")
    transcriber, _ = build_transcriber(monkeypatch, {"cpu": FakeModel(original)}, cuda=False)

    with pytest.raises(ModelLoadError) as info:
        transcriber.transcribe(audio, model_size="small", language="pt", prefer_gpu=False)
    assert info.value is original


def test_audio_without_speech_raises_no_speech(monkeypatch, tmp_path) -> None:
    audio = tmp_path / "silence.wav"
    audio.write_bytes(b"\x00")

    class Silent(FakeModel):
        def transcribe(self, *_args, **_kwargs):
            return iter([]), FakeInfo()

    transcriber, _ = build_transcriber(monkeypatch, {"cpu": Silent()}, cuda=False)
    with pytest.raises(NoSpeechError):
        transcriber.transcribe(audio, model_size="small", language="pt", prefer_gpu=False)


def test_model_is_cached_between_transcriptions(monkeypatch, tmp_path) -> None:
    audio = tmp_path / "note.mp3"
    audio.write_bytes(b"\x00")
    loads: list[str] = []
    model = FakeModel()

    monkeypatch.setattr("transcriber.device.cuda_device_count", lambda: 0)
    monkeypatch.setattr(
        "transcriber.transcription._load_model",
        lambda size, device, workers=1: (loads.append(size), model)[1],
    )
    transcriber = Transcriber()
    for _ in range(3):
        transcriber.transcribe(audio, model_size="small", language="pt", prefer_gpu=False)

    assert loads == ["small"]  # loaded exactly once
    assert transcriber.loaded_model == "small"


def test_changing_worker_count_invalidates_the_cache(monkeypatch, tmp_path) -> None:
    audio = tmp_path / "note.mp3"
    audio.write_bytes(b"\x00")
    loads: list[int] = []

    monkeypatch.setattr("transcriber.device.cuda_device_count", lambda: 0)
    monkeypatch.setattr(
        "transcriber.transcription._load_model",
        lambda size, device, workers=1: (loads.append(workers), FakeModel())[1],
    )
    transcriber = Transcriber()
    transcriber.transcribe(audio, model_size="small", language="pt", prefer_gpu=False)
    transcriber.set_num_workers(2)
    transcriber.transcribe(audio, model_size="small", language="pt", prefer_gpu=False)

    assert loads == [1, 2]
    assert transcriber.num_workers == 2
