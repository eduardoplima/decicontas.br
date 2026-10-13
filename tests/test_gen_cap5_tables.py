"""Generators for the hand-maintained tables of Chapter 5 (``scripts/gen_cap5_tables.py``)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from gen_cap5_tables import (  # noqa: E402
    tabela_classe_referencias,
    tabela_erros_classe,
    tabela_fc_js,
    tabela_iou,
    tabela_prompting,
    tabela_taxonomia,
)


def test_tabela_iou_orders_by_iou_05_and_formats_with_comma():
    df = pd.DataFrame(
        {"display": ["GPT-4.1", "DeepSeek-V4-Flash"], "0.3": [0.7, 0.8], "0.5": [0.6, 0.78], "0.7": [0.5, 0.7], "exact": [0.2, 0.3]}
    )
    linhas = tabela_iou(df).splitlines()
    assert linhas[0].strip() == r"\texttt{deepseek-v4-flash} & 0,800 & 0,780 & 0,700 & 0,300 \\"
    assert linhas[1].strip().startswith(r"\texttt{gpt-4.1} & 0,700")


def test_tabela_prompting_bolds_best_technique_per_row():
    df = pd.DataFrame(
        {
            "model": ["gpt-4.1", "gpt-4.1", "gpt-4.1"],
            "technique": ["few_shot", "cot", "two_stage"],
            "span_f1_macro": [0.717, 0.718, 0.725],
        }
    )
    (linha,) = tabela_prompting(df, ["gpt-4.1"]).splitlines()
    assert linha.strip() == r"\texttt{gpt-4.1} & 0,717 & 0,718 & \textbf{0,725} \\"


def test_tabela_fc_js_emits_fc_js_and_delta_rows_with_bold_span_delta():
    overall = pd.DataFrame(
        {
            "model": ["gpt-4.1", "gpt-4.1"],
            "method": ["function_calling", "json_schema"],
            "token_f1": [0.814, 0.823],
            "span_f1": [0.742, 0.731],
            "span_precision": [0.665, 0.659],
            "span_recall": [0.839, 0.821],
        }
    )
    corpo = tabela_fc_js(overall, ["gpt-4.1"])
    assert r"& FC       & 0,814 & 0,742 & 0,665 & 0,839 \\" in corpo
    assert r"& JS       & 0,823 & 0,731 & 0,659 & 0,821 \\" in corpo
    assert r"& $\Delta$ & $-$0,009 & \textbf{+0,011} & +0,006 & +0,018 \\" in corpo


def test_tabela_taxonomia_reports_counts_and_share_of_errors():
    by_kind = pd.DataFrame(
        {
            "kind": ["match", "FP", "boundary", "duplicate", "type_error", "FN_overlap", "FN_no_pred"],
            "count": [354, 64, 46, 11, 4, 46, 41],
        }
    )
    corpo = tabela_taxonomia(by_kind)
    assert r"Acerto (verdadeiro positivo)         & 354 & --- \\" in corpo
    assert r"\multicolumn{3}{l}{\textit{Falsos positivos (125)}} \\" in corpo
    assert r"\quad Espúrio                        &  64 & 30,2\% \\" in corpo
    assert r"\textbf{Total de erros}              & \textbf{212} & \textbf{100,0\%} \\" in corpo


def test_tabela_erros_classe_sums_errors_per_label_excluding_matches():
    cross = pd.DataFrame(
        {
            "label": ["MULTA"],
            "FN_no_pred": [13], "FN_overlap": [15], "FP": [6], "boundary": [10],
            "duplicate": [8], "match": [175], "type_error": [0],
        }
    )
    (linha,) = tabela_erros_classe(cross).splitlines()
    assert linha.strip() == r"\textsc{Multa}         &  6 & 10 & 8 & 0 & 15 & 13 & 52 \\"


def test_tabela_classe_referencias_groups_by_reference_with_support_rows():
    per_class = pd.DataFrame(
        {
            "display": ["DeepSeek-V4-Flash"] * 4,
            "reference": ["anotador1"] * 4,
            "label": ["MULTA", "OBRIGACAO", "RECOMENDACAO", "RESSARCIMENTO"],
            "f1": [0.843, 0.715, 0.667, 0.744],
            "support": [203, 123, 52, 63],
        }
    )
    corpo = tabela_classe_referencias(per_class, ["DeepSeek-V4-Flash"])
    assert r"\multicolumn{6}{l}{\textit{Padrão-ouro (Anotador 1)}} \\" in corpo
    assert r"Suporte ($n$) & 203 & 123 & 52 & 63 & 441 \\" in corpo
    assert r"\texttt{deepseek-v4-flash} & \textbf{0,843} & \textbf{0,715} & \textbf{0,667} & \textbf{0,744} & \textbf{0,742} \\" in corpo
