"""Tests for the metric utilities added for the advisor review (Chapter 5).

Covers: macro-F1 surfacing, the multi-IoU span sweep (incl. exact match),
the string→offset alignment failure counter, the Holm/Bonferroni correction
and the informative-subset filter.
"""

from __future__ import annotations

import pandas as pd

from research.ner_metrics import (
    count_alignment_failures,
    flatten_metrics,
    span_metrics_multi_iou,
)
from research.release.chapter5_numbers import _holm_bonferroni, _keep_informative_only


def _df_one_doc() -> pd.DataFrame:
    """One document: a MULTA pred overlapping gold at IoU 0.9, a stray MULTA
    false positive, and an unmatched OBRIGACAO gold (false negative)."""
    return pd.DataFrame(
        [
            {
                "text": "x" * 100,
                "golden": [
                    {"start": 0, "end": 20, "labels": ["MULTA"]},
                    {"start": 30, "end": 40, "labels": ["OBRIGACAO"]},
                ],
                "pred_as_golden": [
                    {"start": 0, "end": 18, "labels": ["MULTA"]},
                    {"start": 50, "end": 60, "labels": ["MULTA"]},
                ],
            }
        ]
    )


class TestMacroF1:
    def test_flatten_exposes_span_macro(self) -> None:
        raw = {
            "token_flat": {"precision": 0.0, "recall": 0.0, "f1": 0.0},
            "iou_agg": {"precision": 0.5, "recall": 0.5, "f1": 0.5},
            "iou_per_label": {
                "MULTA": {"precision": 1.0, "recall": 1.0, "f1": 1.0},
                "OBRIGACAO": {"precision": 0.0, "recall": 0.0, "f1": 0.0},
            },
        }
        flat = flatten_metrics(raw)
        # macro averages over the FOUR evaluation labels (absent ones count 0).
        assert flat["span_f1_macro"] == 1.0 / 4
        # token macro omitted when no per-label token scores are present.
        assert "token_f1_macro" not in flat

    def test_token_macro_when_per_label_present(self) -> None:
        raw = {
            "token_flat": {
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
                "per_label": {
                    "MULTA": {"f1": 0.8},
                    "OBRIGACAO": {"f1": 0.4},
                },
            },
            "iou_agg": {"precision": 0.0, "recall": 0.0, "f1": 0.0},
            "iou_per_label": {},
        }
        flat = flatten_metrics(raw)
        assert flat["token_f1_macro"] == (0.8 + 0.4) / 4


class TestMultiIoU:
    def test_thresholds_and_exact(self) -> None:
        res = span_metrics_multi_iou(_df_one_doc(), [0.3, 0.5, 0.7, 1.0])
        # IoU(0..18, 0..20) = 18/20 = 0.9 → matches up to 0.7, fails exact.
        for t in (0.3, 0.5, 0.7):
            assert res[t]["span_f1"] == 0.5  # TP=1, FP=1, FN=1
        assert res[1.0]["span_f1"] == 0.0

    def test_macro_present_in_each_threshold(self) -> None:
        res = span_metrics_multi_iou(_df_one_doc(), [0.5])
        # MULTA f1 = 2/3 (P=0.5, R=1.0); other three labels 0 → macro = (2/3)/4.
        assert abs(res[0.5]["span_f1_macro"] - (2 / 3) / 4) < 1e-9


class TestAlignmentFailures:
    def test_counts_total_aligned_failed(self) -> None:
        row = {
            "text": "multa de R$ 500 aplicada ao gestor por irregularidade grave",
            "pred": {
                "multas": [
                    {"descricao_multa": "multa de R$ 500 aplicada ao gestor"},
                    {"descricao_multa": "zzz qqq texto inexistente no documento"},
                ],
                "obrigacoes": [],
            },
        }
        total, aligned, failed = count_alignment_failures(row)
        assert total == 2
        assert aligned == 1
        assert failed == 1

    def test_no_pred_dict_returns_zeros(self) -> None:
        assert count_alignment_failures({"text": "abc", "pred": None}) == (0, 0, 0)


class TestHolmBonferroni:
    def test_known_values(self) -> None:
        holm, bonf = _holm_bonferroni([0.01, 0.04, 0.03, 0.005])
        # Bonferroni multiplies each by m=4 (capped at 1).
        assert bonf == [0.04, 0.16, 0.12, 0.02]
        # Holm is monotone non-decreasing in p-rank.
        order = sorted(range(4), key=lambda i: [0.01, 0.04, 0.03, 0.005][i])
        adj_sorted = [holm[i] for i in order]
        assert adj_sorted == sorted(adj_sorted)
        assert all(h <= b + 1e-12 for h, b in zip(holm, bonf))

    def test_empty(self) -> None:
        assert _holm_bonferroni([]) == ([], [])


class TestInformativeFilter:
    def test_drops_empty_gold_rows(self) -> None:
        df = pd.DataFrame(
            [
                {"golden": [{"start": 0, "end": 1, "labels": ["MULTA"]}], "pred_as_golden": []},
                {"golden": [], "pred_as_golden": [{"start": 0, "end": 1, "labels": ["MULTA"]}]},
            ]
        )
        out = _keep_informative_only(df)
        assert len(out) == 1
        assert out.iloc[0]["golden"]
