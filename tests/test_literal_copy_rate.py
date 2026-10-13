"""Tests for the literal-copy audit (``research.release.literal_copy_rate``).

Covers the per-string classifier (literal unique / multiple, fuzzy-only,
not found, aligner bounds equal / different in characters and in tokens),
the walk over ``pred`` and the per-model aggregation, including the
reconciliation with the block-M alignment-failure counter.
"""

from __future__ import annotations

import pandas as pd
import pytest

from research.release.literal_copy_rate import (
    COLUMNS,
    build_table,
    classify_string,
    iter_pred_strings,
    literal_first_spans,
    literal_occurrences,
    summarise,
    summarise_frame,
)

TEXT = (
    "Vistos e relatados os autos, ACORDAM os Conselheiros julgar pela irregularidade "
    "das contas, sob pena de multa diaria, e pela aplicacao de multa no valor de "
    "R$ 500,00 ao gestor responsavel, nos termos do art. 107 da LCE 464/2012, e pela "
    "recomendacao ao atual gestor para que adote providencias corretivas no prazo de "
    "90 dias."
)


class TestLiteralOccurrences:
    def test_overlapping_and_absent(self) -> None:
        assert literal_occurrences("aaa", "aa") == [0, 1]
        assert literal_occurrences("abc", "zz") == []
        assert literal_occurrences("abc", "") == []


class TestClassifyString:
    def test_literal_unique_same_bounds(self) -> None:
        s = "recomendacao ao atual gestor para que adote providencias corretivas"
        c = classify_string(TEXT, s)
        assert c["literal"] and c["literal_unique"] and not c["literal_multi"]
        assert not c["fuzzy_only"] and not c["not_found"]
        start = TEXT.index(s)
        assert c["literal_bounds"] == (start, start + len(s))
        assert c["aligner_bounds"] == c["literal_bounds"]
        assert c["aligner_same_bounds"] is True
        assert c["aligner_diff_token_bounds"] is False
        assert c["aligner_other_occurrence"] is False

    def test_literal_multiple_occurrences(self) -> None:
        text = "multa de R$ 500,00 ao gestor. Reitera-se: multa de R$ 500,00 ao gestor."
        s = "multa de R$ 500,00 ao gestor"
        c = classify_string(text, s)
        assert c["literal"] and c["literal_multi"] and not c["literal_unique"]
        assert c["n_occurrences"] == 2
        # The aligner anchors on the first window, hence the first occurrence.
        assert c["literal_bounds"] == (0, len(s))
        assert c["aligner_same_bounds"] is True

    def test_fuzzy_only(self) -> None:
        # Paraphrase close enough for partial_ratio >= 80 but not a substring.
        s = "aplicacao de multa no valor de R$ 500,00 ao gestor responsável"
        assert s not in TEXT
        c = classify_string(TEXT, s)
        assert not c["literal"]
        assert c["fuzzy_only"] is True and c["not_found"] is False
        assert c["aligner_bounds"] is not None
        assert c["literal_bounds"] is None
        assert c["aligner_same_bounds"] is None

    def test_not_found(self) -> None:
        c = classify_string(TEXT, "zzz qqq texto inexistente no documento")
        assert not c["literal"] and not c["fuzzy_only"]
        assert c["not_found"] is True
        assert c["aligner_bounds"] is None

    def test_aligner_diff_bounds_changes_tokens(self) -> None:
        # Literal, but the first word ("multa") also occurs earlier in the
        # window, so the aligner anchors the span on that earlier "multa".
        s = "multa no valor de R$ 500,00 ao gestor responsavel"
        c = classify_string(TEXT, s)
        assert c["literal"] and c["literal_unique"]
        assert c["aligner_same_bounds"] is False
        assert c["aligner_other_occurrence"] is False
        assert c["aligner_bounds"][0] == TEXT.index("multa diaria")
        assert c["aligner_bounds"][0] < c["literal_bounds"][0]
        assert c["aligner_diff_token_bounds"] is True

    def test_aligner_diff_bounds_same_tokens(self) -> None:
        # The first word "a" is found inside the preceding token "ala": the
        # character bounds differ but every covered whitespace token is the
        # same, so the scoring unit does not move.
        text = "ala multa de R$ 500"
        s = "a multa de R$ 500"
        c = classify_string(text, s)
        assert c["literal_bounds"] == (2, 19)
        assert c["aligner_bounds"] == (0, 17)
        assert c["aligner_same_bounds"] is False
        assert c["aligner_diff_token_bounds"] is False


