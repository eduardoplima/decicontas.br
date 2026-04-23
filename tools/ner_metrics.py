"""Shared NER metric utilities used across the ``ner_*.ipynb`` notebooks.

Every notebook that evaluates TCE/RN NER predictions previously carried its
own copy of these functions (IoU scoring, BIO <-> span conversion, the
spaCy-based token/span metric pipeline). They are collected here so the
notebooks can `from tools.ner_metrics import ...` instead of redefining them.

The module has no side effects at import time: spaCy is only loaded inside
:func:`calculate_metrics` when it is called.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd
import spacy
from rapidfuzz import fuzz
from sklearn.metrics import classification_report, precision_recall_fscore_support

DICT_LABELS: dict[str, str] = {
    "obrigacoes": "OBRIGACAO",
    "recomendacoes": "RECOMENDACAO",
    "ressarcimentos": "RESSARCIMENTO",
    "multas": "MULTA",
}

ENTITY_LABELS: list[str] = ["MULTA", "OBRIGACAO", "RECOMENDACAO", "RESSARCIMENTO"]


def _strip_bio(tag: str | None) -> str:
    """Drop the BIO prefix from a tag (`B-MULTA` -> `MULTA`, `O` -> `O`)."""
    if tag == "O" or tag is None:
        return "O"
    parts = tag.split("-", 1)
    return parts[1] if len(parts) == 2 else parts[0]


def compute_iou_score(
    span_a: tuple[int, int],
    span_b: tuple[int, int],
    label_a: str,
    label_b: str,
    threshold: float = 0.5,
) -> float:
    """Return 1.0 when spans overlap with IoU >= threshold and share labels."""
    s_a, e_a = span_a
    s_b, e_b = span_b
    if e_a <= s_b or e_b <= s_a:
        return 0.0
    intersection = max(0, min(e_a, e_b) - max(s_a, s_b))
    union = max(e_a, e_b) - min(s_a, s_b)
    iou = intersection / union if union > 0 else 0.0
    return 1.0 if (iou >= threshold and label_a == label_b) else 0.0


def extract_spans_from_bio(tags: list[str]) -> list[tuple[int, int, str]]:
    """Group a BIO tag sequence into `(start_idx, end_idx, label)` tuples.

    Indices are token positions (half-open), not character offsets.
    """
    spans: list[tuple[int, int, str]] = []
    start: int | None = None
    label: str | None = None
    for j, tag in enumerate(tags):
        if tag.startswith("B-"):
            if start is not None:
                spans.append((start, j, label))  # type: ignore[arg-type]
            label, start = tag[2:], j
        elif tag.startswith("I-") and start is not None and tag[2:] == label:
            continue
        else:
            if start is not None:
                spans.append((start, j, label))  # type: ignore[arg-type]
                start, label = None, None
    if start is not None:
        spans.append((start, len(tags), label))  # type: ignore[arg-type]
    return spans


def bio_to_char_spans(
    bio_tags: list[str],
    token_offsets: list[dict[str, int]],
) -> list[dict[str, Any]]:
    """Turn a BIO sequence + token char offsets into `golden`-style span dicts."""
    spans: list[dict[str, Any]] = []
    current_label: str | None = None
    current_start: int | None = None
    current_end: int | None = None
    min_len = min(len(bio_tags), len(token_offsets))

    for i in range(min_len):
        tag = bio_tags[i]
        tok = token_offsets[i]
        if tag.startswith("B-"):
            if current_label is not None:
                spans.append(
                    {"start": current_start, "end": current_end, "labels": [current_label]}
                )
            current_label = tag[2:]
            current_start = tok["start"]
            current_end = tok["end"]
        elif tag.startswith("I-") and current_label is not None and tag[2:] == current_label:
            current_end = tok["end"]
        else:
            if current_label is not None:
                spans.append(
                    {"start": current_start, "end": current_end, "labels": [current_label]}
                )
                current_label = None

    if current_label is not None:
        spans.append({"start": current_start, "end": current_end, "labels": [current_label]})
    return spans


def convert_pred_to_golden_format(
    row: pd.Series | dict[str, Any],
    window_size: int = 500,
    step_size: int = 100,
    min_score: int = 80,
) -> list[dict[str, Any]]:
    """Locate predicted NER span strings inside the source text with fuzzy matching.

    Produces entries in the same shape as Label Studio's `golden` field:
    `{"start", "end", "text", "labels"}`.
    """
    pred_spans: list[dict[str, Any]] = []
    text = row["text"]
    pred = row["pred"]
    for label_type, spans in pred.items():
        for span in spans or []:
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
            for start in range(0, len(text), step_size):
                window = text[start : start + window_size]
                score = fuzz.partial_ratio(span_text, window)
                if score > best_score and score >= min_score:
                    best_score = score
                    best_pos = (
                        start + window.find(span_text.split()[0]) if span_text.split() else start
                    )
                    best_substring = span_text
            if best_score >= min_score and best_pos >= 0:
                pred_spans.append(
                    {
                        "start": best_pos,
                        "end": best_pos + len(best_substring),
                        "text": best_substring,
                        "labels": [DICT_LABELS[label_type]],
                    }
                )
    return pred_spans


def _span_metric_totals(
    label_metrics: dict[str, dict[str, int]],
) -> tuple[float, float, float, dict[str, dict[str, float | int]]]:
    total_gold = sum(v["total_gold"] for v in label_metrics.values())
    total_pred = sum(v["total_pred"] for v in label_metrics.values())
    total_matched = sum(v["matched"] for v in label_metrics.values())
    iou_p = total_matched / total_pred if total_pred else 0.0
    iou_r = total_matched / total_gold if total_gold else 0.0
    iou_f1 = (2 * iou_p * iou_r / (iou_p + iou_r)) if (iou_p + iou_r) else 0.0

    per_label: dict[str, dict[str, float | int]] = {}
    for lab, m in label_metrics.items():
        pr = m["matched"] / m["total_pred"] if m["total_pred"] else 0.0
        rc = m["matched"] / m["total_gold"] if m["total_gold"] else 0.0
        f1 = (2 * pr * rc / (pr + rc)) if (pr + rc) else 0.0
        per_label[lab] = {
            "precision": pr,
            "recall": rc,
            "f1": f1,
            "matched": m["matched"],
            "total_pred": m["total_pred"],
            "total_gold": m["total_gold"],
        }
    return iou_p, iou_r, iou_f1, per_label


def calculate_metrics(
    df: pd.DataFrame,
    iou_threshold: float = 0.5,
    spacy_model: str = "pt_core_news_sm",
    verbose: bool = False,
) -> dict[str, Any]:
    """Compute token-level and span-level (IoU) metrics over a prediction DataFrame.

    Expects `df` to carry:
      - `text`: document source
      - `golden`: list of `{start, end, labels}` gold spans
      - `pred_as_golden`: list of `{start, end, labels}` predicted spans
    """
    nlp = spacy.load(spacy_model)
    y_true_tokens: list[list[str]] = []
    y_pred_tokens: list[list[str]] = []
    label_metrics: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total_gold": 0, "total_pred": 0, "matched": 0}
    )

    for _, row in df.iterrows():
        text = row["text"]
        doc = nlp(text)
        true_bio = ["O"] * len(doc)
        pred_bio = ["O"] * len(doc)

        for ann in row.get("golden", []):
            start, end, label = ann["start"], ann["end"], ann["labels"][0]
            cs = doc.char_span(start, end, label=label, alignment_mode="expand")
            if cs:
                for j, tok in enumerate(cs):
                    true_bio[tok.i] = f"B-{label}" if j == 0 else f"I-{label}"

        for ann in row.get("pred_as_golden", []):
            start, end, label = ann["start"], ann["end"], ann["labels"][0]
            cs = doc.char_span(start, end, label=label, alignment_mode="expand")
            if cs:
                for j, tok in enumerate(cs):
                    pred_bio[tok.i] = f"B-{label}" if j == 0 else f"I-{label}"

        y_true_tokens.append([_strip_bio(t) for t in true_bio])
        y_pred_tokens.append([_strip_bio(t) for t in pred_bio])

        gold_spans = [(a["start"], a["end"], a["labels"][0]) for a in row.get("golden", [])]
        pred_spans = [
            (a["start"], a["end"], a["labels"][0]) for a in row.get("pred_as_golden", [])
        ]
        for _, _, lab in gold_spans:
            label_metrics[lab]["total_gold"] += 1
        for _, _, lab in pred_spans:
            label_metrics[lab]["total_pred"] += 1

        matched_pairs: set[tuple[int, int]] = set()
        for pi, p in enumerate(pred_spans):
            for gi, g in enumerate(gold_spans):
                if (pi, gi) in matched_pairs:
                    continue
                if compute_iou_score(
                    (p[0], p[1]), (g[0], g[1]), p[2], g[2], threshold=iou_threshold
                ) > 0:
                    label_metrics[p[2]]["matched"] += 1
                    matched_pairs.add((pi, gi))
                    break

    flat_true: list[str] = []
    flat_pred: list[str] = []
    for t_seq, p_seq in zip(y_true_tokens, y_pred_tokens):
        for t, p in zip(t_seq, p_seq):
            if t != "O" or p != "O":
                flat_true.append(t)
                flat_pred.append(p)

    if not flat_true:
        token_prec = token_rec = token_f1 = 0.0
        labels_sorted: list[str] = []
        per_label: dict[str, dict[str, float | int]] = {}
        token_report = "No entity tokens to evaluate."
    else:
        labels_sorted = sorted({lab for lab in flat_true + flat_pred if lab != "O"})
        token_prec, token_rec, token_f1, _ = precision_recall_fscore_support(
            flat_true, flat_pred, labels=labels_sorted, average="micro", zero_division=0
        )
        prec_l, rec_l, f1_l, sup_l = precision_recall_fscore_support(
            flat_true, flat_pred, labels=labels_sorted, average=None, zero_division=0
        )
        per_label = {
            lab: {"precision": float(p), "recall": float(r), "f1": float(f), "support": int(s)}
            for lab, p, r, f, s in zip(labels_sorted, prec_l, rec_l, f1_l, sup_l)
        }
        token_report = classification_report(
            flat_true, flat_pred, labels=labels_sorted, zero_division=0
        )

    iou_prec, iou_rec, iou_f1, iou_per_label = _span_metric_totals(label_metrics)

    raw: dict[str, Any] = {
        "token_flat": {
            "precision": float(token_prec),
            "recall": float(token_rec),
            "f1": float(token_f1),
            "per_label": per_label,
            "labels": labels_sorted,
        },
        "iou_agg": {"precision": iou_prec, "recall": iou_rec, "f1": iou_f1},
        "iou_per_label": iou_per_label,
    }

    if verbose:
        print("====== TOKEN-LEVEL (IGNORANDO B-/I-, SEM 'O') ======")
        print(f"Precision: {token_prec:.4f}")
        print(f"Recall:    {token_rec:.4f}")
        print(f"F1:        {token_f1:.4f}")
        print(token_report)
        print("====== SPAN-LEVEL IOU>=0.5 (AGREGADO) ======")
        print(f"Precision: {iou_prec:.4f}")
        print(f"Recall:    {iou_rec:.4f}")
        print(f"F1:        {iou_f1:.4f}")
        print("====== SPAN-LEVEL IOU POR RÓTULO ======")
        for lab, m in iou_per_label.items():
            print(
                f"{lab}: P={m['precision']:.4f} R={m['recall']:.4f} F1={m['f1']:.4f} "
                f"(matched={m['matched']}, pred={m['total_pred']}, gold={m['total_gold']})"
            )

    return raw


def flatten_metrics(raw: dict[str, Any]) -> dict[str, float]:
    """Collapse the nested result from :func:`calculate_metrics` into a flat dict.

    Keys: `token_precision`, `token_recall`, `token_f1`, `span_precision`,
    `span_recall`, `span_f1`, and per-label `f1_<LABEL>` / `precision_<LABEL>` /
    `recall_<LABEL>` entries. Handy for `wandb.log` and per-row DataFrame rows.
    """
    metrics: dict[str, float] = {
        "token_precision": float(raw["token_flat"]["precision"]),
        "token_recall": float(raw["token_flat"]["recall"]),
        "token_f1": float(raw["token_flat"]["f1"]),
        "span_precision": float(raw["iou_agg"]["precision"]),
        "span_recall": float(raw["iou_agg"]["recall"]),
        "span_f1": float(raw["iou_agg"]["f1"]),
    }
    for label, vals in raw["iou_per_label"].items():
        metrics[f"f1_{label}"] = float(vals["f1"])
        metrics[f"precision_{label}"] = float(vals["precision"])
        metrics[f"recall_{label}"] = float(vals["recall"])
    return metrics


def evaluate_results(df_results: pd.DataFrame, return_raw: bool = False):
    """End-to-end LLM evaluation: run conversion, compute metrics, flatten.

    By default returns the flat metrics dict. Pass `return_raw=True` to also
    get the nested `raw` dict from :func:`calculate_metrics` (used by
    ``ner_results.ipynb``, which persists it for later analysis).
    """
    df_results["pred_as_golden"] = df_results.apply(
        lambda row: convert_pred_to_golden_format(
            row, window_size=500, step_size=100, min_score=80
        ),
        axis=1,
    )
    raw = calculate_metrics(df_results, iou_threshold=0.5)
    metrics = flatten_metrics(raw)
    return (metrics, raw) if return_raw else metrics


evaluate_llm_results = evaluate_results


def evaluate_bio_results(data: dict[str, list[list[str]]]) -> dict[str, float]:
    """Flat metrics from paired BIO sequences (`true_labels`, `pred_labels`)."""
    gold_seqs = data["true_labels"]
    pred_seqs = data["pred_labels"]

    flat_true: list[str] = []
    flat_pred: list[str] = []
    label_metrics: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total_gold": 0, "total_pred": 0, "matched": 0}
    )

    for gold_tags, pred_tags in zip(gold_seqs, pred_seqs):
        min_len = min(len(gold_tags), len(pred_tags))
        gt = gold_tags[:min_len]
        pt = pred_tags[:min_len]

        for t, p in zip(gt, pt):
            tl, pl = _strip_bio(t), _strip_bio(p)
            if tl != "O" or pl != "O":
                flat_true.append(tl)
                flat_pred.append(pl)

        g_spans = extract_spans_from_bio(gt)
        p_spans = extract_spans_from_bio(pt)
        for _, _, lab in g_spans:
            label_metrics[lab]["total_gold"] += 1
        for _, _, lab in p_spans:
            label_metrics[lab]["total_pred"] += 1
        matched: set[tuple[int, int]] = set()
        for pi, p in enumerate(p_spans):
            for gi, g in enumerate(g_spans):
                if (pi, gi) in matched:
                    continue
                if compute_iou_score(
                    (p[0], p[1]), (g[0], g[1]), p[2], g[2], threshold=0.5
                ) > 0:
                    label_metrics[p[2]]["matched"] += 1
                    matched.add((pi, gi))
                    break

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
    return flatten_metrics(raw)


def full_evaluation(
    bio_data: list[dict[str, Any]],
    oof_true: list[list[str]],
    oof_pred: list[list[str]],
    model_name: str = "Model",
) -> dict[str, Any]:
    """Run the spaCy metric pipeline on out-of-fold BIO predictions.

    Converts BIO + char offsets back to char spans, builds a DataFrame, calls
    :func:`calculate_metrics`, prints a short summary, and returns a dict in
    the shape the supervised notebooks expect.
    """
    rows = []
    for i, sample in enumerate(bio_data):
        offsets = sample["token_offsets"]
        golden = bio_to_char_spans(oof_true[i], offsets)
        pred_as_golden = bio_to_char_spans(oof_pred[i], offsets)
        rows.append(
            {
                "text": sample["text"],
                "golden": golden,
                "pred_as_golden": pred_as_golden,
            }
        )

    df = pd.DataFrame(rows)
    raw = calculate_metrics(df, iou_threshold=0.5)

    print(f"\n{'=' * 60}")
    print(f"  {model_name} (avaliação via spaCy)")
    print(f"{'=' * 60}")
    print(f"Token-level F1 (micro, excl. O): {raw['token_flat']['f1']:.4f}")
    print(f"  Precision: {raw['token_flat']['precision']:.4f}")
    print(f"  Recall:    {raw['token_flat']['recall']:.4f}")
    print(f"Span-level F1 (IoU >= 0.5):      {raw['iou_agg']['f1']:.4f}")
    print(f"  Precision: {raw['iou_agg']['precision']:.4f}")
    print(f"  Recall:    {raw['iou_agg']['recall']:.4f}")
    print("\nPer-entity Span F1:")
    for ent, vals in sorted(raw["iou_per_label"].items()):
        print(
            f"  {ent}: F1={vals['f1']:.4f} P={vals['precision']:.4f} R={vals['recall']:.4f}"
            f" (matched={vals['matched']}, pred={vals['total_pred']}, gold={vals['total_gold']})"
        )

    per_entity_f1 = {k: v["f1"] for k, v in raw["iou_per_label"].items()}
    return {
        "model": model_name,
        "token_f1": raw["token_flat"]["f1"],
        "token_precision": raw["token_flat"]["precision"],
        "token_recall": raw["token_flat"]["recall"],
        "span_f1": raw["iou_agg"]["f1"],
        "span_precision": raw["iou_agg"]["precision"],
        "span_recall": raw["iou_agg"]["recall"],
        "per_entity_f1": per_entity_f1,
        "raw": raw,
    }


def print_metrics_report(raw: dict[str, Any]) -> None:
    """Print the same human-readable block that old `calculate_metrics` emitted."""
    tf = raw["token_flat"]
    print("====== TOKEN-LEVEL (IGNORANDO B-/I-, SEM 'O') ======")
    print(f"Precision: {tf['precision']:.4f}")
    print(f"Recall:    {tf['recall']:.4f}")
    print(f"F1:        {tf['f1']:.4f}")
    ia = raw["iou_agg"]
    print("====== SPAN-LEVEL IOU>=0.5 (AGREGADO) ======")
    print(f"Precision: {ia['precision']:.4f}")
    print(f"Recall:    {ia['recall']:.4f}")
    print(f"F1:        {ia['f1']:.4f}")
    print("====== SPAN-LEVEL IOU POR RÓTULO ======")
    for lab, m in raw["iou_per_label"].items():
        print(
            f"{lab}: P={m['precision']:.4f} R={m['recall']:.4f} F1={m['f1']:.4f} "
            f"(matched={m['matched']}, pred={m['total_pred']}, gold={m['total_gold']})"
        )
