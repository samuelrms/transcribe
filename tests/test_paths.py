"""Tests for directory resolution from source and from a frozen build."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from transcriber import paths


@pytest.fixture
def frozen(monkeypatch):
    """Pretend the application is running from a PyInstaller bundle."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    yield


def test_not_frozen_when_running_from_source() -> None:
    assert paths.is_frozen() is False


def test_project_root_holds_the_package() -> None:
    assert (paths.project_root() / "transcriber" / "__init__.py").exists()


def test_resource_root_finds_the_bundled_fonts() -> None:
    assert (paths.resource_root() / "assets" / "fonts").is_dir()


def test_resource_root_uses_meipass_when_bundled(monkeypatch, tmp_path, frozen) -> None:
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert paths.resource_root() == tmp_path


def test_log_goes_to_the_repository_from_source() -> None:
    assert paths.log_dir() == paths.project_root()


def test_log_leaves_the_bundle_when_frozen(frozen) -> None:
    log_directory = paths.log_dir()
    assert log_directory != paths.project_root()
    assert Path.home() in log_directory.parents or log_directory == Path.home()


def test_output_is_the_repository_folder_from_source() -> None:
    assert paths.output_dir() == paths.project_root() / "output"


def test_output_leaves_the_bundle_when_frozen(frozen) -> None:
    output = paths.output_dir()
    assert "Transcriber" in output.parts
    assert Path.home() in output.parents


def test_user_data_dir_is_under_the_home_directory() -> None:
    assert Path.home() in paths.user_data_dir().parents


@pytest.mark.skipif(sys.platform != "linux", reason="XDG is a Linux convention")
def test_user_data_dir_honours_xdg(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert paths.user_data_dir() == tmp_path / "Transcriber"
