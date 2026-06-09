"""Reproducible numerics for Chapter 5 of the dissertation.

Consumes the cleanlab-corrected results we already produced (LLM
rescores + supervised k-fold retrain + bootstrap) and emits one CSV
per logical block plus a master ``REPORT.md`` cross-referencing the
specific numbers each section of the chapter cites.

Blocks (mirrors the user's checklist):

A. Corpus characterisation
B. Cleanlab audit (group counts, transition matrix, per-class delta)
C. Main results table — 14 models × overall metrics + per-fold std
D. Per-entity span F1 heatmap (14 × 4)
E. Cost-benefit (input/output tokens, no API cost data on disk)
F. Function-calling vs JSON schema (4 × 2 × overall metrics)
G. Function-calling vs JSON schema per entity (4 × 2 × 4)
H. Prompt techniques (4 × 4 + per-entity for narrative pairs)
I. Error analysis of best model
J. Bootstrap CIs + paired comparisons
K. Canonical token F1 number normalisation note

Run:
    uv run python -m research.release.chapter5_numbers
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support

from research.fewshot import FEWSHOT_RESULT_POSITIONS
from research.ner_metrics import (
    ENTITY_LABELS,
    _span_metric_totals,
    _strip_bio,
    bio_to_char_spans,
    bipartite_greedy_match,
    calculate_metrics,
    convert_pred_to_golden_format,
    count_alignment_failures,
    flatten_metrics,
    span_metrics_multi_iou,
)
from research.release.bootstrap_significance import (
    DISPLAY_NAMES,
    HIGHLIGHTED_PAIRS,
    MODELS,
    bootstrap_ci_f1,
    compute_doc_level_counts,
    f1_from_sums,
    paired_bootstrap_diff,
)


from research.release import paths

REPO_ROOT = paths.REPO_ROOT
OUTPUT_ROOT = paths.CHAPTER5_DIR
RELEASE_DIR = paths.RELEASE_DIR  # shared
RELEASE_PRE_DIR = paths.RELEASE_PRE_DIR  # shared
CORRECTIONS_JSON = paths.CORRECTIONS_JSON  # shared

CORRECTED_OUTPUT_DIR = paths.OUTPUT_CORRECTED_DIR
EXPERIMENTS_DIR = paths.CORRECTED_EXPERIMENTS_DIR
KFOLD_CORRECTED = paths.KFOLD_CORRECTED  # shared

logger = logging.getLogger("research.release.chapter5_numbers")


def _ensure_pred_as_golden(df: pd.DataFrame) -> pd.DataFrame:
    if "pred_as_golden" in df.columns:
        return df
    df = df.copy()
    df["pred_as_golden"] = df.apply(convert_pred_to_golden_format, axis=1)
    return df


# ----- Block A + B: corpus and cleanlab audit -----------------------------


def block_a_corpus(out_dir: Path) -> dict[str, Any]:
    pre = json.loads((RELEASE_PRE_DIR / "decicontas.json").read_text(encoding="utf-8"))
    post = json.loads((RELEASE_DIR / "decicontas.json").read_text(encoding="utf-8"))

    def _summary(docs):
        n = len(docs)
        n_with = sum(1 for d in docs if d["entities"])
        per_class = Counter(e["label"] for d in docs for e in d["entities"])
        return {
            "total_docs": n,
            "docs_with_entity": n_with,
            "docs_without_entity": n - n_with,
            "total_entities": sum(per_class.values()),
            **{label: per_class.get(label, 0) for label in ENTITY_LABELS},
        }

    pre_s = _summary(pre)
    post_s = _summary(post)
    rows = []
    for k in pre_s:
        rows.append({"metric": k, "before": pre_s[k], "after": post_s[k], "delta": post_s[k] - pre_s[k]})
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "A_corpus.csv", index=False)
    logger.info("wrote %s", out_dir / "A_corpus.csv")
    return {"pre": pre_s, "post": post_s}


def block_b_cleanlab(out_dir: Path) -> dict[str, Any]:
    payload = json.loads(CORRECTIONS_JSON.read_text(encoding="utf-8"))
    summary = payload.get("summary") or {}
    decisions = Counter()
    label_final_counts = Counter()
    for change in payload.get("token_changes", []):
        decisions[change["decision"]] += 1
        label_final_counts[change["label_final"]] += 1
    # Group-level decisions are the unit the reviewer acted on (one decision per
    # flagged entity group), recorded in the corrections file's ``summary``.
    # These answer p57: of the 567 inspected groups, how many were actually
    # altered vs. left at gold. They are distinct from the per-token tallies
    # below (one flagged group spans many tokens).
    g_accept = summary.get("accept") or 0
    g_reject = summary.get("reject") or 0
    g_custom = summary.get("custom") or 0
    g_decided = summary.get("groups_decided") or 0
    g_altered = g_accept + g_custom
    rows_summary = [
        {"metric": "groups_total", "value": summary.get("groups_total")},
        {"metric": "groups_decided_>=0.95", "value": g_decided},
        {
            "metric": "groups_below_threshold",
            "value": (summary.get("groups_total") or 0) - g_decided,
        },
        # --- group-level decisions (p57: intervention volume) ---
        {"metric": "groups_accept", "value": g_accept},
        {"metric": "groups_custom", "value": g_custom},
        {"metric": "groups_reject", "value": g_reject},
        {"metric": "groups_altered (accept+custom)", "value": g_altered},
        {
            "metric": "groups_acceptance_rate",
            "value": round(g_altered / g_decided, 4) if g_decided else None,
        },
        {
            "metric": "groups_rejection_rate",
            "value": round(g_reject / g_decided, 4) if g_decided else None,
        },
        # --- token-level tallies (every token inside the decided groups) ---
        {"metric": "token_changes", "value": summary.get("token_changes")},
        {"metric": "token_decision_accept", "value": decisions.get("accept", 0)},
        {"metric": "token_decision_reject", "value": decisions.get("reject", 0)},
        {"metric": "token_decision_custom", "value": decisions.get("custom", 0)},
    ]
    pd.DataFrame(rows_summary).to_csv(out_dir / "B_cleanlab_summary.csv", index=False)
    logger.info("wrote %s", out_dir / "B_cleanlab_summary.csv")

    # label_final distribution (what corrected tokens become)
    label_rows = [{"label_final": k, "count": v} for k, v in sorted(label_final_counts.items())]
    pd.DataFrame(label_rows).to_csv(out_dir / "B_label_final_counts.csv", index=False)
    logger.info("wrote %s", out_dir / "B_label_final_counts.csv")

    # Net delta by class (recover from before/after)
    pre = json.loads((RELEASE_PRE_DIR / "decicontas.json").read_text(encoding="utf-8"))
    post = json.loads((RELEASE_DIR / "decicontas.json").read_text(encoding="utf-8"))
    pre_c = Counter(e["label"] for d in pre for e in d["entities"])
    post_c = Counter(e["label"] for d in post for e in d["entities"])
    delta_rows = [
        {"label": label, "before": pre_c[label], "after": post_c[label], "delta": post_c[label] - pre_c[label]}
        for label in ENTITY_LABELS
    ]
    pd.DataFrame(delta_rows).to_csv(out_dir / "B_class_delta.csv", index=False)
    logger.info("wrote %s", out_dir / "B_class_delta.csv")
    return {"summary": summary, "label_final": label_final_counts}


# ----- Block C + D: per-model overall + per-entity ------------------------


def _load_llm_df(path: Path) -> pd.DataFrame:
    raw = json.loads(path.read_text(encoding="utf-8"))
    df = pd.DataFrame(raw)
    return _ensure_pred_as_golden(df)


_CORRECTED_DOCS_BY_MASTER_POSITION: list[dict] | None = None


def _corrected_docs_by_master_position() -> list[dict]:
    """Cache the corrected dataset and pad with empty placeholders at the
    five fewshot positions so it aligns 1-to-1 with the supervised JSON
    (866 entries, with empty BIO at positions 5/781/789/816/851)."""
    global _CORRECTED_DOCS_BY_MASTER_POSITION
    if _CORRECTED_DOCS_BY_MASTER_POSITION is not None:
        return _CORRECTED_DOCS_BY_MASTER_POSITION
    docs = json.loads(
        (RELEASE_DIR / "decicontas.json").read_text(encoding="utf-8")
    )
    fewshot = set(FEWSHOT_RESULT_POSITIONS)
    docs_iter = iter(docs)
    full: list[dict] = []
    for pos in range(866):
        if pos in fewshot:
            full.append({})
        else:
            full.append(next(docs_iter))
    _CORRECTED_DOCS_BY_MASTER_POSITION = full
    return full


def _load_supervised_df(path: Path) -> pd.DataFrame:
    """Load supervised OOF JSON and convert BIO sequences to character-level
    spans using the corrected dataset's ``token_offsets``.

    Carrying ``text`` plus char-offset spans lets ``calculate_metrics``
    score supervised baselines through the same spaCy tokenizer used for
    LLMs — fixing audit finding #1 (incommensurable token F1).
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    rec = raw[0] if isinstance(raw, list) else raw
    full = _corrected_docs_by_master_position()
    rows: list[dict] = []
    for i, (tl, pl) in enumerate(zip(rec["true_labels"], rec["pred_labels"])):
        doc = full[i]
        if not doc:
            # Fewshot placeholder — drop_fewshot will remove it later.
            rows.append(
                {
                    "doc_id": i,
                    "text": "",
                    "golden": [],
                    "pred_as_golden": [],
                    "model": rec.get("model", path.stem),
                }
            )
            continue
        offsets = [
            {"start": s, "end": e} for s, e in doc.get("token_offsets", [])
        ]
        # Truncate to whichever is shortest so misaligned BIO sequences
        # (e.g. truncated at training time) don't wander off into
        # unmapped offset territory.
        min_len = min(len(tl), len(pl), len(offsets))
        rows.append(
            {
                "doc_id": i,
                "text": doc["text"],
                "golden": bio_to_char_spans(tl[:min_len], offsets[:min_len]),
                "pred_as_golden": bio_to_char_spans(pl[:min_len], offsets[:min_len]),
                "model": rec.get("model", path.stem),
            }
        )
    return pd.DataFrame(rows)


