"""Regenerate every figure produced by ``ner_results.ipynb`` and
``ner_experiments.ipynb`` against the cleanlab-corrected dataset.

Produces 12 PNGs under ``figures/`` with the ``_corrected`` suffix:

ner_results.ipynb (4):
  overall_f1_comparison_corrected.png
  entity_f1_heatmap_corrected.png
  strategy_comparison_corrected.png
  precision_recall_scatter_corrected.png

ner_experiments.ipynb (8):
  exp1_overall_f1_corrected.png
  exp1_entity_heatmap_corrected.png
  exp1_precision_recall_corrected.png
  exp2_method_comparison_corrected.png
  exp2_delta_per_entity_corrected.png
  exp3_technique_heatmap_corrected.png
  exp3_strategy_dots_corrected.png
  exp3_best_per_technique_entity_corrected.png

All data comes from CSVs already produced by ``chapter5_numbers``
(``dataset/results/chapter5_corrected/``) — no metric recomputation.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.patches import Patch


REPO_ROOT = Path(__file__).resolve().parents[2]
NUMS = REPO_ROOT / "dataset" / "results" / "chapter5_corrected"
FIG_DIR = REPO_ROOT / "figures"
SUFFIX = ""  # overwrite originals; corrected dataset is now canonical
ENTITY_LABELS = ["MULTA", "OBRIGACAO", "RECOMENDACAO", "RESSARCIMENTO"]

logger = logging.getLogger("research.release.regenerate_figures")


def _save(fig: plt.Figure, name: str) -> Path:
    out = FIG_DIR / f"{name}{SUFFIX}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("wrote %s", out)
    return out


def _per_entity_pivot(per: pd.DataFrame, key: list[str], label_col: str = "label") -> pd.DataFrame:
    """Pivot long per-entity to wide (rows = key, cols = entity, values = f1)."""
    return per.pivot_table(index=key, columns=label_col, values="f1")[ENTITY_LABELS]


# ----- ner_results.ipynb (4 figures) --------------------------------------


def _ner_results_dataframe() -> pd.DataFrame:
    """Recreate the df_metrics shape: model, strategy, paradigm, token_*, span_*, f1_<LABEL>."""
    main = pd.read_csv(NUMS / "C_main_results.csv")
    per = pd.read_csv(NUMS / "D_per_entity.csv")
    f1_pivot = per.pivot_table(index="model", columns="label", values="f1")[
        ENTITY_LABELS
    ]
    f1_pivot.columns = [f"f1_{c}" for c in f1_pivot.columns]
    df = main.set_index("model").join(f1_pivot)
    df["strategy"] = df.index.map(
        lambda x: x.rsplit("__", 1)[1] if "__" in x else "few_shot"
    )
    df["paradigm"] = df["strategy"].apply(
        lambda s: "supervised" if s == "supervised" else "few-shot"
    )
    df["model_name"] = df.index.map(
        lambda x: x.rsplit("__", 1)[0] if "__" in x else x
    )
    return df.sort_values("span_f1", ascending=False)


def fig_overall_f1_comparison(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(
        1, 2, figsize=(16, max(6, len(df) * 0.4)), sharey=True
    )
    order = df.index.tolist()
    axes[0].barh(order, df["token_f1"], color="steelblue")
    axes[0].set_xlabel("F1 por Token")
    axes[0].set_title("F1 em Nível de Token")
    axes[0].set_xlim(0, 1)
    for i, v in enumerate(df["token_f1"]):
        axes[0].text(v + 0.01, i, f"{v:.3f}", va="center", fontsize=9)
    axes[1].barh(order, df["span_f1"], color="darkorange")
    axes[1].set_xlabel("F1 por Span")
    axes[1].set_title("F1 em Nível de Span (IoU ≥ 0.5)")
    axes[1].set_xlim(0, 1)
    for i, v in enumerate(df["span_f1"]):
        axes[1].text(v + 0.01, i, f"{v:.3f}", va="center", fontsize=9)
    plt.tight_layout()
    _save(fig, "overall_f1_comparison")


def fig_entity_f1_heatmap(df: pd.DataFrame) -> None:
    f1_cols = [f"f1_{l}" for l in ENTITY_LABELS]
    df_entity = df[f1_cols].copy()
    df_entity.columns = [c.replace("f1_", "") for c in df_entity.columns]
    fig, ax = plt.subplots(figsize=(10, max(5, len(df_entity) * 0.45)))
    sns.heatmap(
        df_entity, annot=True, fmt=".3f", cmap="YlOrRd", ax=ax, linewidths=0.5,
        vmin=0, vmax=1,
    )
    ax.set_title("F1 de Span por Tipo de Entidade")
    ax.set_ylabel("")
    plt.tight_layout()
    _save(fig, "entity_f1_heatmap")


def fig_strategy_comparison(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    strategies = sorted(df["strategy"].unique())
    for i, strat in enumerate(strategies):
        subset = df[df["strategy"] == strat]
        ax.scatter([i] * len(subset), subset["span_f1"], s=80, zorder=5)
        ax.hlines(
            subset["span_f1"].mean(), i - 0.2, i + 0.2, colors="black", linewidth=2
        )
    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels(strategies, rotation=30, ha="right")
    ax.set_ylabel("F1 de Span")
    ax.set_title("F1 de Span por Estratégia (cada ponto = um modelo)")
    plt.tight_layout()
    _save(fig, "strategy_comparison")


def fig_precision_recall_scatter(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(
        df["span_precision"], df["span_recall"], s=100, c=df["span_f1"],
        cmap="viridis", edgecolors="k", vmin=0, vmax=1,
    )
    for idx, row in df.iterrows():
        label = idx.replace("__", "\n")
        ax.annotate(
            label, (row["span_precision"], row["span_recall"]),
            fontsize=7, ha="left", va="bottom", xytext=(4, 4),
            textcoords="offset points",
        )
    ax.plot([0, 1], [0, 1], "k--", alpha=0.3)
    ax.set_xlabel("Precisão (Span)")
    ax.set_ylabel("Revocação (Span)")
    ax.set_title("Precisão vs Revocação (cor = F1)")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    plt.colorbar(ax.collections[0], ax=ax, label="F1 de Span")
    plt.tight_layout()
    _save(fig, "precision_recall_scatter")


# ----- ner_experiments.ipynb — Experiment 1 (3 figures) -------------------


def _exp1_dataframe() -> pd.DataFrame:
    """Same shape as df_fewshot: includes paradigm + per-entity F1 columns."""
    df = _ner_results_dataframe().reset_index().rename(columns={"model": "experiment"})
    df["model"] = df["model_name"]
    return df


def fig_exp1_overall_f1(df: pd.DataFrame) -> None:
    colors = df["paradigm"].map({"supervised": "#2ca02c", "few-shot": "steelblue"}).values
    fig, axes = plt.subplots(1, 2, figsize=(16, max(6, len(df) * 0.45)), sharey=True)
    axes[0].barh(df["model"], df["token_f1"], color=colors)
    axes[0].set_xlabel("F1 por Token")
    axes[0].set_title("F1 em Nível de Token")
    axes[0].set_xlim(0, 1)
    for i, v in enumerate(df["token_f1"]):
        axes[0].text(v + 0.01, i, f"{v:.3f}", va="center", fontsize=9)
    axes[1].barh(df["model"], df["span_f1"], color=colors)
    axes[1].set_xlabel("F1 por Span")
    axes[1].set_title("F1 em Nível de Span (IoU ≥ 0.5)")
    axes[1].set_xlim(0, 1)
    for i, v in enumerate(df["span_f1"]):
        axes[1].text(v + 0.01, i, f"{v:.3f}", va="center", fontsize=9)
    axes[1].legend(handles=[
        Patch(color="steelblue", label="LLM few-shot"),
        Patch(color="#2ca02c", label="Supervisionado"),
    ], loc="lower right")
    plt.tight_layout()
    _save(fig, "exp1_overall_f1")


def fig_exp1_entity_heatmap(df: pd.DataFrame) -> None:
    f1_cols = [f"f1_{l}" for l in ENTITY_LABELS]
    df_entity = df[f1_cols].copy()
    df_entity.columns = [c.replace("f1_", "") for c in df_entity.columns]
    df_entity.index = df["model"]
    fig, ax = plt.subplots(figsize=(10, max(5, len(df_entity) * 0.5)))
    sns.heatmap(
        df_entity, annot=True, fmt=".3f", cmap="YlOrRd", ax=ax, linewidths=0.5,
        vmin=0, vmax=1,
    )
    ax.set_title("F1 de Span por Tipo de Entidade (Experimento 1)")
    ax.set_ylabel("")
    plt.tight_layout()
    _save(fig, "exp1_entity_heatmap")


def fig_exp1_precision_recall(df: pd.DataFrame) -> None:
    paradigm_colors = df["paradigm"].map(
        {"supervised": "#2ca02c", "few-shot": "steelblue"}
    )
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(
        df["span_precision"], df["span_recall"], s=120, c=paradigm_colors,
        edgecolors="k", zorder=5,
    )
    for _, row in df.iterrows():
        ax.annotate(
            row["model"], (row["span_precision"], row["span_recall"]),
            fontsize=7, ha="left", va="bottom", xytext=(4, 4),
            textcoords="offset points",
        )
    ax.plot([0, 1], [0, 1], "k--", alpha=0.3)
    ax.set_xlabel("Precisão (Span)")
    ax.set_ylabel("Revocação (Span)")
    ax.set_title("Precisão vs Revocação — Few-Shot e Supervisionado")
    ax.set_xlim(0.3, 0.95)
    ax.set_ylim(0.4, 1.0)
    ax.legend(handles=[
        Patch(color="steelblue", label="LLM few-shot"),
        Patch(color="#2ca02c", label="Supervisionado"),
    ])
    plt.tight_layout()
    _save(fig, "exp1_precision_recall")


# ----- ner_experiments.ipynb — Experiment 2 (2 figures) -------------------


def _exp2_dataframe() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (overall, per_entity) DataFrames."""
    overall = pd.read_csv(NUMS / "F_fc_vs_json_overall.csv")
    per_entity = pd.read_csv(NUMS / "G_fc_vs_json_per_entity.csv")
    return overall, per_entity