class TestIterPredStrings:
    def test_walk_skips_empty_and_malformed(self) -> None:
        pred = {
            "multas": [{"descricao_multa": "multa A"}, {"descricao_multa": ""}, "bogus"],
            "obrigacoes": [{"descricao_obrigacao": None}],
            "recomendacoes": None,
            "ressarcimentos": [{"descricao_ressarcimento": "ressarcir B"}],
        }
        assert list(iter_pred_strings(pred)) == ["multa A", "ressarcir B"]

    def test_non_dict_pred_yields_nothing(self) -> None:
        assert list(iter_pred_strings(None)) == []
        assert list(iter_pred_strings("{'multas': []}")) == []


def _frame() -> pd.DataFrame:
    """Two documents, four strings: literal (same bounds), literal (shifted
    bounds), fuzzy-only and not found."""
    return pd.DataFrame(
        [
            {
                "text": TEXT,
                "pred": {
                    "multas": [
                        {"descricao_multa": "multa no valor de R$ 500,00 ao gestor responsavel"},
                        {"descricao_multa": "zzz qqq texto inexistente no documento"},
                    ],
                    "recomendacoes": [
                        {
                            "descricao_recomendacao": (
                                "recomendacao ao atual gestor para que adote providencias"
                            )
                        }
                    ],
                },
            },
            {
                "text": TEXT,
                "pred": {
                    "multas": [
                        {
                            "descricao_multa": (
                                "aplicacao de multa no valor de R$ 500,00 ao gestor responsável"
                            )
                        }
                    ],
                },
            },
        ]
    )


class TestSummarise:
    def test_counts_and_percentages(self) -> None:
        rows = [
            classify_string(TEXT, "multa no valor de R$ 500,00 ao gestor responsavel"),
            classify_string(TEXT, "recomendacao ao atual gestor para que adote providencias"),
            classify_string(TEXT, "aplicacao de multa no valor de R$ 500,00 ao gestor responsável"),
            classify_string(TEXT, "zzz qqq texto inexistente no documento"),
        ]
        s = summarise("m", rows)
        assert list(s) == COLUMNS
        assert s["n_strings"] == 4
        assert (s["literal"], s["fuzzy_only"], s["not_found"]) == (2, 1, 1)
        assert s["literal_pct"] == 50.0 and s["not_found_pct"] == 25.0
        assert s["literal_unique"] == 2 and s["literal_unique_pct"] == 50.0
        # One of the two literal strings gets shifted by the aligner.
        assert s["aligner_same_bounds"] == 1 and s["aligner_same_bounds_pct"] == 50.0
        assert s["aligner_diff_bounds"] == 1 and s["aligner_diff_token_bounds"] == 1

    def test_empty_model(self) -> None:
        s = summarise("m", [])
        assert s["n_strings"] == 0 and s["literal_pct"] == 0.0

    def test_summarise_frame_reconciles_with_block_m(self) -> None:
        s = summarise_frame("m", _frame())
        assert s["n_strings"] == 4 and s["not_found"] == 1

    def test_summarise_frame_raises_when_walks_diverge(self, monkeypatch) -> None:
        import research.release.literal_copy_rate as mod

        monkeypatch.setattr(mod, "count_alignment_failures", lambda row: (99, 99, 0))
        with pytest.raises(RuntimeError):
            summarise_frame("m", _frame())


class TestBuildTable:
    def test_ordered_by_not_found_rate_then_input_order(self) -> None:
        clean = pd.DataFrame(
            [{"text": TEXT, "pred": {"multas": [{"descricao_multa": "multa diaria"}]}}]
        )
        table = build_table({"clean_a": clean, "noisy": _frame(), "clean_b": clean})
        assert list(table.columns) == COLUMNS
        assert table["model"].tolist() == ["noisy", "clean_a", "clean_b"]
        assert table["n_strings"].tolist() == [4, 1, 1]


class TestLiteralFirstSpans:
    def test_literal_strings_land_on_their_occurrence(self) -> None:
        row = _frame().iloc[0]
        spans = literal_first_spans(row)
        # The unlocatable string is dropped as in production; the two literal
        # ones sit exactly where they occur; labels follow DICT_LABELS.
        assert [sp["labels"][0] for sp in spans] == ["MULTA", "RECOMENDACAO"]
        for sp in spans:
            assert TEXT[sp["start"] : sp["end"]] == sp["text"]

    def test_non_literal_goes_through_aligner(self) -> None:
        row = _frame().iloc[1]
        spans = literal_first_spans(row)
        assert len(spans) == 1
        assert TEXT[spans[0]["start"] : spans[0]["end"]] != spans[0]["text"]