def _drop_fewshot(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(index=FEWSHOT_RESULT_POSITIONS, errors="ignore").reset_index(drop=True)


def _is_supervised_model(name: str) -> bool:
    return name.endswith("__supervised")


def load_all_models(input_dir: Path) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for m in MODELS:
        path = input_dir / f"models_results_decicontas_{m}.json"
        if not path.exists():
            logger.warning("missing %s", path)
            continue
        if _is_supervised_model(m):
            df = _load_supervised_df(path)
        else:
            df = _load_llm_df(path)
        df = _drop_fewshot(df)
        out[m] = df
    return out


def _per_entity_metrics_llm(df: pd.DataFrame) -> dict[str, Any]:
    """Run calculate_metrics; flatten per-entity P/R/F1 (LLM/char-offset path)."""
    raw = calculate_metrics(df, iou_threshold=0.5)
    return _pack_per_entity(raw)


def _per_entity_metrics_bio(df: pd.DataFrame) -> dict[str, Any]:
    """Compute BIO-based metrics for supervised predictions where ``golden``
    and ``pred_as_golden`` carry token-index spans (not character offsets).

    Mirrors :func:`research.ner_metrics.evaluate_bio_results` but operates on
    the per-doc DataFrame layout used here and exposes the raw dict for
    per-entity extraction.
    """
    flat_true: list[str] = []
    flat_pred: list[str] = []
    label_metrics: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total_gold": 0, "total_pred": 0, "matched": 0}
    )
    for _, row in df.iterrows():
        gold_spans = [(g["start"], g["end"], g["labels"][0]) for g in row.get("golden", [])]
        pred_spans = [(p["start"], p["end"], p["labels"][0]) for p in row.get("pred_as_golden", [])]
        # Token-level: rebuild BIO sequences over the document's token range.
        ends = [s[1] for s in gold_spans] + [s[1] for s in pred_spans]
        max_tok = max(ends) if ends else 0
        true_bio = ["O"] * max_tok
        pred_bio = ["O"] * max_tok
        for s, e, lab in gold_spans:
            for j in range(s, e):
                true_bio[j] = (f"B-{lab}" if j == s else f"I-{lab}")
        for s, e, lab in pred_spans:
            for j in range(s, e):
                pred_bio[j] = (f"B-{lab}" if j == s else f"I-{lab}")
        for t, p in zip(true_bio, pred_bio):
            tl, pl = _strip_bio(t), _strip_bio(p)
            if tl != "O" or pl != "O":
                flat_true.append(tl)
                flat_pred.append(pl)
        # Span-level IoU at token-index granularity, using the shared bipartite
        # matcher (each pred matches at most one gold and vice-versa).
        for _, _, lab in gold_spans:
            label_metrics[lab]["total_gold"] += 1
        for _, _, lab in pred_spans:
            label_metrics[lab]["total_pred"] += 1
        for pi, _ in bipartite_greedy_match(pred_spans, gold_spans, iou_threshold=0.5):
            label_metrics[pred_spans[pi][2]]["matched"] += 1

    labels_sorted = sorted({lab for lab in flat_true + flat_pred if lab != "O"})
    if labels_sorted:
        token_prec, token_rec, token_f1, _ = precision_recall_fscore_support(
            flat_true, flat_pred, labels=labels_sorted, average="micro", zero_division=0
        )
    else:
        token_prec = token_rec = token_f1 = 0.0
    iou_p, iou_r, iou_f1, per_label = _span_metric_totals(label_metrics)
    raw = {
        "token_flat": {
            "precision": float(token_prec),
            "recall": float(token_rec),
            "f1": float(token_f1),
        },
        "iou_agg": {"precision": iou_p, "recall": iou_r, "f1": iou_f1},
        "iou_per_label": per_label,
    }
    return _pack_per_entity(raw)


def _pack_per_entity(raw: dict) -> dict[str, Any]:
    per = raw.get("iou_per_label", {})
    out = {}
    for label in ENTITY_LABELS:
        m = per.get(label) or {}
        out[label] = {
            "precision": float(m.get("precision", 0.0)),
            "recall": float(m.get("recall", 0.0)),
            "f1": float(m.get("f1", 0.0)),
            "matched": int(m.get("matched", 0)),
            "total_gold": int(m.get("total_gold", 0)),
            "total_pred": int(m.get("total_pred", 0)),
        }
    return {"flat": flatten_metrics(raw), "per_entity": out, "raw": raw}


def _per_entity_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """Dispatch based on whether the DataFrame carries char-offset
    predictions (LLM, with ``text``) or token-index ones (supervised)."""
    if "text" in df.columns:
        return _per_entity_metrics_llm(df)
    return _per_entity_metrics_bio(df)