def fig_exp2_method_comparison(overall: pd.DataFrame) -> None:
    models = sorted(overall["model"].unique())
    x = np.arange(len(models))
    width = 0.35
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, metric, ylabel, title in [
        (axes[0], "token_f1", "F1 por Token", "F1 em Nível de Token"),
        (axes[1], "span_f1", "F1 por Span", "F1 em Nível de Span"),
    ]:
        fc_vals = [
            overall.loc[
                (overall["model"] == m) & (overall["method"] == "function_calling"),
                metric,
            ].iloc[0] if not overall[
                (overall["model"] == m) & (overall["method"] == "function_calling")
            ].empty else 0
            for m in models
        ]
        js_vals = [
            overall.loc[
                (overall["model"] == m) & (overall["method"] == "json_schema"), metric
            ].iloc[0] if not overall[
                (overall["model"] == m) & (overall["method"] == "json_schema")
            ].empty else 0
            for m in models
        ]
        bars1 = ax.bar(x - width / 2, fc_vals, width, label="function_calling", color="steelblue")
        bars2 = ax.bar(x + width / 2, js_vals, width, label="json_schema", color="darkorange")
        ax.set_xticks(x)
        ax.set_xticklabels(models, rotation=30, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend()
        ax.set_ylim(0, 1)
        for bars in [bars1, bars2]:
            for bar in bars:
                if bar.get_height() > 0:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.01,
                        f"{bar.get_height():.3f}",
                        ha="center", va="bottom", fontsize=8,
                    )
    plt.tight_layout()
    _save(fig, "exp2_method_comparison")


