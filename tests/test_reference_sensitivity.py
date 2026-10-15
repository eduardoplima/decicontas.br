"""Contagens por documento da sensibilidade à referência (``scripts/reference_sensitivity.py``)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from reference_sensitivity import (  # noqa: E402
    per_class_counts,
    per_doc_class_counts,
    score_against,
)

GOLD = {
    0: [(0, 10, "MULTA")],
    1: [],
    2: [(0, 4, "RECOMENDACAO"), (10, 20, "OBRIGACAO")],
}
PRED = {
    0: [(0, 9, "MULTA"), (30, 40, "MULTA")],
    2: [(0, 4, "OBRIGACAO"), (10, 20, "OBRIGACAO")],
}


def test_per_doc_counts_follow_index_order_and_label_equality() -> None:
    c = per_doc_class_counts(PRED, GOLD)
    assert c["MULTA"]["tp"].tolist() == [1, 0, 0]
    assert c["MULTA"]["fp"].tolist() == [1, 0, 0]
    # A predicted OBRIGACAO over a gold RECOMENDACAO is one FP and one FN.
    assert c["OBRIGACAO"]["tp"].tolist() == [0, 0, 1]
    assert c["OBRIGACAO"]["fp"].tolist() == [0, 0, 1]
    assert c["RECOMENDACAO"]["fn"].tolist() == [0, 0, 1]


def test_per_class_counts_is_the_sum_of_per_doc_counts() -> None:
    per_doc = per_doc_class_counts(PRED, GOLD)
    totals = per_class_counts(PRED, GOLD)
    for lab, c in per_doc.items():
        assert totals[lab] == {k: int(v.sum()) for k, v in c.items()}


def test_score_against_micro_from_counts() -> None:
    # tp = 2, fp = 2, fn = 1 -> micro F1 = 4 / 7
    assert abs(score_against(PRED, GOLD)["span_f1"] - 4 / 7) < 1e-12
