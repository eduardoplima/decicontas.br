"""Exact-first string→offset alignment of LLM predictions (advisor review, D4-b).

The legacy aligner located every predicted string by fuzzy search and anchored
the span at the first occurrence of the string's first word inside the winning
window, which displaced even verbatim copies. The corrected aligner tries a
literal match first and only falls back to the fuzzy search when the string is
not a substring of the document.
"""

from __future__ import annotations

from research.ner_metrics import (
    convert_pred_to_golden_format,
    count_alignment_failures,
    locate_span,
)


def _row(text: str, s: str) -> dict:
    return {"text": text, "pred": {"multas": [{"descricao_multa": s}]}}


def _span(text: str, s: str) -> tuple[int, int]:
    start = text.index(s)
    return start, start + len(s)


def test_literal_string_is_placed_at_its_occurrence_even_when_first_word_appears_earlier():
    text = ("Aplicar multa de R$ 100,00 ao gestor por atraso. " * 3) + (
        "Aplicar multa ao Sr. Fulano no valor de R$ 50,00 por dia de atraso. Fim."
    )
    s = "multa ao Sr. Fulano no valor de R$ 50,00 por dia de atraso"
    (located,) = convert_pred_to_golden_format(_row(text, s))
    assert (located["start"], located["end"]) == _span(text, s)


def test_literal_string_longer_than_the_window_is_located_exactly():
    filler = "lorem ipsum dolor sit amet consectetur. " * 25 + "abc "  # 1004 chars: off the 100-grid
    s = "determinar ao gestor " + "que adote as providências cabíveis " * 20 + "no prazo de trinta dias"
    assert len(s) > 500
    text = filler + s + " " + filler
    assert text.index(s) % 100 != 0
    (located,) = convert_pred_to_golden_format(_row(text, s))
    assert (located["start"], located["end"]) == _span(text, s)


def test_repeated_literal_string_picks_the_occurrence_nearest_the_fuzzy_anchor():
    # First occurrence straddles every 500-char window (starts at 60, length ~460),
    # so no window scores 100 on it; the second occurrence sits whole inside the
    # window that starts at 1000, preceded by an earlier "multa" that displaces
    # the legacy anchor to 1000. The nearest literal occurrence to that anchor is
    # the second one.
    s = "multa ao Sr. Fulano no valor de R$ 50,00 " + "por dia de atraso no cumprimento " * 13
    s = s.strip()
    assert 445 <= len(s) <= 480  # straddles the window that starts at 0 (60 + len > 500)
    head = "x" * 60
    gap = "y" * (1000 - 60 - len(s) - 2)
    text = head + s + ". " + gap + "multa anterior " + s + " fim."
    second = text.index(s, 61)
    assert text[1000:1015] == "multa anterior " and second == 1015
    assert locate_span(text, s, exact_first=False) == (1000, 1000 + len(s))  # legacy: displaced anchor
    assert locate_span(text, s) == (second, second + len(s))


def test_non_literal_string_still_falls_back_to_fuzzy_alignment():
    text = "O Tribunal decide aplicar multa ao gestor no valor de R$ 1.000,00 (mil reais) pelo atraso."
    s = "multa ao gestor no valor de R$ 1000,00 (mil reais)"  # paraphrase: missing thousands dot
    (located,) = convert_pred_to_golden_format(_row(text, s))
    assert located["start"] == text.index("multa ao gestor")


def test_unlocatable_string_is_dropped_and_counted_as_failure():
    text = "Texto completamente diferente sem relação alguma com a predição do modelo."
    s = "ressarcimento ao erário da quantia de R$ 9.999,99 pelo responsável"
    assert convert_pred_to_golden_format(_row(text, s)) == []
    assert count_alignment_failures(_row(text, s)) == (1, 0, 1)


def test_exact_first_can_be_disabled_to_reproduce_the_legacy_aligner():
    text = "Aplicar multa de R$ 100,00 ao gestor. Aplicar multa ao Sr. Fulano no valor de R$ 50,00."
    s = "multa ao Sr. Fulano no valor de R$ 50,00"
    (legacy,) = convert_pred_to_golden_format(_row(text, s), exact_first=False)
    assert legacy["start"] == text.index("multa")  # the artefact: anchored at the first "multa"
    assert locate_span(text, s, exact_first=False) == (text.index("multa"), text.index("multa") + len(s))