def fig_exp2_delta_per_entity(per_entity: pd.DataFrame) -> None:
    delta_rows = []
    for model in sorted(per_entity["model"].unique()):
        row = {"model": model}
        for label in ENTITY_LABELS:
            fc = per_entity[
                (per_entity["model"] == model)
                & (per_entity["method"] == "function_calling")
                & (per_entity["label"] == label)
            ]["f1"]
            js = per_entity[
                (per_entity["model"] == model)
                & (per_entity["method"] == "json_schema")
                & (per_entity["label"] == label)
            ]["f1"]
            fc_v = fc.iloc[0] if not fc.empty else 0.0
            js_v = js.iloc[0] if not js.empty else 0.0
            row[f"delta_{label}"] = fc_v - js_v
        delta_rows.append(row)
    df_delta = pd.DataFrame(delta_rows).set_index("model")
    fig, ax = plt.subplots(figsize=(10, 5))
    df_delta.plot(kind="bar", ax=ax, colormap="RdYlGn")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Delta de F1 (function_calling − json_schema)")
    ax.set_title("Impacto do Método de Structured Output por Entidade")
    ax.legend(title="Entidade", bbox_to_anchor=(1.02, 1))
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    _save(fig, "exp2_delta_per_entity")


# ----- ner_experiments.ipynb — Experiment 3 (3 figures) -------------------


