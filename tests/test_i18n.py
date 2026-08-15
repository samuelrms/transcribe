"""Tests for the translation catalog and language switching."""

from __future__ import annotations

import pytest

from transcriber import i18n
from transcriber.errors import AudioFileError, UnsupportedFormatError


@pytest.fixture(autouse=True)
def restore_language():
    """Every test starts and ends on the default language."""
    original = i18n.get_language()
    i18n.set_language(i18n.DEFAULT_LANGUAGE)
    yield
    i18n.set_language(original)


def test_catalogs_have_exactly_the_same_keys() -> None:
    pt = set(i18n._CATALOG[i18n.PT_BR])
    en = set(i18n._CATALOG[i18n.EN])
    assert pt == en, f"only in pt: {pt - en} | only in en: {en - pt}"


def test_no_translation_is_empty() -> None:
    for language, entries in i18n._CATALOG.items():
        empty = [key for key, value in entries.items() if not value.strip()]
        assert not empty, f"{language} has empty values: {empty}"


def test_placeholders_match_between_languages() -> None:
    import string

    def placeholders(value: str) -> set[str]:
        return {name for _, name, _, _ in string.Formatter().parse(value) if name}

    for key, pt_value in i18n._CATALOG[i18n.PT_BR].items():
        en_value = i18n._CATALOG[i18n.EN][key]
        assert placeholders(pt_value) == placeholders(en_value), key


def test_default_language_is_brazilian_portuguese() -> None:
    assert i18n.get_language() == i18n.PT_BR
    assert i18n.t("action.transcribe") == "Transcrever"


def test_switching_language_changes_the_text() -> None:
    i18n.set_language(i18n.EN)
    assert i18n.t("action.transcribe") == "Transcribe"


def test_unknown_language_keeps_the_current_one() -> None:
    i18n.set_language("de")
    assert i18n.get_language() == i18n.PT_BR


def test_unknown_key_falls_back_to_the_key_itself() -> None:
    assert i18n.t("does.not.exist") == "does.not.exist"


def test_formatting_params_are_applied() -> None:
    assert "small" in i18n.t("error.out_of_memory", model="small")


def test_missing_params_do_not_raise() -> None:
    assert i18n.t("error.out_of_memory")  # no exception, template returned


def test_error_message_follows_the_current_language() -> None:
    error = AudioFileError("error.no_file")
    assert error.message == "Nenhum arquivo de áudio foi selecionado."
    i18n.set_language(i18n.EN)
    assert error.message == "No audio file was selected."


def test_error_display_joins_message_and_hint() -> None:
    error = UnsupportedFormatError(
        "error.unsupported", hint_key="error.unsupported.hint", suffix=".mp4", formats=".mp3"
    )
    display = error.display()
    assert ".mp4" in display and ".mp3" in display
    assert error.message in display