def block_cd_main_results(model_dfs: dict[str, pd.DataFrame], out_dir: Path) -> dict[str, dict]:
    """Compute Block C (overall) + Block D (per-entity) + supervised fold std."""
    overall_rows = []
    per_entity_rows = []
    cv_std_rows = []
    metrics_by_model: dict[str, dict] = {}
    for m, df in model_dfs.items():
        logger.info("metrics for %s", m)
        result = _per_entity_metrics(df)
        flat = result["flat"]
        metrics_by_model[m] = result
        overall_rows.append(
            {
                "model": m,
                "display": DISPLAY_NAMES.get(m, m),
                "token_f1": flat["token_f1"],
                "token_f1_macro": flat.get("token_f1_macro", float("nan")),
                "token_precision": flat["token_precision"],
                "token_recall": flat["token_recall"],
                "span_f1": flat["span_f1"],
                "span_f1_macro": flat["span_f1_macro"],
                "span_precision": flat["span_precision"],
                "span_recall": flat["span_recall"],
            }
        )
        for label, vals in result["per_entity"].items():
            per_entity_rows.append(
                {
                    "model": m,
                    "display": DISPLAY_NAMES.get(m, m),
                    "label": label,
                    "precision": vals["precision"],
                    "recall": vals["recall"],
                    "f1": vals["f1"],
                    "matched": vals["matched"],
                    "total_gold": vals["total_gold"],
                    "total_pred": vals["total_pred"],
                }
            )

    # Supervised fold std (Block C item 17-19)
    safe_map = {
        "bilstm-crf__supervised": "bilstm-crf",
        "neuralmind_bert-base-portuguese-cased__supervised": "neuralmind_bert-base-portuguese-cased",
        "neuralmind_bert-large-portuguese-cased__supervised": "neuralmind_bert-large-portuguese-cased",
        "rufimelo_Legal-BERTimbau-base__supervised": "rufimelo_Legal-BERTimbau-base",
    }
    for m, safe in safe_map.items():
        cv_path = KFOLD_CORRECTED / "summary" / f"cv_{safe}.json"
        if not cv_path.exists():
            continue
        cv = json.loads(cv_path.read_text(encoding="utf-8"))
        sf = cv["span_f1"]
        tf = cv["token_f1"]
        cv_std_rows.append(
            {
                "model": m,
                "display": DISPLAY_NAMES.get(m, m),
                "span_f1_mean": sf["mean"],
                "span_f1_std": sf["std"],
                "span_f1_min": min(sf["values"]),
                "span_f1_max": max(sf["values"]),
                "span_f1_per_fold": "; ".join(f"{v:.4f}" for v in sf["values"]),
                "token_f1_mean": tf["mean"],
                "token_f1_std": tf["std"],
                "token_f1_min": min(tf["values"]),
                "token_f1_max": max(tf["values"]),
                "token_f1_per_fold": "; ".join(f"{v:.4f}" for v in tf["values"]),
                "config": json.dumps(cv["config"], ensure_ascii=False),
            }
        )

    df_overall = (
        pd.DataFrame(overall_rows).sort_values("span_f1", ascending=False).reset_index(drop=True)
    )
    df_per_entity = pd.DataFrame(per_entity_rows)
    df_cv_std = pd.DataFrame(cv_std_rows)

    df_overall.to_csv(out_dir / "C_main_results.csv", index=False)
    df_per_entity.to_csv(out_dir / "D_per_entity.csv", index=False)
    df_cv_std.to_csv(out_dir / "C_supervised_fold_std.csv", index=False)
    logger.info("wrote %s", out_dir / "C_main_results.csv")
    logger.info("wrote %s", out_dir / "D_per_entity.csv")
    logger.info("wrote %s", out_dir / "C_supervised_fold_std.csv")

    # Pivot for heatmap (model rows × entity columns) — span F1
    heatmap = (
        df_per_entity.pivot(index="display", columns="label", values="f1")[
            list(ENTITY_LABELS)
        ]
    )
    heatmap.to_csv(out_dir / "D_heatmap_span_f1.csv")
    logger.info("wrote %s", out_dir / "D_heatmap_span_f1.csv")
    return metrics_by_model


# ----- Block F + G: function calling vs JSON schema -----------------------


def block_fg_structured(out_dir: Path) -> None:
    src = EXPERIMENTS_DIR / "function_calling_json_schema"
    if not src.exists():
        logger.warning("missing %s", src)
        return
    overall_rows = []
    per_entity_rows = []
    for jf in sorted(src.glob("*.json")):
        df = _ensure_pred_as_golden(_load_llm_df(jf))
        df = _drop_fewshot(df)
        result = _per_entity_metrics(df)
        flat = result["flat"]
        name = jf.stem.replace("models_results_decicontas_", "")
        method = "function_calling" if name.endswith("_fc") else "json_schema"
        model_clean = name.replace("_fc", "").replace("_json", "").replace("_few_shot", "")
        overall_rows.append(
            {
                "model": model_clean,
                "method": method,
                "token_f1": flat["token_f1"],
                "span_f1": flat["span_f1"],
                "span_f1_macro": flat["span_f1_macro"],
                "span_precision": flat["span_precision"],
                "span_recall": flat["span_recall"],
            }
        )
        for label, vals in result["per_entity"].items():
            per_entity_rows.append(
                {
                    "model": model_clean,
                    "method": method,
                    "label": label,
                    "f1": vals["f1"],
                    "precision": vals["precision"],
                    "recall": vals["recall"],
                }
            )
    df_overall = pd.DataFrame(overall_rows).sort_values(["model", "method"]).reset_index(drop=True)
    df_per_entity = pd.DataFrame(per_entity_rows)

    # Compute deltas (FC - JS) per model
    pivot_overall = df_overall.set_index(["model", "method"])
    delta_rows = []
    for model in pivot_overall.index.get_level_values(0).unique():
        try:
            fc = pivot_overall.loc[(model, "function_calling")]
            js = pivot_overall.loc[(model, "json_schema")]
        except KeyError:
            continue
        delta_rows.append(
            {
                "model": model,
                "delta_token_f1": fc["token_f1"] - js["token_f1"],
                "delta_span_f1": fc["span_f1"] - js["span_f1"],
                "delta_span_precision": fc["span_precision"] - js["span_precision"],
                "delta_span_recall": fc["span_recall"] - js["span_recall"],
            }
        )
    df_delta = pd.DataFrame(delta_rows)

    df_overall.to_csv(out_dir / "F_fc_vs_json_overall.csv", index=False)
    df_delta.to_csv(out_dir / "F_fc_vs_json_delta.csv", index=False)
    df_per_entity.to_csv(out_dir / "G_fc_vs_json_per_entity.csv", index=False)
    logger.info("wrote %s, %s, %s", "F_fc_vs_json_overall.csv", "F_fc_vs_json_delta.csv", "G_fc_vs_json_per_entity.csv")


# ----- Block H: prompt engineering techniques -----------------------------


def _parse_technique(stem: str) -> tuple[str, str]:
    techniques = ["dynamic_few_shot", "two_stage", "few_shot", "cot"]
    name = stem.replace("models_results_decicontas_", "")
    for t in techniques:
        if name.endswith(f"_{t}"):
            return name[: -(len(t) + 1)], t
    return name, "unknown"


def block_h_prompting(out_dir: Path) -> None:
    src = EXPERIMENTS_DIR / "prompt_engineering"
    if not src.exists():
        logger.warning("missing %s", src)
        return
    overall_rows = []
    per_entity_rows = []
    for jf in sorted(src.glob("*.json")):
        df = _ensure_pred_as_golden(_load_llm_df(jf))
        df = _drop_fewshot(df)
        result = _per_entity_metrics(df)
        flat = result["flat"]
        model, technique = _parse_technique(jf.stem)
        overall_rows.append(
            {
                "model": model,
                "technique": technique,
                "token_f1": flat["token_f1"],
                "span_f1": flat["span_f1"],
                "span_f1_macro": flat["span_f1_macro"],
                "span_precision": flat["span_precision"],
                "span_recall": flat["span_recall"],
            }
        )
        for label, vals in result["per_entity"].items():
            per_entity_rows.append(
                {
                    "model": model,
                    "technique": technique,
                    "label": label,
                    "f1": vals["f1"],
                    "precision": vals["precision"],
                    "recall": vals["recall"],
                }
            )
    df_overall = pd.DataFrame(overall_rows).sort_values(["model", "technique"]).reset_index(drop=True)
    df_per_entity = pd.DataFrame(per_entity_rows)

    # Aggregated stats by technique
    tech_summary = (
        df_overall.groupby("technique")[["token_f1", "span_f1"]]
        .agg(["mean", "std", "min", "max"])
        .reset_index()
    )

    df_overall.to_csv(out_dir / "H_prompting_overall.csv", index=False)
    df_per_entity.to_csv(out_dir / "H_prompting_per_entity.csv", index=False)
    tech_summary.to_csv(out_dir / "H_prompting_technique_summary.csv", index=False)
    logger.info("wrote H_prompting_*.csv")


# ----- Block I: error analysis of best model ------------------------------