def _exp3_dataframes() -> tuple[pd.DataFrame, pd.DataFrame]:
    overall = pd.read_csv(NUMS / "H_prompting_overall.csv")
    per = pd.read_csv(NUMS / "H_prompting_per_entity.csv")
    return overall, per


def fig_exp3_technique_heatmap(overall: pd.DataFrame) -> None:
    pivot = overall.pivot_table(index="model", columns="technique", values="span_f1")
    pivot = pivot.sort_values(pivot.columns.tolist(), ascending=False)
    fig, ax = plt.subplots(figsize=(12, max(5, len(pivot) * 0.6)))
    sns.heatmap(
        pivot, annot=True, fmt=".3f", cmap="YlGn", ax=ax, linewidths=0.5,
        vmin=0.3, vmax=0.85,
    )
    ax.set_title("F1 de Span — Modelo × Técnica")
    ax.set_ylabel("")
    plt.tight_layout()
    _save(fig, "exp3_technique_heatmap")


def fig_exp3_strategy_dots(overall: pd.DataFrame) -> None:
    techniques = sorted(overall["technique"].unique())
    fig, ax = plt.subplots(figsize=(10, 5))
    rng = np.random.default_rng(42)
    for i, tech in enumerate(techniques):
        subset = overall[overall["technique"] == tech]
        jitter = rng.uniform(-0.15, 0.15, len(subset))
        ax.scatter(
            [i] * len(subset) + jitter, subset["span_f1"], s=80, zorder=5, alpha=0.7
        )
        ax.hlines(
            subset["span_f1"].mean(), i - 0.25, i + 0.25, colors="black", linewidth=2.5
        )
        for _, row in subset.iterrows():
            ax.annotate(
                row["model"], (i + 0.2, row["span_f1"]), fontsize=6, alpha=0.7
            )
    ax.set_xticks(range(len(techniques)))
    ax.set_xticklabels(techniques, rotation=20, ha="right")
    ax.set_ylabel("F1 de Span")
    ax.set_title("F1 de Span por Técnica (cada ponto = um modelo, barra = média)")
    plt.tight_layout()
    _save(fig, "exp3_strategy_dots")


def fig_exp3_best_per_technique_entity(
    overall: pd.DataFrame, per_entity: pd.DataFrame
) -> None:
    best_idx = overall.groupby("technique")["span_f1"].idxmax()
    best_per_tech = overall.loc[best_idx][["model", "technique"]]
    rows = []
    for _, br in best_per_tech.iterrows():
        row = {"technique": br["technique"]}
        for label in ENTITY_LABELS:
            sel = per_entity[
                (per_entity["model"] == br["model"])
                & (per_entity["technique"] == br["technique"])
                & (per_entity["label"] == label)
            ]["f1"]
            row[label] = sel.iloc[0] if not sel.empty else 0.0
        rows.append(row)
    df_best_entity = pd.DataFrame(rows).set_index("technique")
    fig, ax = plt.subplots(figsize=(10, 4))
    df_best_entity.plot(kind="bar", ax=ax, colormap="Set2")
    ax.set_ylabel("F1 de Span")
    ax.set_title("Melhor Modelo por Técnica — F1 por Entidade")
    ax.legend(title="Entidade", bbox_to_anchor=(1.02, 1))
    ax.set_ylim(0, 1)
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    _save(fig, "exp3_best_per_technique_entity")


# ----- Orchestration ------------------------------------------------------


def run() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({"font.size": 10})

    df_results = _ner_results_dataframe()
    fig_overall_f1_comparison(df_results)
    fig_entity_f1_heatmap(df_results)
    fig_strategy_comparison(df_results)
    fig_precision_recall_scatter(df_results)

    df_exp1 = _exp1_dataframe()
    fig_exp1_overall_f1(df_exp1)
    fig_exp1_entity_heatmap(df_exp1)
    fig_exp1_precision_recall(df_exp1)

    fcjs_overall, fcjs_per = _exp2_dataframe()
    fig_exp2_method_comparison(fcjs_overall)
    fig_exp2_delta_per_entity(fcjs_per)

    pe_overall, pe_per = _exp3_dataframes()
    fig_exp3_technique_heatmap(pe_overall)
    fig_exp3_strategy_dots(pe_overall)
    fig_exp3_best_per_technique_entity(pe_overall, pe_per)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run()


if __name__ == "__main__":
    main()
