"""Tests for ``tools.etl.text_alignment.find_span_in_text``."""

from __future__ import annotations

import pytest

from tools.etl.text_alignment import find_span_in_text


def test_exact_substring_case_sensitive(sample_texto_acordao: str) -> None:
    needle = "julgar irregulares as contas"
    match = find_span_in_text(needle, sample_texto_acordao)
    assert match == needle


def test_case_insensitive_match_returns_original_casing(
    sample_texto_acordao: str,
) -> None:
    """Descricao in different case must still match and return source casing."""
    needle = "JULGAR IRREGULARES AS CONTAS"
    match = find_span_in_text(needle, sample_texto_acordao)
    assert match == "julgar irregulares as contas"


def test_whitespace_difference_triggers_fuzzy_and_still_matches(
    sample_texto_acordao: str,
) -> None:
    """A small word-level diff must fall through to fuzzy and still match."""
    # Original text contains "julgar irregulares as contas"; drop the "es"
    # to skip both exact and case-insensitive lookups.
    needle = "julgar irregular as contas"
    match = find_span_in_text(needle, sample_texto_acordao)
    assert match is not None
    assert "irregulares" in match


def test_returns_none_when_nothing_close(sample_texto_acordao: str) -> None:
    needle = "completamente ausente do texto original xpto xpto xpto"
    assert find_span_in_text(needle, sample_texto_acordao) is None


def test_fuzzy_above_threshold_matches(sample_texto_acordao: str) -> None:
    """A single-character typo against a real span should fuzzy-match above 90."""
    # Original contains "multa cominatória diária."
    needle = "multa cominatoria diaria"  # missing accents
    match = find_span_in_text(needle, sample_texto_acordao)
    assert match is not None
    assert "cominat" in match.lower()


def test_fuzzy_below_threshold_returns_none(sample_texto_acordao: str) -> None:
    """Completely unrelated text should not fuzzy-match."""
    needle = "lorem ipsum dolor sit amet consectetur"
    assert find_span_in_text(needle, sample_texto_acordao) is None


def test_empty_inputs() -> None:
    assert find_span_in_text("", "some text") is None
    assert find_span_in_text("something", "") is None
    assert find_span_in_text("", "") is None


@pytest.mark.parametrize("descricao", ["CPF 000.000.000-00", "Acórdão nº 0123/2024"])
def test_exact_match_at_various_positions(
    descricao: str, sample_texto_acordao: str
) -> None:
    assert find_span_in_text(descricao, sample_texto_acordao) == descricao