def _classify_pair(pred_spans, gold_spans, iou_threshold: float = 0.5):
    """Match pred to gold; categorize each as exact, type_error, boundary, FP, FN.

    Strategy: per (pred, gold) pair compute IoU. For each pred, take the
    gold span with highest overlap (regardless of label). If best IoU >=
    threshold and labels match -> "exact". Same gold but labels differ ->
    "type_error". IoU > 0 but < threshold -> "boundary". Else (no overlap
    at all) -> "FP". Gold spans that never get any pred with IoU > 0 ->
    "FN".
    """
    used_gold: set[int] = set()
    pred_classes: list[dict] = []
    for pi, p in enumerate(pred_spans):
        best_gi = -1
        best_iou = 0.0
        for gi, g in enumerate(gold_spans):
            inter = max(0, min(p[1], g[1]) - max(p[0], g[0]))
            union = max(p[1], g[1]) - min(p[0], g[0])
            iou = inter / union if union > 0 else 0.0
            if iou > best_iou:
                best_iou = iou
                best_gi = gi
        if best_iou == 0.0:
            pred_classes.append({"kind": "FP", "label": p[2], "iou": 0.0})
            continue
        used_gold.add(best_gi)
        gold_label = gold_spans[best_gi][2]
        if best_iou >= iou_threshold and p[2] == gold_label:
            pred_classes.append({"kind": "exact", "label": gold_label, "iou": best_iou})
        elif best_iou >= iou_threshold and p[2] != gold_label:
            pred_classes.append(
                {"kind": "type_error", "label": gold_label, "pred_label": p[2], "iou": best_iou}
            )
        else:  # 0 < iou < threshold
            pred_classes.append({"kind": "boundary", "label": gold_label, "pred_label": p[2], "iou": best_iou})
    fn_classes = [
        {"kind": "FN", "label": gold_spans[gi][2], "iou": 0.0}
        for gi in range(len(gold_spans))
        if gi not in used_gold
    ]
    return pred_classes + fn_classes


def block_i_errors(model_dfs: dict[str, pd.DataFrame], best_model: str, out_dir: Path) -> None:
    if best_model not in model_dfs:
        logger.warning("best model %s not loaded; skipping error analysis", best_model)
        return
    df = model_dfs[best_model]
    rows: list[dict] = []
    for _, row in df.iterrows():
        gold = [(g["start"], g["end"], g["labels"][0]) for g in row.get("golden", [])]
        pred = [(p["start"], p["end"], p["labels"][0]) for p in row.get("pred_as_golden", [])]
        for cls in _classify_pair(pred, gold):
            rows.append(cls)
    err_df = pd.DataFrame(rows)
    err_df.to_csv(out_dir / "I_errors_long.csv", index=False)

    # Counts by kind
    counts_kind = err_df["kind"].value_counts().to_dict()
    pd.DataFrame(
        [{"kind": k, "count": v} for k, v in counts_kind.items()]
    ).to_csv(out_dir / "I_errors_by_kind.csv", index=False)

    # Matrix label × kind
    matrix = err_df.groupby(["label", "kind"]).size().unstack(fill_value=0)
    matrix.to_csv(out_dir / "I_errors_label_x_kind.csv")

    # Type-error pairs (gold label -> pred label)
    type_errors = err_df[err_df["kind"] == "type_error"]
    if not type_errors.empty:
        pair_counts = type_errors.groupby(["label", "pred_label"]).size().reset_index(name="count")
        pair_counts.to_csv(out_dir / "I_type_error_pairs.csv", index=False)

    # IoU histogram for boundary errors
    bins = [0.0, 0.2, 0.4, 0.5, 0.7, 0.9, 1.0]
    boundary = err_df[err_df["kind"] == "boundary"]
    if not boundary.empty:
        hist, edges = np.histogram(boundary["iou"], bins=bins)
        hist_df = pd.DataFrame(
            {
                "bin_low": edges[:-1],
                "bin_high": edges[1:],
                "count": hist,
            }
        )
        hist_df.to_csv(out_dir / "I_boundary_iou_histogram.csv", index=False)

    logger.info("wrote I_errors_*.csv (best model: %s, %d records)", best_model, len(err_df))


# ----- Block J: bootstrap CIs + paired comparisons ------------------------


def _holm_bonferroni(pvals: list[float]) -> tuple[list[float], list[float]]:
    """Return (Holm-adjusted, Bonferroni-adjusted) p-values for a family.

    Holm is the step-down method (uniformly more powerful than Bonferroni
    while controlling the same family-wise error rate). Both are computed
    here without a statsmodels dependency. The family is the set of
    comparisons passed in (see :func:`block_j_significance`, where it is the
    reported highlighted pairs).
    """
    m = len(pvals)
    if m == 0:
        return [], []
    bonf = [min(1.0, p * m) for p in pvals]
    order = sorted(range(m), key=lambda i: pvals[i])
    holm = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * pvals[idx])
        holm[idx] = min(1.0, running)
    return holm, bonf


def block_j_significance(model_dfs: dict[str, pd.DataFrame], out_dir: Path) -> dict[str, Any]:
    model_counts: dict[str, dict] = {}
    for m, df in model_dfs.items():
        tp, fp, fn = compute_doc_level_counts(df)
        p, r, f1 = f1_from_sums(int(tp.sum()), int(fp.sum()), int(fn.sum()))
        model_counts[m] = {"tp": tp, "fp": fp, "fn": fn, "f1": f1, "p": p, "r": r}

    # Block J item 41: B = 10000, configured upstream

    ci_rows = []
    for m, c in model_counts.items():
        ci = bootstrap_ci_f1(c)
        ci_rows.append(
            {
                "model": m,
                "display": DISPLAY_NAMES.get(m, m),
                "span_f1_point": c["f1"],
                "span_f1_mean": ci["mean"],
                "span_f1_std": ci["std"],
                "ci_lower": ci["ci_lower"],
                "ci_upper": ci["ci_upper"],
                "ci_width": ci["ci_upper"] - ci["ci_lower"],
            }
        )
    df_ci = pd.DataFrame(ci_rows).sort_values("span_f1_point", ascending=False).reset_index(drop=True)
    df_ci.to_csv(out_dir / "J_bootstrap_ci.csv", index=False)

    # All 91 pairs
    pair_rows = []
    for a, b in combinations(model_counts.keys(), 2):
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
    df_pairs.to_csv(out_dir / "J_bootstrap_paired_all.csv", index=False)

    # Highlighted subset
    mask = df_pairs.apply(
        lambda row: (
            (row["model_a"], row["model_b"]) in HIGHLIGHTED_PAIRS
            or (row["model_b"], row["model_a"]) in HIGHLIGHTED_PAIRS
        ),
        axis=1,
    )
    df_highlighted = df_pairs[mask].copy().reset_index(drop=True)
    # Multiple-comparison correction (p48a). The reported family is the set of
    # highlighted pairs (the comparisons the chapter actually discusses); we
    # adjust the per-comparison p-values with Holm and Bonferroni so the "Sig."
    # column in Table 13 reflects family-wise error control instead of 12
    # uncorrected tests. Marginal differences (e.g. GPT-4 Turbo vs GPT-4.1)
    # are expected not to survive — reinforcing the saturation reading.
    holm, bonf = _holm_bonferroni(df_highlighted["p_value"].tolist())
    df_highlighted["p_holm"] = holm
    df_highlighted["p_bonferroni"] = bonf
    df_highlighted["sig_holm_5pct"] = [p < 0.05 for p in holm]
    df_highlighted["sig_bonferroni_5pct"] = [p < 0.05 for p in bonf]
    df_highlighted["family_size"] = len(df_highlighted)
    df_highlighted.to_csv(out_dir / "J_bootstrap_paired_highlighted.csv", index=False)

    # Smallest significant diff
    sig = df_pairs[df_pairs["significant_95"]].copy()
    sig["abs_diff"] = sig["diff_f1"].abs()
    smallest = sig.nsmallest(1, "abs_diff").iloc[0].to_dict() if not sig.empty else None
    n_sig = int(df_pairs["significant_95"].sum())
    n_total = len(df_pairs)
    # Resampling unit (p32): the bootstrap resamples whole documents — each row
    # of the per-model DataFrame is one document (the unit of analysis). Expose
    # n so the text can state it explicitly.
    n_docs = len(next(iter(model_dfs.values()))) if model_dfs else 0

    summary_rows = [
        {"metric": "resampling_unit", "value": "document"},
        {"metric": "n_docs_resampled", "value": n_docs},
        {"metric": "n_total_pairs", "value": n_total},
        {"metric": "n_significant_5pct_uncorrected", "value": n_sig},
        {
            "metric": "highlighted_family_size",
            "value": int(len(df_highlighted)),
        },
        {
            "metric": "highlighted_n_sig_uncorrected",
            "value": int(df_highlighted["significant_95"].sum()),
        },
        {
            "metric": "highlighted_n_sig_holm",
            "value": int(df_highlighted["sig_holm_5pct"].sum()),
        },
        {
            "metric": "highlighted_n_sig_bonferroni",
            "value": int(df_highlighted["sig_bonferroni_5pct"].sum()),
        },
        {
            "metric": "smallest_significant_abs_diff",
            "value": float(smallest["abs_diff"]) if smallest else None,
        },
        {
            "metric": "smallest_significant_pair",
            "value": (
                f"{smallest['display_a']} vs {smallest['display_b']}" if smallest else None
            ),
        },
    ]
    pd.DataFrame(summary_rows).to_csv(out_dir / "J_bootstrap_summary.csv", index=False)

    logger.info(
        "wrote J_*.csv (n_pairs=%d, n_sig=%d, smallest_sig=%s)",
        n_total,
        n_sig,
        smallest["abs_diff"] if smallest else "—",
    )
    return {"df_ci": df_ci, "df_pairs": df_pairs, "summary_rows": summary_rows}


