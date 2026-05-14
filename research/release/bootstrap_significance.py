"""Document-level bootstrap for span F1 — port of ``notebooks/statistical_significance.ipynb``.

Computes individual 95% CIs and pairwise comparisons (10,000 resamples by
default) for every model in :data:`MODELS`, reading prediction JSONs from
``--input-dir`` and writing CSV + LaTeX outputs to ``--output-dir``.

The notebook stays as the authoritative narrative version; this script
exists so the same analysis can be re-run on the cleanlab-corrected
result bundle (``dataset/results/output_corrected/``) and against the
post-retrain supervised baseline JSONs without manual notebook
execution.

Behaviour mirrors the notebook exactly:
  * Both LLM and BIO layouts auto-detected.
  * Few-shot leak positions (``FEWSHOT_RESULT_POSITIONS``) dropped from
    every model before counting.
  * Non-bipartite IoU>=0.5 matching for ``compute_doc_level_counts``.
  * Same seed (42) and N=10000.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from rapidfuzz import fuzz

from research.fewshot import FEWSHOT_RESULT_POSITIONS
from research.ner_metrics import bipartite_greedy_match


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = REPO_ROOT / "dataset" / "results" / "output_corrected"
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT / "dataset" / "experiments" / "significance_outputs_corrected"
)
DEFAULT_FIG_DIR = REPO_ROOT / "figures"

N_BOOTSTRAP = 10_000
SEED = 42
IOU_THRESHOLD = 0.5
ALPHA = 0.05


logger = logging.getLogger("research.release.bootstrap_significance")


MODELS = [
    "gpt-4-turbo",
    "gpt-5.4-mini_few_shot",
    "gpt-4o",
    "gpt-5.4-nano_few_shot",
    "rufimelo_Legal-BERTimbau-base__supervised",
    "gpt-41-mini",
    "neuralmind_bert-base-portuguese-cased__supervised",
    "gpt-35",
    "gpt-41",
    "neuralmind_bert-large-portuguese-cased__supervised",
    "gemini-2.5-flash_few_shot",
    "deepseek-v3_few_shot",
    "bilstm-crf__supervised",
    "gpt-41-nano",
]

DISPLAY_NAMES = {
    "gpt-4-turbo": "GPT-4 Turbo",
    "gpt-5.4-mini_few_shot": "GPT-5.4-mini",
    "gpt-4o": "GPT-4o",
    "gpt-5.4-nano_few_shot": "GPT-5.4-nano",
    "rufimelo_Legal-BERTimbau-base__supervised": "Legal-BERTimbau-base",
    "gpt-41-mini": "GPT-4.1-mini",
    "neuralmind_bert-base-portuguese-cased__supervised": "BERTimbau-base",
    "gpt-35": "GPT-3.5",
    "gpt-41": "GPT-4.1",
    "neuralmind_bert-large-portuguese-cased__supervised": "BERTimbau-large",
    "gemini-2.5-flash_few_shot": "Gemini-2.5-flash",
    "deepseek-v3_few_shot": "DeepSeek-V3",
    "bilstm-crf__supervised": "BiLSTM-CRF",
    "gpt-41-nano": "GPT-4.1-nano",
}

HIGHLIGHTED_PAIRS = [
    ("gpt-4-turbo", "gpt-5.4-mini_few_shot"),
    ("gpt-4-turbo", "gpt-4o"),
    ("gpt-5.4-mini_few_shot", "gpt-4o"),
    ("gpt-4-turbo", "rufimelo_Legal-BERTimbau-base__supervised"),
    ("gpt-4-turbo", "neuralmind_bert-base-portuguese-cased__supervised"),
    ("gpt-5.4-mini_few_shot", "rufimelo_Legal-BERTimbau-base__supervised"),
    ("gpt-4-turbo", "gpt-41-nano"),
    ("gpt-4-turbo", "deepseek-v3_few_shot"),
    ("gpt-4-turbo", "gemini-2.5-flash_few_shot"),
    # Chapter-5 narrative additions
    ("neuralmind_bert-base-portuguese-cased__supervised", "bilstm-crf__supervised"),
    (
        "rufimelo_Legal-BERTimbau-base__supervised",
        "neuralmind_bert-base-portuguese-cased__supervised",
    ),
    ("gpt-4-turbo", "bilstm-crf__supervised"),
]


# ----- Layout normalisation ------------------------------------------------

DICT_LABELS = {
    "obrigacoes": "OBRIGACAO",
    "recomendacoes": "RECOMENDACAO",
    "ressarcimentos": "RESSARCIMENTO",
    "multas": "MULTA",
}


def convert_pred_to_golden_format(row, window_size=500, step_size=100, min_score=80):
    """Align a Pydantic LLM prediction back to character offsets in the source text."""
    pred_spans: list[dict] = []
    text = row["text"]
    pred = row["pred"]
    if not isinstance(pred, dict):
        return pred_spans
    for label_type, spans in pred.items():
        if label_type not in DICT_LABELS or not spans:
            continue
        for span in spans:
            if not isinstance(span, dict):
                continue
            span_text = (
                span.get("descricao_multa")
                or span.get("descricao_obrigacao")
                or span.get("descricao_ressarcimento")
                or span.get("descricao_recomendacao")
            )
            if not span_text:
                continue
            best_score, best_pos, best_substring = 0, -1, ""
            for start in range(0, max(1, len(text) - 1), step_size):
                window = text[start : start + window_size]
                score = fuzz.partial_ratio(span_text, window)
                if score > best_score and score >= min_score:
                    best_score = score
                    tokens = span_text.split()
                    if tokens:
                        rel = window.find(tokens[0])
                        best_pos = start + rel if rel >= 0 else start
                    else:
                        best_pos = start
                    best_substring = span_text
            if best_score >= min_score and best_pos >= 0:
                pred_spans.append(
                    {
                        "start": int(best_pos),
                        "end": int(best_pos + len(best_substring)),
                        "text": best_substring,
                        "labels": [DICT_LABELS[label_type]],
                    }
                )
    return pred_spans


def bio_to_spans(bio_seq) -> list[dict]:
    """Reconstruct ``{start, end, labels}`` dicts from a BIO sequence (token indices)."""
    spans: list[dict] = []
    i, n = 0, len(bio_seq)
    while i < n:
        tag = bio_seq[i]
        if isinstance(tag, str) and tag.startswith("B-"):
            label = tag[2:]
            start = i
            i += 1
            while i < n and isinstance(bio_seq[i], str) and bio_seq[i] == f"I-{label}":
                i += 1
            spans.append({"start": start, "end": i, "labels": [label]})
        else:
            i += 1
    return spans


def _candidate_paths(
    model_name: str, input_dir: Path, fallback_dir: Path | None = None
) -> list[Path]:
    paths = [
        input_dir / f"models_results_decicontas_{model_name}.json",
        input_dir / f"{model_name}.json",
        input_dir / f"{model_name}_predictions.json",
    ]
    if fallback_dir is not None:
        paths.extend(
            [
                fallback_dir / f"models_results_decicontas_{model_name}.json",
                fallback_dir / f"{model_name}.json",
                fallback_dir / f"{model_name}_predictions.json",
            ]
        )
    return paths


def _load_from_llm_layout(df: pd.DataFrame, model_name: str) -> pd.DataFrame:
    if "pred_as_golden" not in df.columns:
        if "pred" not in df.columns:
            raise ValueError("LLM layout missing both 'pred_as_golden' and 'pred'.")
        df = df.copy()
        df["pred_as_golden"] = df.apply(convert_pred_to_golden_format, axis=1)
    df["model"] = model_name
    return df.reset_index(drop=True)


def _load_from_bio_layout(obj, model_name: str) -> pd.DataFrame:
    rec = obj[0] if isinstance(obj, list) else obj
    true_labels = rec["true_labels"]
    pred_labels = rec["pred_labels"]
    if len(true_labels) != len(pred_labels):
        raise ValueError("BIO layout: true_labels and pred_labels lengths differ.")
    rows: list[dict] = []
    for i, (tl, pl) in enumerate(zip(true_labels, pred_labels)):
        rows.append(
            {
                "doc_id": i,
                "golden": bio_to_spans(tl),
                "pred_as_golden": bio_to_spans(pl),
                "model": model_name,
            }
        )
    return pd.DataFrame(rows)


def load_model_predictions(
    model_name: str,
    input_dir: Path,
    fallback_dir: Path | None = None,
) -> pd.DataFrame:
    for path in _candidate_paths(model_name, input_dir, fallback_dir):
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        if (
            isinstance(raw, list)
            and len(raw) == 1
            and isinstance(raw[0], dict)
            and "true_labels" in raw[0]
            and "pred_labels" in raw[0]
        ):
            return _load_from_bio_layout(raw, model_name)
        if isinstance(raw, dict) and "true_labels" in raw and "pred_labels" in raw:
            return _load_from_bio_layout(raw, model_name)
        df = pd.DataFrame(raw)
        if {"golden"} <= set(df.columns):
            return _load_from_llm_layout(df, model_name)
        raise ValueError(f"Unrecognised layout in {path}. Columns: {list(df.columns)}")
    raise FileNotFoundError(
        f"No predictions for '{model_name}' under {input_dir}"
    )


# ----- Per-document counts -------------------------------------------------


def compute_doc_level_counts(df: pd.DataFrame, iou_threshold: float = IOU_THRESHOLD):
    """Per-document tp/fp/fn under the shared bipartite greedy matcher
    (:func:`research.ner_metrics.bipartite_greedy_match`).

    Each pred matches at most one gold and vice-versa, so ``tp <=
    min(len(pred), len(gold))`` and the resulting ``fp`` and ``fn`` are
    always non-negative — corpus precision and recall stay in ``[0, 1]``
    and reproduce :func:`research.ner_metrics.calculate_metrics` exactly.
    """
    n = len(df)
    tp = np.zeros(n, dtype=np.int32)
    fp = np.zeros(n, dtype=np.int32)
    fn = np.zeros(n, dtype=np.int32)
    for i, row in enumerate(df.itertuples(index=False)):
        gold = [(g["start"], g["end"], g["labels"][0]) for g in row.golden]
        pred = [(p["start"], p["end"], p["labels"][0]) for p in row.pred_as_golden]
        matches = bipartite_greedy_match(pred, gold, iou_threshold=iou_threshold)
        tp[i] = len(matches)
        fp[i] = len(pred) - len(matches)
        fn[i] = len(gold) - len(matches)
    return tp, fp, fn


def f1_from_sums(tp_sum: int, fp_sum: int, fn_sum: int):
    p = tp_sum / (tp_sum + fp_sum) if (tp_sum + fp_sum) > 0 else 0.0
    r = tp_sum / (tp_sum + fn_sum) if (tp_sum + fn_sum) > 0 else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return p, r, f1


# ----- Bootstrap -----------------------------------------------------------


def bootstrap_ci_f1(counts, n_iter=N_BOOTSTRAP, seed=SEED, alpha=ALPHA):
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    n = len(tp)
    rng = np.random.default_rng(seed)
    f1s = np.empty(n_iter, dtype=np.float64)
    idx_matrix = rng.integers(0, n, size=(n_iter, n))
    for b in range(n_iter):
        idx = idx_matrix[b]
        _, _, f1 = f1_from_sums(tp[idx].sum(), fp[idx].sum(), fn[idx].sum())
        f1s[b] = f1
    lo = np.percentile(f1s, 100 * alpha / 2)
    hi = np.percentile(f1s, 100 * (1 - alpha / 2))
    return {
        "mean": float(f1s.mean()),
        "std": float(f1s.std(ddof=1)),
        "ci_lower": float(lo),
        "ci_upper": float(hi),
    }


def paired_bootstrap_diff(counts_a, counts_b, n_iter=N_BOOTSTRAP, seed=SEED, alpha=ALPHA):
    n = len(counts_a["tp"])
    assert n == len(counts_b["tp"])
    rng = np.random.default_rng(seed)
    idx_matrix = rng.integers(0, n, size=(n_iter, n))
    diffs = np.empty(n_iter, dtype=np.float64)
    for b in range(n_iter):
        idx = idx_matrix[b]
        _, _, f1_a = f1_from_sums(
            counts_a["tp"][idx].sum(),
            counts_a["fp"][idx].sum(),
            counts_a["fn"][idx].sum(),
        )
        _, _, f1_b = f1_from_sums(
            counts_b["tp"][idx].sum(),
            counts_b["fp"][idx].sum(),
            counts_b["fn"][idx].sum(),
        )
        diffs[b] = f1_a - f1_b
    lo = float(np.percentile(diffs, 100 * alpha / 2))
    hi = float(np.percentile(diffs, 100 * (1 - alpha / 2)))
    p_two = 2 * min((diffs <= 0).mean(), (diffs >= 0).mean())
    return {
        "mean_diff": float(diffs.mean()),
        "ci_lower": lo,
        "ci_upper": hi,
        "p_value": float(min(p_two, 1.0)),
        "significant": (lo > 0) or (hi < 0),
    }


# ----- LaTeX writers -------------------------------------------------------


def _escape_latex(s: str) -> str:
    return (
        s.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
    )


def write_latex_ci(df_ci: pd.DataFrame, out_path: Path) -> None:
    lines = []
    for _, row in df_ci.iterrows():
        name = _escape_latex(row["display_name"])
        lines.append(
            f"        {name:<35s} & {row['span_f1_point']:.4f} "
            f"& [{row['ci_lower']:.3f};\\ {row['ci_upper']:.3f}] \\\\"
        )
    tex = (
        "\\begin{table}[ht]\n"
        "    \\centering\n"
        "    \\caption{95\\% confidence intervals via \\textit{bootstrap} "
        "for the Span F1 of every evaluated model "
        f"({N_BOOTSTRAP:,} document-level resamples, IoU $\\geq$ 0.5).}}\n"
        "    \\label{tab:bootstrap_ic}\n"
        "    \\small\n"
        "    \\begin{tabular}{lcc}\n"
        "        \\hline\n"
        "        \\textbf{Model} & \\textbf{Span F1} & \\textbf{95\\% CI} \\\\\n"
        "        \\hline\n"
        + "\n".join(lines)
        + "\n"
        "        \\hline\n"
        "    \\end{tabular}\n"
        "\\end{table}\n"
    )
    out_path.write_text(tex, encoding="utf-8")


def write_latex_paired(df_highlighted: pd.DataFrame, out_path: Path) -> None:
    lines = []
    for _, row in df_highlighted.iterrows():
        a = _escape_latex(row["display_a"])
        b = _escape_latex(row["display_b"])
        sig = "Yes" if row["significant_95"] else "No"
        if row["p_value"] < 1e-3:
            p_str = "$< 0.001$"
        else:
            p_str = f"{row['p_value']:.3f}"
        diff_str = f"{row['diff_f1']:+.3f}"
        ci_str = f"[{row['ci_lower']:+.3f};\\ {row['ci_upper']:+.3f}]"
        lines.append(
            f"        {a} vs. {b} & {diff_str} & {ci_str} & {p_str} & {sig} \\\\"
        )
    tex = (
        "\\begin{table}[ht]\n"
        "    \\centering\n"
        "    \\caption{Paired comparisons via \\textit{bootstrap} "
        f"(B = {N_BOOTSTRAP:,}). "
        "A positive $\\Delta$ Span F1 indicates the first model outperforms the second.}\n"
        "    \\label{tab:bootstrap_paired}\n"
        "    \\small\n"
        "    \\begin{tabular}{lcccc}\n"
        "        \\hline\n"
        "        \\textbf{Comparison} & $\\Delta$ \\textbf{F1} "
        "& \\textbf{95\\% CI of difference} & $\\mathbf{p}$ & \\textbf{Sig. 5\\%} \\\\\n"
        "        \\hline\n"
        + "\n".join(lines)
        + "\n"
        "        \\hline\n"
        "    \\end{tabular}\n"
        "\\end{table}\n"
    )
    out_path.write_text(tex, encoding="utf-8")


# ----- Plots ---------------------------------------------------------------


def write_forest_plot(df_ci: pd.DataFrame, out_path: Path) -> None:
    import matplotlib.pyplot as plt

    df_plot = df_ci.sort_values("span_f1_point").reset_index(drop=True)
    y = np.arange(len(df_plot))
    fig, ax = plt.subplots(figsize=(9, max(4, 0.45 * len(df_plot))))
    ax.errorbar(
        df_plot["span_f1_point"],
        y,
        xerr=[
            df_plot["span_f1_point"] - df_plot["ci_lower"],
            df_plot["ci_upper"] - df_plot["span_f1_point"],
        ],
        fmt="o",
        capsize=4,
        markersize=6,
        linewidth=1.2,
    )
    best_f1 = df_plot["span_f1_point"].max()
    ax.axvline(
        best_f1,
        color="gray",
        linestyle="--",
        alpha=0.4,
        label=f"Melhor F1 pontual ({best_f1:.3f})",
    )
    ax.set_yticks(y)
    ax.set_yticklabels(df_plot["display_name"])
    ax.set_xlabel("F1 de Span (IoU $\\geq$ 0.5)")
    ax.set_title(f"Intervalos de Confiança de 95% (bootstrap, B = {N_BOOTSTRAP:,})")
    ax.grid(axis="x", linestyle=":", alpha=0.4)
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight", dpi=160)
    plt.savefig(out_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def write_heatmap(
    df_ci: pd.DataFrame, df_pairs: pd.DataFrame, out_path: Path
) -> None:
    import matplotlib.pyplot as plt

    model_order = df_ci["model"].tolist()
    display_order = [DISPLAY_NAMES.get(m, m) for m in model_order]
    n = len(model_order)
    diff_mat = np.zeros((n, n))
    sig_mat = np.zeros((n, n), dtype=bool)
    idx = {m: i for i, m in enumerate(model_order)}
    for _, row in df_pairs.iterrows():
        i = idx[row["model_a"]]
        j = idx[row["model_b"]]
        diff_mat[i, j] = row["diff_f1"]
        diff_mat[j, i] = -row["diff_f1"]
        sig_mat[i, j] = row["significant_95"]
        sig_mat[j, i] = row["significant_95"]
    annot = np.empty_like(diff_mat, dtype=object)
    for i in range(n):
        for j in range(n):
            if i == j:
                annot[i, j] = "-"
            else:
                s = f"{diff_mat[i, j]:+.3f}"
                if sig_mat[i, j]:
                    s += "*"
                annot[i, j] = s
    fig, ax = plt.subplots(figsize=(0.75 * n + 3, 0.6 * n + 2))
    vmax = np.abs(diff_mat).max()
    im = ax.imshow(diff_mat, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="equal")
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(display_order, rotation=45, ha="right")
    ax.set_yticklabels(display_order)
    for i in range(n):
        for j in range(n):
            color = "black" if abs(diff_mat[i, j]) < 0.6 * vmax else "white"
            ax.text(
                j, i, annot[i, j], ha="center", va="center", color=color, fontsize=8
            )
    cbar = plt.colorbar(im, ax=ax, shrink=0.75)
    cbar.set_label("Diferença de F1 de Span (linha - coluna)")
    ax.set_title(
        f"Diferenças pareadas de F1 de Span (* = significativo a 5%, B = {N_BOOTSTRAP:,})"
    )
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight", dpi=160)
    plt.savefig(out_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


# ----- Orchestration -------------------------------------------------------


def run(
    *,
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    fig_dir: Path = DEFAULT_FIG_DIR,
    fallback_dir: Path | None = None,
) -> dict[str, pd.DataFrame]:
    """Run the full bootstrap analysis. ``fallback_dir`` is consulted for
    any model JSON missing from ``input_dir`` — useful when the supervised
    retrain has not finished yet and we want to combine corrected LLMs
    with the legacy supervised predictions for a partial leaderboard."""
    output_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    model_dfs: dict[str, pd.DataFrame] = {}
    for m in MODELS:
        try:
            model_dfs[m] = load_model_predictions(m, input_dir, fallback_dir)
            logger.info("loaded %s (%d docs)", m, len(model_dfs[m]))
        except FileNotFoundError as exc:
            logger.warning("skipping %s: %s", m, exc)

    if len(model_dfs) < 2:
        raise RuntimeError("at least 2 models required to run comparisons")

    # Drop few-shot leak positions
    model_dfs = {
        m: df.drop(index=FEWSHOT_RESULT_POSITIONS, errors="ignore").reset_index(
            drop=True
        )
        for m, df in model_dfs.items()
    }

    # Align lengths
    lengths = {m: len(df) for m, df in model_dfs.items()}
    most_common_len, _ = Counter(lengths.values()).most_common(1)[0]
    model_dfs = {m: df for m, df in model_dfs.items() if len(df) == most_common_len}
    logger.info(
        "aligned to %d docs across %d models", most_common_len, len(model_dfs)
    )

    # Compute counts + per-model F1
    model_counts: dict[str, dict[str, Any]] = {}
    for m, df in model_dfs.items():
        tp, fp, fn = compute_doc_level_counts(df)
        p, r, f1 = f1_from_sums(int(tp.sum()), int(fp.sum()), int(fn.sum()))
        model_counts[m] = {"tp": tp, "fp": fp, "fn": fn, "f1": f1, "p": p, "r": r}
        logger.info("%s: F1=%.4f P=%.4f R=%.4f", m, f1, p, r)

    # Individual CIs
    results_ci: dict[str, dict[str, float]] = {}
    for m, counts in model_counts.items():
        results_ci[m] = bootstrap_ci_f1(counts)

    df_ci = (
        pd.DataFrame(
            [
                {
                    "model": m,
                    "display_name": DISPLAY_NAMES.get(m, m),
                    "span_f1_point": model_counts[m]["f1"],
                    "span_f1_mean": r["mean"],
                    "std": r["std"],
                    "ci_lower": r["ci_lower"],
                    "ci_upper": r["ci_upper"],
                    "ci_width": r["ci_upper"] - r["ci_lower"],
                }
                for m, r in results_ci.items()
            ]
        )
        .sort_values("span_f1_point", ascending=False)
        .reset_index(drop=True)
    )

    # Paired comparisons
    pair_rows: list[dict[str, Any]] = []
    for a, b in combinations(list(model_counts.keys()), 2):
        r = paired_bootstrap_diff(model_counts[a], model_counts[b])
        pair_rows.append(
            {
                "model_a": a,
                "model_b": b,
                "display_a": DISPLAY_NAMES.get(a, a),
                "display_b": DISPLAY_NAMES.get(b, b),
                "f1_a": model_counts[a]["f1"],
                "f1_b": model_counts[b]["f1"],
                "diff_f1": r["mean_diff"],
                "ci_lower": r["ci_lower"],
                "ci_upper": r["ci_upper"],
                "p_value": r["p_value"],
                "significant_95": r["significant"],
            }
        )
    df_pairs = (
        pd.DataFrame(pair_rows)
        .sort_values("diff_f1", key=abs, ascending=False)
        .reset_index(drop=True)
    )

    mask = df_pairs.apply(
        lambda row: (
            (row["model_a"], row["model_b"]) in HIGHLIGHTED_PAIRS
            or (row["model_b"], row["model_a"]) in HIGHLIGHTED_PAIRS
        ),
        axis=1,
    )
    df_highlighted = df_pairs[mask].copy().reset_index(drop=True)

    # Persist
    df_ci.to_csv(output_dir / "bootstrap_ci.csv", index=False, encoding="utf-8")
    df_pairs.to_csv(
        output_dir / "bootstrap_paired.csv", index=False, encoding="utf-8"
    )
    df_highlighted.to_csv(
        output_dir / "bootstrap_highlighted_pairs.csv",
        index=False,
        encoding="utf-8",
    )
    df_pairs.to_markdown(
        output_dir / "paired_bootstrap_results.csv", index=False
    )
    write_latex_ci(df_ci, output_dir / "table_bootstrap_ic.tex")
    write_latex_paired(df_highlighted, output_dir / "table_bootstrap_paired.tex")
    write_forest_plot(df_ci, fig_dir / "forest_plot_bootstrap.png")
    write_heatmap(df_ci, df_pairs, fig_dir / "heatmap_pairs_bootstrap.png")

    return {"df_ci": df_ci, "df_pairs": df_pairs, "df_highlighted": df_highlighted}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--fig-dir", type=Path, default=DEFAULT_FIG_DIR)
    parser.add_argument(
        "--fallback-dir",
        type=Path,
        default=None,
        help="If a model file is missing from --input-dir, look here too. "
        "Useful for combining corrected LLM rescores with the legacy "
        "supervised predictions while the supervised retrain is in flight.",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    out = run(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        fig_dir=args.fig_dir,
        fallback_dir=args.fallback_dir,
    )
    df_ci = out["df_ci"]
    print("\nLeaderboard (point F1, 95% CI):")
    for _, row in df_ci.iterrows():
        print(
            f"  {row['display_name']:<25s} "
            f"F1={row['span_f1_point']:.4f} "
            f"[{row['ci_lower']:.3f}; {row['ci_upper']:.3f}]"
        )


if __name__ == "__main__":
    main()
