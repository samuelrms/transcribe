"""Tests for the batch queue: deduplication, state, progress and export paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from transcriber.batch import Batch, Job, JobStatus, unique_path
from transcriber.transcription import Segment, TranscriptionResult


def make_result(elapsed: float = 3.5) -> TranscriptionResult:
    return TranscriptionResult(
        file_path=Path("/tmp/note.mp3"),
        text="olá",
        segments=[Segment(0.0, 1.0, "olá")],
        language="pt",
        language_probability=1.0,
        audio_duration=1.0,
        elapsed=elapsed,
        model_size="small",
        device_label="CPU",
    )


def write_audio(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.write_bytes(b"\x00")
    return path


# ---------------------------------------------------------------------- queue


def test_add_accepts_supported_files(tmp_path) -> None:
    batch = Batch()
    added = batch.add([write_audio(tmp_path, "a.mp3"), write_audio(tmp_path, "b.ogg")])
    assert added == 2
    assert len(batch) == 2


def test_add_skips_unsupported_formats(tmp_path) -> None:
    batch = Batch()
    assert batch.add([write_audio(tmp_path, "clip.mp4")]) == 0
    assert len(batch) == 0


def test_add_deduplicates_the_same_file(tmp_path) -> None:
    audio = write_audio(tmp_path, "a.mp3")
    batch = Batch()
    assert batch.add([audio]) == 1
    assert batch.add([audio]) == 0
    assert len(batch) == 1


def test_add_deduplicates_across_relative_and_absolute_paths(tmp_path, monkeypatch) -> None:
    audio = write_audio(tmp_path, "a.mp3")
    monkeypatch.chdir(tmp_path)
    batch = Batch()
    batch.add([audio])
    assert batch.add(["a.mp3"]) == 0


def test_clear_empties_the_queue(tmp_path) -> None:
    batch = Batch()
    batch.add([write_audio(tmp_path, "a.mp3")])
    batch.clear()
    assert len(batch) == 0


def test_remove_finished_keeps_only_unfinished_jobs(tmp_path) -> None:
    batch = Batch()
    batch.add([write_audio(tmp_path, f"{name}.mp3") for name in "abcd"])
    batch.jobs[0].finish(make_result())
    batch.jobs[1].fail("boom")
    batch.jobs[2].cancel()
    batch.remove_finished()
    assert [job.status for job in batch] == [JobStatus.PENDING]


def test_index_of_returns_the_position(tmp_path) -> None:
    batch = Batch()
    batch.add([write_audio(tmp_path, "a.mp3"), write_audio(tmp_path, "b.mp3")])
    assert batch.index_of(batch.jobs[1]) == 1


# ----------------------------------------------------------------- job states


def test_job_starts_pending(tmp_path) -> None:
    job = Job(path=write_audio(tmp_path, "a.mp3"))
    assert job.status is JobStatus.PENDING
    assert job.text == ""


def test_finish_stores_result_and_elapsed(tmp_path) -> None:
    job = Job(path=write_audio(tmp_path, "a.mp3"))
    job.finish(make_result(elapsed=7.25))
    assert job.status is JobStatus.DONE
    assert job.progress == 1.0
    assert job.text == "olá"
    assert job.message == "7.2s"


def test_fail_records_the_message(tmp_path) -> None:
    job = Job(path=write_audio(tmp_path, "a.mp3"))
    job.fail("no memory")
    assert job.status is JobStatus.ERROR
    assert job.error == "no memory"


def test_start_clears_a_previous_error(tmp_path) -> None:
    job = Job(path=write_audio(tmp_path, "a.mp3"))
    job.fail("boom")
    job.start()
    assert job.status is JobStatus.RUNNING
    assert job.error is None


@pytest.mark.parametrize(
    ("status", "final"),
    [
        (JobStatus.PENDING, False),
        (JobStatus.RUNNING, False),
        (JobStatus.DONE, True),
        (JobStatus.ERROR, True),
        (JobStatus.CANCELLED, True),
    ],
)
def test_is_final_flags_terminal_states(status: JobStatus, final: bool) -> None:
    assert status.is_final is final


def test_status_label_is_translated() -> None:
    from transcriber import i18n

    assert JobStatus.DONE.label == "concluído"
    i18n.set_language(i18n.EN)
    try:
        assert JobStatus.DONE.label == "done"
    finally:
        i18n.set_language(i18n.DEFAULT_LANGUAGE)


# -------------------------------------------------------------------- progress


def test_overall_progress_is_zero_for_an_empty_batch() -> None:
    assert Batch().overall_progress() == 0.0


def test_overall_progress_averages_jobs(tmp_path) -> None:
    batch = Batch()
    batch.add([write_audio(tmp_path, "a.mp3"), write_audio(tmp_path, "b.mp3")])
    batch.jobs[0].finish(make_result())
    batch.jobs[1].progress = 0.5
    assert batch.overall_progress() == pytest.approx(0.75)


def test_overall_progress_never_exceeds_one(tmp_path) -> None:
    batch = Batch()
    batch.add([write_audio(tmp_path, "a.mp3")])
    batch.jobs[0].finish(make_result())
    batch.jobs[0].progress = 5.0
    assert batch.overall_progress() == 1.0


def test_summary_line_reports_each_bucket(tmp_path) -> None:
    batch = Batch()
    batch.add([write_audio(tmp_path, f"{name}.mp3") for name in "abc"])
    batch.jobs[0].finish(make_result())
    batch.jobs[1].start()
    summary = batch.summary_line()
    assert "1 concluído(s)" in summary
    assert "1 transcrevendo" in summary
    assert "1 na fila" in summary


def test_summary_line_when_empty() -> None:
    assert Batch().summary_line() == "nenhum arquivo na fila"


def test_pending_and_with_results_filter_correctly(tmp_path) -> None:
    batch = Batch()
    batch.add([write_audio(tmp_path, "a.mp3"), write_audio(tmp_path, "b.mp3")])
    batch.jobs[0].finish(make_result())
    assert len(batch.pending()) == 1
    assert len(batch.with_results()) == 1


# ----------------------------------------------------------------- export path


def test_unique_path_uses_the_plain_name_when_free(tmp_path) -> None:
    assert unique_path(tmp_path, "note", ".txt") == tmp_path / "note.txt"


def test_unique_path_appends_a_counter_on_collision(tmp_path) -> None:
    (tmp_path / "note.txt").write_text("x")
    (tmp_path / "note-2.txt").write_text("x")
    assert unique_path(tmp_path, "note", ".txt") == tmp_path / "note-3.txt"


def test_unique_path_keeps_extensions_apart(tmp_path) -> None:
    (tmp_path / "note.txt").write_text("x")
    assert unique_path(tmp_path, "note", ".srt") == tmp_path / "note.srt"


# ------------------------------------------------------------- model cache


def test_hub_cache_dir_honours_hf_hub_cache(monkeypatch, tmp_path) -> None:
    from transcriber.model_store import hub_cache_dir

    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
    assert hub_cache_dir() == tmp_path


def test_hub_cache_dir_falls_back_to_hf_home(monkeypatch, tmp_path) -> None:
    from transcriber.model_store import hub_cache_dir

    monkeypatch.delenv("HF_HUB_CACHE", raising=False)
    monkeypatch.delenv("HUGGINGFACE_HUB_CACHE", raising=False)
    monkeypatch.setenv("HF_HOME", str(tmp_path))
    assert hub_cache_dir() == tmp_path / "hub"


def test_model_is_not_cached_when_absent(monkeypatch, tmp_path) -> None:
    from transcriber.model_store import is_model_cached

    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
    assert is_model_cached("medium") is False


def test_model_is_cached_when_weights_exist(monkeypatch, tmp_path) -> None:
    from transcriber.model_store import is_model_cached

    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
    snapshot = tmp_path / "models--Systran--faster-whisper-medium" / "snapshots" / "abc123"
    snapshot.mkdir(parents=True)
    (snapshot / "model.bin").write_bytes(b"\x00")
    assert is_model_cached("medium") is True


def test_snapshot_without_weights_is_not_cached(monkeypatch, tmp_path) -> None:
    from transcriber.model_store import is_model_cached

    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
    snapshot = tmp_path / "models--Systran--faster-whisper-small" / "snapshots" / "abc123"
    snapshot.mkdir(parents=True)
    (snapshot / "config.json").write_text("{}")
    assert is_model_cached("small") is False


def test_local_directory_counts_as_cached(tmp_path) -> None:
    from transcriber.model_store import is_model_cached

    assert is_model_cached(str(tmp_path)) is True