# ----- Block K: IoU threshold sensitivity ---------------------------------


# Sweep of IoU thresholds; 1.0 == exact-span match.
IOU_SWEEP = [0.3, 0.5, 0.7, 1.0]
_IOU_LABEL = {0.3: "0.3", 0.5: "0.5", 0.7: "0.7", 1.0: "exact"}


def block_k_iou_sensitivity(model_dfs: dict[str, pd.DataFrame], out_dir: Path) -> None:
    """Span F1 of every model at IoU ∈ {0.3, 0.5, 0.7} and exact match (p43a).

    Because entities are long, the canonical IoU ≥ 0.5 is permissive; this
    block shows whether the model ranking is stable as the threshold tightens.
    Span IoU is computed over character offsets, so no re-tokenisation is
    needed (see :func:`research.ner_metrics.span_metrics_multi_iou`).
    """
    rows: list[dict] = []
    for m, df in model_dfs.items():
        per_t = span_metrics_multi_iou(df, IOU_SWEEP)
        for t in IOU_SWEEP:
            flat = per_t[t]
            rows.append(
                {
                    "model": m,
                    "display": DISPLAY_NAMES.get(m, m),
                    "iou_threshold": _IOU_LABEL[t],
                    "span_f1": flat["span_f1"],
                    "span_f1_macro": flat["span_f1_macro"],
                    "span_precision": flat["span_precision"],
                    "span_recall": flat["span_recall"],
                }
            )
    df_long = pd.DataFrame(rows)
    df_long.to_csv(out_dir / "K_iou_sensitivity.csv", index=False)
    logger.info("wrote %s", out_dir / "K_iou_sensitivity.csv")

    # Wide pivot (model × threshold) on span F1 for quick reading.
    wide = df_long.pivot(index="display", columns="iou_threshold", values="span_f1")[
        [_IOU_LABEL[t] for t in IOU_SWEEP]
    ]
    wide.to_csv(out_dir / "K_iou_sensitivity_wide.csv")

    # Ranking stability: Spearman correlation of the per-threshold model
    # ranking against the canonical IoU=0.5 ranking.
    rank_corr_rows = []
    base = wide["0.5"]
    for t in IOU_SWEEP:
        col = _IOU_LABEL[t]
        rho = wide[col].corr(base, method="spearman")
        rank_corr_rows.append(
            {"iou_threshold": col, "spearman_vs_0.5": round(float(rho), 4)}
        )
    pd.DataFrame(rank_corr_rows).to_csv(
        out_dir / "K_iou_ranking_stability.csv", index=False
    )
    logger.info("wrote %s", out_dir / "K_iou_ranking_stability.csv")


# ----- Block L: metrics restricted to informative documents ---------------


