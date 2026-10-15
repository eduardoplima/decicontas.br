"""Deslocamentos de fronteira em caracteres (``scripts/boundary_offsets.py``)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from boundary_offsets import describe_pair, exact_tp, to_tokens  # noqa: E402

from research.dataset_io import token_offsets  # noqa: E402

TEXT = "APLICAÇÃO DE multa no valor de R$ 500,00 ao gestor;"


def test_exact_tp_is_one_to_one() -> None:
    gold = [(0, 5, "MULTA"), (0, 5, "MULTA")]
    assert exact_tp([(0, 5, "MULTA")], gold) == 1
    assert exact_tp([(0, 5, "MULTA")] * 3, gold) == 2
    assert exact_tp([(0, 5, "OBRIGACAO")], gold) == 0


def test_describe_pair_reports_prefix_and_omitted_suffix() -> None:
    gold = (TEXT.index("multa"), len(TEXT), "MULTA")
    pred = (0, len(TEXT) - 1, "MULTA")
    row = describe_pair(TEXT, pred, gold)
    assert row["start_delta"] == -len("APLICAÇÃO DE ")
    assert row["start_prefix"].strip() == "APLICAÇÃO DE"
    assert row["end_delta"] == -1
    assert row["end_omitted"] == ";"


def test_trailing_punctuation_does_not_change_the_token_span() -> None:
    offsets = token_offsets(TEXT)
    start = TEXT.index("multa")
    with_semicolon, without = to_tokens(
        [(start, len(TEXT), "MULTA"), (start, len(TEXT) - 1, "MULTA")], offsets
    )
    assert with_semicolon == without