def _keep_informative_only(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only documents carrying at least one gold entity (drops the 629
    empty documents that can only contribute false positives)."""
    return df[df["golden"].apply(len) > 0].reset_index(drop=True)


def block_l_informative_subset(model_dfs: dict[str, pd.DataFrame], out_dir: Path) -> None:
    """Re-score every model on the 232 informative documents only (p41b).

    Of the 861 documents, 629 carry no gold entity and contribute only false
    positives. Restricting to the 232 documents with ≥ 1 gold entity shows how
    much of each model's precision came from the volume of easy negatives
    rather than from accurate span delimitation.
    """
    rows: list[dict] = []
    for m, df in model_dfs.items():
        sub = _keep_informative_only(df)
        full = span_metrics_multi_iou(df, [0.5])[0.5]
        info = span_metrics_multi_iou(sub, [0.5])[0.5]
        rows.append(
            {
                "model": m,
                "display": DISPLAY_NAMES.get(m, m),
                "n_docs_full": len(df),
                "n_docs_informative": len(sub),
                "span_f1_full": full["span_f1"],
                "span_f1_informative": info["span_f1"],
                "delta_span_f1": info["span_f1"] - full["span_f1"],
                "span_precision_full": full["span_precision"],
                "span_precision_informative": info["span_precision"],
                "delta_span_precision": info["span_precision"] - full["span_precision"],
                "span_recall_full": full["span_recall"],
                "span_recall_informative": info["span_recall"],
            }
        )
    df_out = (
        pd.DataFrame(rows).sort_values("span_f1_informative", ascending=False).reset_index(drop=True)
    )
    df_out.to_csv(out_dir / "L_informative_subset.csv", index=False)
    logger.info("wrote %s", out_dir / "L_informative_subset.csv")


# ----- Block M: string->offset alignment failure rate ---------------------


def block_m_alignment_failures(model_dfs: dict[str, pd.DataFrame], out_dir: Path) -> None:
    """Per-model rate at which predicted span strings fail to align (p34).

    The LLM pipeline returns textual descriptions, not character offsets; they
    are located in the source by fuzzy matching (rapidfuzz partial_ratio,
    window 500 / step 100 / min_score 80). Strings that no window matches at
    that floor are silently dropped during scoring — so any non-trivial failure
    rate means real predictions never reach the metric. This block surfaces it.
    Only LLM result frames carry the raw ``pred``/``text``; supervised BIO
    frames are skipped.
    """
    rows: list[dict] = []
    for m, df in model_dfs.items():
        if "pred" not in df.columns or "text" not in df.columns:
            continue
        n_total = n_aligned = n_failed = 0
        for _, row in df.iterrows():
            t, a, f = count_alignment_failures(row)
            n_total += t
            n_aligned += a
            n_failed += f
        rows.append(
            {
                "model": m,
                "display": DISPLAY_NAMES.get(m, m),
                "n_pred_strings": n_total,
                "n_aligned": n_aligned,
                "n_failed": n_failed,
                "failure_rate": round(n_failed / n_total, 4) if n_total else 0.0,
            }
        )
    if not rows:
        logger.warning("no LLM frames with raw 'pred' for alignment audit")
        return
    df_out = (
        pd.DataFrame(rows).sort_values("failure_rate", ascending=False).reset_index(drop=True)
    )
    df_out.to_csv(out_dir / "M_alignment_failures.csv", index=False)
    logger.info("wrote %s", out_dir / "M_alignment_failures.csv")


# ----- Block E: cost-benefit (data unavailable) ---------------------------


def block_e_cost(model_dfs: dict[str, pd.DataFrame], out_dir: Path) -> None:
    """Token usage estimates from the source texts.

    We do **not** have logged input/output token counts from the API
    calls (predictions JSON store only the structured output, not the
    raw token counts). What we *can* compute deterministically is:

    - Mean characters per document (≈ 4 chars / token rule of thumb gives
      a rough estimate of input tokens).
    - Mean output JSON length (predictions Pydantic-serialised).

    Pricing (USD/1M tokens) must come from the user manually because it
    depends on (a) the snapshot the deployment served at execution time
    and (b) the provider tier. We emit a TEMPLATE CSV the user fills.
    """
    rows = []
    for m, df in model_dfs.items():
        if _is_supervised_model(m):
            continue
        if "text" not in df.columns:
            continue
        chars = df["text"].str.len()
        if "pred" in df.columns:
            pred_chars = df["pred"].apply(lambda x: len(json.dumps(x, ensure_ascii=False)) if x else 0)
        else:
            pred_chars = pd.Series([0] * len(df))
        rows.append(
            {
                "model": m,
                "display": DISPLAY_NAMES.get(m, m),
                "n_docs": len(df),
                "mean_input_chars": float(chars.mean()),
                "mean_output_chars": float(pred_chars.mean()),
                "approx_mean_input_tokens": float(chars.mean() / 4),
                "approx_mean_output_tokens": float(pred_chars.mean() / 4),
                "total_input_chars": int(chars.sum()),
                "total_output_chars": int(pred_chars.sum()),
                "input_cost_per_1M_USD": "",  # FILL MANUALLY
                "output_cost_per_1M_USD": "",  # FILL MANUALLY
                "estimated_total_cost_USD": "",  # =approx_*_tokens * cost_per_1M / 1e6
            }
        )
    pd.DataFrame(rows).to_csv(out_dir / "E_cost_template.csv", index=False)
    logger.info("wrote %s (pricing fields blank — fill manually)", out_dir / "E_cost_template.csv")


# ----- Master orchestration + REPORT.md -----------------------------------


def _md_table(df: pd.DataFrame, float_fmt: str = ".4f") -> str:
    return df.to_markdown(index=False, floatfmt=float_fmt)


def _pivot_md(
    long_df: pd.DataFrame,
    index_cols: list[str],
    column_col: str,
    value_col: str,
    *,
    float_fmt: str = ".4f",
) -> str:
    pivoted = long_df.pivot_table(
        index=index_cols, columns=column_col, values=value_col
    ).reset_index()
    return pivoted.to_markdown(index=False, floatfmt=float_fmt)


def write_report(out_dir: Path, j_summary: list[dict[str, Any]]) -> None:
    """Compose the master REPORT.md with every table rendered inline."""
    parts = ["# Capítulo 5 — Números reproduzíveis (gold corrigido)\n"]
    parts.append(
        "Documento auto-contido: todas as tabelas aparecem inline. Os CSVs "
        "ao lado deste arquivo são as fontes canônicas (uma por bloco), "
        "geradas por `research.release.chapter5_numbers`. Cada bloco abaixo "
        "corresponde a um item do checklist do capítulo.\n"
    )

    parts.append("## Pipeline de métricas (correções aplicadas)\n")
    parts.append(
        "Esta versão dos números incorpora as duas correções priorizadas no "
        "`METRICS_AUDIT.md`:\n\n"
        "1. **Matching pred↔gold bipartido por IoU descendente** "
        "(`research.ner_metrics.bipartite_greedy_match`). Cada predição casa com "
        "no máximo um gold e vice-versa, eliminando a divergência anterior "
        "entre `calculate_metrics` (que tinha `break` após o primeiro match) "
        "e o bootstrap (que contava todos os pares sobrepostos). Esta única "
        "função é agora a fonte para `calculate_metrics`, `evaluate_bio_results` "
        "e `compute_doc_level_counts` — `matched ≤ min(|pred|, |gold|)` por "
        "construção, e P/R sempre em [0, 1].\n\n"
        "2. **Token F1 de supervisionados via spaCy.** As predições BIO dos "
        "supervisionados (token-level `\\S+`) são reconvertidas para spans "
        "caractere-level via `bio_to_char_spans`, depois pontuadas por "
        "`calculate_metrics` (que tokeniza com `pt_core_news_sm`). Resultado: "
        "supervisionados e LLMs compartilham o mesmo tokenizador de avaliação, "
        "tornando o token F1 da Tabela C diretamente comparável entre paradigmas.\n"
    )
    # Comparison: pre-fix vs post-fix span F1 (LLM and supervised) and token F1 supervised.
    pre_span_f1 = {
        "gpt-4-turbo": 0.7599,
        "gpt-5.4-mini_few_shot": 0.7574,
        "gpt-4o": 0.7515,
        "gpt-5.4-nano_few_shot": 0.7490,
        "gpt-41-mini": 0.7345,
        "gpt-35": 0.7323,
        "gpt-41": 0.7264,
        "gemini-2.5-flash_few_shot": 0.7100,
        "neuralmind_bert-base-portuguese-cased__supervised": 0.6896,
        "deepseek-v3_few_shot": 0.6704,
        "rufimelo_Legal-BERTimbau-base__supervised": 0.6051,
        "neuralmind_bert-large-portuguese-cased__supervised": 0.6049,
        "bilstm-crf__supervised": 0.5926,
        "gpt-41-nano": 0.4424,
    }
    pre_token_f1_sup = {
        "neuralmind_bert-base-portuguese-cased__supervised": 0.7642,
        "neuralmind_bert-large-portuguese-cased__supervised": 0.6514,
        "rufimelo_Legal-BERTimbau-base__supervised": 0.6679,
        "bilstm-crf__supervised": 0.7191,
    }
    # Block J old summary numbers (pre-fix)
    pre_n_sig = 61
    pre_smallest = 0.0337
    df_main_for_compare = pd.read_csv(out_dir / "C_main_results.csv")
    rows = []
    for _, r in df_main_for_compare.iterrows():
        m = r["model"]
        if m not in pre_span_f1:
            continue
        rows.append(
            {
                "model": r["display"],
                "span F1 antes": pre_span_f1[m],
                "span F1 depois": float(r["span_f1"]),
                "Δ span F1": float(r["span_f1"]) - pre_span_f1[m],
            }
        )
    rows.sort(key=lambda x: -x["span F1 depois"])
    parts.append("### Comparativo antes × depois — Span F1 (14 modelos)\n")
    parts.append(
        pd.DataFrame(rows).to_markdown(index=False, floatfmt=".4f") + "\n"
    )
    sup_rows = []
    for _, r in df_main_for_compare.iterrows():
        m = r["model"]
        if m not in pre_token_f1_sup:
            continue
        sup_rows.append(
            {
                "model": r["display"],
                "token F1 antes (\\S+)": pre_token_f1_sup[m],
                "token F1 depois (spaCy)": float(r["token_f1"]),
                "Δ token F1": float(r["token_f1"]) - pre_token_f1_sup[m],
            }
        )
    parts.append(
        "### Comparativo antes × depois — Token F1 supervisionados (efeito da unificação do tokenizador)\n"
    )
    parts.append(
        pd.DataFrame(sup_rows).to_markdown(index=False, floatfmt=".4f") + "\n"
    )
    j_summary_df = pd.DataFrame(j_summary)
    n_sig_now = int(
        j_summary_df.loc[
            j_summary_df["metric"] == "n_significant_5pct_uncorrected", "value"
        ].iloc[0]
    )
    smallest_now = float(
        j_summary_df.loc[
            j_summary_df["metric"] == "smallest_significant_abs_diff", "value"
        ].iloc[0]
    )
    parts.append(
        "### Comparativo antes × depois — Significância (bootstrap pareado)\n"
    )
    parts.append(
        pd.DataFrame(
            [
                {"métrica": "Pares significativos a 5% (de 91)", "antes": pre_n_sig, "depois": n_sig_now, "Δ": n_sig_now - pre_n_sig},
                {"métrica": "Menor Δ detectável (significativo)", "antes": pre_smallest, "depois": smallest_now, "Δ": smallest_now - pre_smallest},
            ]
        ).to_markdown(index=False, floatfmt=".4f")
        + "\n"
    )

    # FC vs JSON Schema: span F1 antes/depois por (modelo, método)
    pre_fcjs_span_f1 = {
        ("gpt-3.5", "function_calling"): 0.7276,
        ("gpt-3.5", "json_schema"): 0.6734,
        ("gpt-4o", "function_calling"): 0.7500,
        ("gpt-4o", "json_schema"): 0.6715,
        ("gpt-5.4-mini", "function_calling"): 0.7566,
        ("gpt-5.4-mini", "json_schema"): 0.5650,
        ("gpt-5.4-nano", "function_calling"): 0.7482,
        ("gpt-5.4-nano", "json_schema"): 0.7087,
    }
    # FC-vs-JSON only exists for runs that ran that experiment (else archived under old_experiments).
    if (out_dir / "F_fc_vs_json_overall.csv").exists():
        df_fcjs_now = pd.read_csv(out_dir / "F_fc_vs_json_overall.csv")
        fcjs_rows = []
        for _, r in df_fcjs_now.iterrows():
            key = (r["model"], r["method"])
            if key not in pre_fcjs_span_f1:
                continue
            fcjs_rows.append(
                {
                    "model": r["model"],
                    "method": r["method"],
                    "span F1 antes": pre_fcjs_span_f1[key],
                    "span F1 depois": float(r["span_f1"]),
                    "Δ span F1": float(r["span_f1"]) - pre_fcjs_span_f1[key],
                }
            )
        parts.append(
            "### Comparativo antes × depois — FC vs JSON Schema (8 experimentos)\n"
        )
        parts.append(
            pd.DataFrame(fcjs_rows).to_markdown(index=False, floatfmt=".4f") + "\n"
        )

    # Prompting techniques: span F1 antes/depois por (modelo, técnica)
    pre_prompt_span_f1 = {
        ("gpt-5.4-nano", "cot"): 0.7613,
        ("gpt-5.4-mini", "few_shot"): 0.7566,
        ("gpt-5.4-nano", "few_shot"): 0.7482,
        ("gpt-5.4-mini", "cot"): 0.7348,
        ("gemini-2.5-flash", "cot"): 0.7346,
        ("gemini-2.5-flash", "two_stage"): 0.7253,
        ("gpt-5.4-nano", "two_stage"): 0.7196,
        ("gemini-2.5-flash", "few_shot"): 0.7093,
        ("gemini-2.5-flash", "dynamic_few_shot"): 0.7085,
        ("deepseek-v3", "two_stage"): 0.6954,
        ("gpt-5.4-nano", "dynamic_few_shot"): 0.6925,
        ("gpt-5.4-mini", "dynamic_few_shot"): 0.6800,
        ("gpt-5.4-mini", "two_stage"): 0.6798,
        ("deepseek-v3", "few_shot"): 0.6685,
        ("deepseek-v3", "dynamic_few_shot"): 0.5584,
        ("deepseek-v3", "cot"): 0.5250,
    }
    df_prompt_now = pd.read_csv(out_dir / "H_prompting_overall.csv")
    prompt_rows = []
    for _, r in df_prompt_now.iterrows():
        key = (r["model"], r["technique"])
        if key not in pre_prompt_span_f1:
            continue
        prompt_rows.append(
            {
                "model": r["model"],
                "technique": r["technique"],
                "span F1 antes": pre_prompt_span_f1[key],
                "span F1 depois": float(r["span_f1"]),
                "Δ span F1": float(r["span_f1"]) - pre_prompt_span_f1[key],
            }
        )
    prompt_rows.sort(key=lambda x: -x["span F1 depois"])
    parts.append(
        "### Comparativo antes × depois — Técnicas de prompting (16 experimentos)\n"
    )
    parts.append(
        pd.DataFrame(prompt_rows).to_markdown(index=False, floatfmt=".4f") + "\n"
    )

    # ----- A. Corpus -------------------------------------------------------
    parts.append("## A. Caracterização do corpus\n")
    parts.append(_md_table(pd.read_csv(out_dir / "A_corpus.csv")) + "\n")

    # ----- B. Cleanlab -----------------------------------------------------
    parts.append("## B. Auditoria Cleanlab\n")
    parts.append(
        "Dos **567** grupos com confiança ≥ 0,95 inspecionados (anotador único), "
        "apenas os marcados como `accept`/`custom` resultaram em alteração; os "
        "`reject` permaneceram no gold. As contagens de grupo abaixo respondem ao "
        "volume de intervenção (aceitos × rejeitados); as contagens de token são a "
        "granularidade fina dentro dos grupos decididos.\n"
    )
    parts.append("**Resumo das decisões (grupo) e contagens de tokens:**\n")
    parts.append(_md_table(pd.read_csv(out_dir / "B_cleanlab_summary.csv")) + "\n")
    parts.append("**Distribuição de `label_final` (rótulos para os quais os tokens foram migrados):**\n")
    parts.append(_md_table(pd.read_csv(out_dir / "B_label_final_counts.csv")) + "\n")
    parts.append("**Saldo líquido por classe:**\n")
    parts.append(_md_table(pd.read_csv(out_dir / "B_class_delta.csv")) + "\n")

    # ----- C. Main results -------------------------------------------------
    parts.append("## C. Resultados gerais (14 modelos × 6 métricas)\n")
    parts.append(_md_table(pd.read_csv(out_dir / "C_main_results.csv")) + "\n")
    parts.append("**Variabilidade entre folds dos supervisionados (itens 17–19):**\n")
    parts.append(_md_table(pd.read_csv(out_dir / "C_supervised_fold_std.csv")) + "\n")

    # Paradigm aggregate (LLM few-shot vs supervised)
    df_main = pd.read_csv(out_dir / "C_main_results.csv")
    df_main["paradigm"] = df_main["model"].apply(
        lambda m: "supervised" if m.endswith("__supervised") else "few-shot"
    )
    paradigm_agg = (
        df_main.groupby("paradigm")[["token_f1", "span_f1"]]
        .agg(["mean", "std", "min", "max"])
        .round(4)
        .reset_index()
    )
    parts.append("**Resumo por paradigma (média entre modelos):**\n")
    parts.append(paradigm_agg.to_markdown(index=False, floatfmt=".4f") + "\n")

    # ----- D. Heatmap ------------------------------------------------------
    parts.append("## D. F1 de Span por entidade × modelo\n")
    parts.append("**Heatmap (span F1 por modelo × entidade):**\n")
    parts.append(_md_table(pd.read_csv(out_dir / "D_heatmap_span_f1.csv")) + "\n")
    parts.append("**Detalhe completo (precision, recall, F1, matched/gold/pred):**\n")
    parts.append(_md_table(pd.read_csv(out_dir / "D_per_entity.csv")) + "\n")

    # ----- E. Cost ---------------------------------------------------------
    parts.append("## E. Custo-benefício\n")
    parts.append(
        "Os JSONs de predição não armazenam contagens de tokens da API; "
        "o template abaixo reporta caracteres médios e estimativa "
        "aproximada de tokens (≈ 4 chars/token), com colunas em branco "
        "para as tarifas USD/1M de cada provedor — preencher manualmente "
        "consultando o histórico de billing.\n"
    )
    parts.append(_md_table(pd.read_csv(out_dir / "E_cost_template.csv")) + "\n")

    # ----- F + G. FC vs JSON (only if this cycle ran that experiment) ------
    if (out_dir / "F_fc_vs_json_overall.csv").exists():
        parts.append("## F. Function calling vs JSON schema\n")
        parts.append("**Métricas overall:**\n")
        parts.append(_md_table(pd.read_csv(out_dir / "F_fc_vs_json_overall.csv")) + "\n")
        parts.append("**Δ por modelo (FC − JS):**\n")
        parts.append(_md_table(pd.read_csv(out_dir / "F_fc_vs_json_delta.csv")) + "\n")
    if (out_dir / "G_fc_vs_json_per_entity.csv").exists():
        parts.append("## G. FC vs JSON Schema por entidade\n")
        fcjs_per = pd.read_csv(out_dir / "G_fc_vs_json_per_entity.csv")
        parts.append("**Span F1 (modelo+método × entidade) — pivotado:**\n")
        parts.append(_pivot_md(fcjs_per, ["model", "method"], "label", "f1") + "\n")
        parts.append("**Span Precision (modelo+método × entidade):**\n")
        parts.append(_pivot_md(fcjs_per, ["model", "method"], "label", "precision") + "\n")
        parts.append("**Span Recall (modelo+método × entidade):**\n")
        parts.append(_pivot_md(fcjs_per, ["model", "method"], "label", "recall") + "\n")

    # ----- H. Prompting ---------------------------------------------------
    parts.append("## H. Técnicas de prompting\n")
    parts.append("**Métricas overall (modelo × técnica):**\n")
    parts.append(_md_table(pd.read_csv(out_dir / "H_prompting_overall.csv")) + "\n")
    parts.append("**Span F1 pivotado (modelo × técnica):**\n")
    h_overall = pd.read_csv(out_dir / "H_prompting_overall.csv")
    parts.append(
        _pivot_md(h_overall, ["model"], "technique", "span_f1") + "\n"
    )
    parts.append("**Resumo agregado por técnica (média ± std, min, max):**\n")
    parts.append(
        _md_table(pd.read_csv(out_dir / "H_prompting_technique_summary.csv")) + "\n"
    )
    parts.append(
        "**Por entidade — span F1 (modelo+técnica × entidade):** "
        "essencial para a narrativa de queda do DeepSeek-V3 com CoT, "
        "ganho do gpt-5.4-nano e do Gemini.\n"
    )
    h_per = pd.read_csv(out_dir / "H_prompting_per_entity.csv")
    parts.append(
        _pivot_md(h_per, ["model", "technique"], "label", "f1") + "\n"
    )
    parts.append("**Span Precision por entidade (mesmo eixo):**\n")
    parts.append(
        _pivot_md(h_per, ["model", "technique"], "label", "precision") + "\n"
    )
    parts.append("**Span Recall por entidade:**\n")
    parts.append(
        _pivot_md(h_per, ["model", "technique"], "label", "recall") + "\n"
    )

    # ----- I. Errors -------------------------------------------------------
    parts.append("## I. Análise de erros do melhor modelo\n")
    df_main = pd.read_csv(out_dir / "C_main_results.csv")
    best = df_main.iloc[0]["display"] if not df_main.empty else "—"
    parts.append(f"**Melhor modelo identificado por span F1: {best}.**\n")
    parts.append("**Contagens por tipo de erro:**\n")
    parts.append(_md_table(pd.read_csv(out_dir / "I_errors_by_kind.csv")) + "\n")
    parts.append("**Matriz rótulo × tipo de erro:**\n")
    parts.append(_md_table(pd.read_csv(out_dir / "I_errors_label_x_kind.csv")) + "\n")
    pair_path = out_dir / "I_type_error_pairs.csv"
    if pair_path.exists():
        parts.append("**Pares de tipo errado (gold → pred):**\n")
        parts.append(_md_table(pd.read_csv(pair_path)) + "\n")
    parts.append("**Histograma de IoU para erros de fronteira:**\n")
    parts.append(
        _md_table(pd.read_csv(out_dir / "I_boundary_iou_histogram.csv")) + "\n"
    )

    # ----- J. Significance -------------------------------------------------
    parts.append("## J. Significância estatística (bootstrap pareado)\n")
    parts.append("**Item 41 — N de reamostragens**: 10.000.\n")
    parts.append("**Item 42 — IC 95% por modelo:**\n")
    parts.append(_md_table(pd.read_csv(out_dir / "J_bootstrap_ci.csv")) + "\n")
    parts.append("**Itens 43–46 — Pares destacados:**\n")
    parts.append(
        _md_table(pd.read_csv(out_dir / "J_bootstrap_paired_highlighted.csv")) + "\n"
    )
    parts.append("**Itens 47–48 — Resumo:**\n")
    parts.append(_md_table(pd.DataFrame(j_summary)) + "\n")
    parts.append(
        "**p48a — Correção para múltiplas comparações.** A família reportada são "
        "os pares destacados acima; `p_holm`/`p_bonferroni` controlam o erro "
        "familiar (FWER) e `sig_holm_5pct` substitui a coluna 'Sig.' não corrigida "
        "da Tabela 13. Diferenças marginais tendem a não sobreviver, reforçando a "
        "leitura de saturação.\n"
    )
    parts.append("**Tabela completa dos 91 pares (ordenada por |Δ|):**\n")
    parts.append(_md_table(pd.read_csv(out_dir / "J_bootstrap_paired_all.csv")) + "\n")

    # ----- K. IoU sensitivity ---------------------------------------------
    parts.append("## K. Sensibilidade ao limiar de IoU (p43a)\n")
    parts.append(
        "Como as entidades são longas, IoU ≥ 0,5 é permissivo. Span F1 por modelo "
        "para IoU ∈ {0,3, 0,5, 0,7} e correspondência exata (1,0):\n"
    )
    parts.append(_md_table(pd.read_csv(out_dir / "K_iou_sensitivity_wide.csv")) + "\n")
    parts.append(
        "**Estabilidade do ranking** (Spearman do ranking de cada limiar vs. "
        "IoU = 0,5):\n"
    )
    parts.append(
        _md_table(pd.read_csv(out_dir / "K_iou_ranking_stability.csv")) + "\n"
    )

    # ----- L. Informative subset ------------------------------------------
    parts.append("## L. Métrica restrita aos documentos informativos (p41b)\n")
    parts.append(
        "Dos 861 documentos, 629 não têm entidade gold e só contribuem com falsos "
        "positivos. Restringindo aos 232 documentos com ≥ 1 entidade, vê-se quanto "
        "da precisão vinha do volume de negativos (queda de precisão = inflada "
        "pelos vazios):\n"
    )
    parts.append(_md_table(pd.read_csv(out_dir / "L_informative_subset.csv")) + "\n")

    # ----- M. Alignment failures ------------------------------------------
    m_path = out_dir / "M_alignment_failures.csv"
    if m_path.exists():
        parts.append("## M. Taxa de falha de alinhamento string→offset (p34)\n")
        parts.append(
            "As predições dos LLMs são strings (não offsets); são localizadas no "
            "texto-fonte por correspondência difusa (rapidfuzz `partial_ratio`, "
            "janela 500 / passo 100 / `min_score` 80). Strings que nenhuma janela "
            "casa nesse piso são descartadas silenciosamente na pontuação — a taxa "
            "de falha abaixo quantifica quantas predições nunca chegam à métrica:\n"
        )
        parts.append(_md_table(pd.read_csv(m_path)) + "\n")

    # ----- Nota: Canonical token F1 ---------------------------------------
    parts.append("## Nota — Token F1 do GPT-4-turbo (canônico)\n")
    row = df_main[df_main["model"] == "gpt-4-turbo"]
    if not row.empty:
        token_f1 = row.iloc[0]["token_f1"]
        parts.append(
            f"Valor canônico após correção: **{token_f1:.4f}** "
            f"(reportar como `0,{int(round(token_f1 * 10000)):04d}` ou "
            f"{token_f1*100:.2f}\\% conforme convenção da seção).\n"
        )
    (out_dir / "REPORT.md").write_text("\n".join(parts), encoding="utf-8")
    logger.info("wrote %s", out_dir / "REPORT.md")


def run() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    block_a_corpus(OUTPUT_ROOT)
    block_b_cleanlab(OUTPUT_ROOT)

    logger.info("loading model predictions from %s", CORRECTED_OUTPUT_DIR)
    model_dfs = load_all_models(CORRECTED_OUTPUT_DIR)

    metrics_by_model = block_cd_main_results(model_dfs, OUTPUT_ROOT)

    block_fg_structured(OUTPUT_ROOT)
    block_h_prompting(OUTPUT_ROOT)

    # Identify best model by point span F1
    best = max(
        ((m, mb["flat"]["span_f1"]) for m, mb in metrics_by_model.items()),
        key=lambda kv: kv[1],
    )[0]
    logger.info("best model by span F1: %s", best)
    block_i_errors(model_dfs, best, OUTPUT_ROOT)

    j = block_j_significance(model_dfs, OUTPUT_ROOT)
    block_k_iou_sensitivity(model_dfs, OUTPUT_ROOT)
    block_l_informative_subset(model_dfs, OUTPUT_ROOT)
    block_m_alignment_failures(model_dfs, OUTPUT_ROOT)
    block_e_cost(model_dfs, OUTPUT_ROOT)

    write_report(OUTPUT_ROOT, j["summary_rows"])


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
