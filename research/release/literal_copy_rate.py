"""Literal-copy rate of the LLM span strings and the effect of the fuzzy aligner.

The LLM pipeline returns the *text* of each span (``descricao_*``), not its
offsets. :func:`research.ner_metrics.convert_pred_to_golden_format` locates
that string in the source document by fuzzy matching (rapidfuzz
``partial_ratio`` over a sliding window of 500 characters, step 100, floor 80),
anchors the start on the first occurrence of the string's first word inside
the winning window and estimates the end as ``start + len(string)``. A zero
alignment-failure rate (block M of ``evaluation_numbers``) therefore says
nothing about whether a model copies verbatim, nor whether the boundaries the
aligner returns are the ones the string actually occupies.

This module measures both, per model, over the 861 valid rows (few-shot
leakage rows dropped like every other evaluation script). For every
non-empty predicted string ``s`` in document ``t``:

* ``literal``: ``s`` is an exact substring of ``t`` (``literal_unique`` when
  it occurs once, ``literal_multi`` otherwise);
* ``fuzzy_only``: not a substring, but the production aligner still locates it;
* ``not_found``: neither — reconciles with ``n_failed`` in
  ``M_alignment_failures.csv``;
* for literal strings, whether the aligner returns the same ``(start, end)``
  as the first literal occurrence (``aligner_same_bounds``) or not
  (``aligner_diff_bounds``), and how many of the differences change the set
  of whitespace tokens the span covers (``aligner_diff_token_bounds``) — the
  unit in which the span metrics are computed, so only those can move a
  score.

Writes ``model_evaluation/M_literal_copy.csv`` (one row per LLM, ordered like
``M_alignment_failures.csv``) and ``M_literal_copy_rescore.csv``, which prices
the artefact: the same predictions re-scored with literal strings placed at
their own literal occurrence (everything else unchanged), at the canonical
IoU >= 0.5 and under exact token matching.

Run:
    uv run python -m research.release.literal_copy_rate
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import pandas as pd

from research.dataset_io import char_span_to_token_span, spans_to_token_units, token_offsets
from research.ner_metrics import (
    convert_pred_to_golden_format,
    count_alignment_failures,
    span_metrics_multi_iou,
)
from research.release import paths
from research.release.bootstrap_significance import DISPLAY_NAMES, MODELS
from research.release.evaluation_numbers import (
    _drop_fewshot,
    _is_supervised_model,
    _load_llm_df,
)

logger = logging.getLogger("research.release.literal_copy_rate")

OUTPUT_CSV = paths.EVALUATION_DIR / "M_literal_copy.csv"
RESCORE_CSV = paths.EVALUATION_DIR / "M_literal_copy_rescore.csv"

COLUMNS: list[str] = [
    "model",
    "n_strings",
    "literal",
    "literal_pct",
    "literal_unique",
    "literal_unique_pct",
    "fuzzy_only",
    "fuzzy_only_pct",
    "not_found",
    "not_found_pct",
    "aligner_same_bounds",
    "aligner_same_bounds_pct",
    "aligner_diff_bounds",
    "aligner_diff_token_bounds",
]


# ----- per-string classification ------------------------------------------


def iter_pred_strings(pred: Any) -> Iterator[str]:
    """Yield every non-empty predicted span string of a ``pred`` dict.

    Same walk and same skip rules as
    :func:`research.ner_metrics.count_alignment_failures`, so the totals
    reconcile with block M. Empty strings and ``None`` do not count.
    """
    if not isinstance(pred, dict):
        return
    for _label_type, spans in pred.items():
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
            yield span_text


def literal_occurrences(text: str, s: str) -> list[int]:
    """Start offsets of every (possibly overlapping) occurrence of ``s`` in ``text``."""
    if not s:
        return []
    out: list[int] = []
    pos = text.find(s)
    while pos >= 0:
        out.append(pos)
        pos = text.find(s, pos + 1)
    return out


def fuzzy_align(text: str, s: str, **aligner_kwargs: int) -> tuple[int, int] | None:
    """``(start, end)`` the *legacy* fuzzy-first aligner assigns to ``s`` in ``text``.

    Delegates to :func:`research.ner_metrics.convert_pred_to_golden_format`
    with ``exact_first=False`` and a one-string prediction, so window, step,
    threshold and the first-word anchoring are the real ones rather than a
    copy. This is the aligner the audit prices; production now tries the
    literal match first (:func:`research.ner_metrics.locate_span`). Returns
    ``None`` when no window reaches the floor (the string would be dropped
    before scoring).
    """
    located = convert_pred_to_golden_format(
        {"text": text, "pred": {"multas": [{"descricao_multa": s}]}},
        exact_first=False,
        **aligner_kwargs,
    )
    if not located:
        return None
    return int(located[0]["start"]), int(located[0]["end"])


def classify_string(text: str, s: str) -> dict[str, Any]:
    """Classify one predicted string against its source document.

    Keys:

    * ``literal`` / ``literal_unique`` / ``literal_multi`` / ``fuzzy_only`` /
      ``not_found`` — mutually exclusive outcome flags (``literal_unique`` and
      ``literal_multi`` partition ``literal``);
    * ``n_occurrences`` — literal occurrences of ``s`` in ``text``;
    * ``literal_bounds`` — ``(start, end)`` of the first literal occurrence, or
      ``None``;
    * ``aligner_bounds`` — what the fuzzy aligner returns, or ``None``;
    * ``aligner_same_bounds`` — for literal strings, whether the aligner lands
      exactly on the first literal occurrence (``None`` otherwise);
    * ``aligner_other_occurrence`` — for literal strings, whether the aligner
      landed on a *different* literal occurrence instead (ambiguity, not an
      aligner artefact);
    * ``aligner_diff_token_bounds`` — for literal strings whose bounds differ,
      whether the whitespace-token range differs too (the scoring unit).
    """
    occurrences = literal_occurrences(text, s)
    aligner = fuzzy_align(text, s)
    literal = bool(occurrences)
    out: dict[str, Any] = {
        "literal": literal,
        "n_occurrences": len(occurrences),
        "literal_unique": len(occurrences) == 1,
        "literal_multi": len(occurrences) > 1,
        "fuzzy_only": (not literal) and aligner is not None,
        "not_found": (not literal) and aligner is None,
        "literal_bounds": (occurrences[0], occurrences[0] + len(s)) if literal else None,
        "aligner_bounds": aligner,
        "aligner_same_bounds": None,
        "aligner_other_occurrence": None,
        "aligner_diff_token_bounds": None,
    }
    if not literal:
        return out

    first = out["literal_bounds"]
    same = aligner == first
    out["aligner_same_bounds"] = same
    # The aligner's end is always start + len(s), so matching the start of
    # another occurrence means it landed exactly on that occurrence.
    out["aligner_other_occurrence"] = (
        (not same) and aligner is not None and aligner[0] in occurrences[1:]
    )
    if same:
        out["aligner_diff_token_bounds"] = False
    else:
        offsets = token_offsets(text)
        literal_tokens = char_span_to_token_span(first[0], first[1], offsets)
        aligner_tokens = (
            char_span_to_token_span(aligner[0], aligner[1], offsets)
            if aligner is not None
            else None
        )
        out["aligner_diff_token_bounds"] = literal_tokens != aligner_tokens
    return out


# ----- per-model aggregation ----------------------------------------------


def _pct(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 2) if denominator else 0.0


def summarise(model: str, classifications: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate :func:`classify_string` outputs into one CSV row."""
    rows = list(classifications)
    n = len(rows)
    literal = sum(1 for r in rows if r["literal"])
    literal_unique = sum(1 for r in rows if r["literal_unique"])
    fuzzy_only = sum(1 for r in rows if r["fuzzy_only"])
    not_found = sum(1 for r in rows if r["not_found"])
    same = sum(1 for r in rows if r["aligner_same_bounds"])
    diff_tokens = sum(1 for r in rows if r["aligner_diff_token_bounds"])
    assert literal + fuzzy_only + not_found == n
    return {
        "model": model,
        "n_strings": n,
        "literal": literal,
        "literal_pct": _pct(literal, n),
        "literal_unique": literal_unique,
        "literal_unique_pct": _pct(literal_unique, n),
        "fuzzy_only": fuzzy_only,
        "fuzzy_only_pct": _pct(fuzzy_only, n),
        "not_found": not_found,
        "not_found_pct": _pct(not_found, n),
        "aligner_same_bounds": same,
        "aligner_same_bounds_pct": _pct(same, literal),
        "aligner_diff_bounds": literal - same,
        "aligner_diff_token_bounds": diff_tokens,
    }


def classify_frame(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Classify every predicted string of an LLM result frame (``text`` + ``pred``)."""
    out: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        text = row["text"] or ""
        for s in iter_pred_strings(row["pred"]):
            out.append(classify_string(text, s))
    return out


def summarise_frame(model: str, df: pd.DataFrame) -> dict[str, Any]:
    """One CSV row for a model, reconciled against the block-M counter.

    ``n_strings`` must equal the total that
    :func:`research.ner_metrics.count_alignment_failures` sees and
    ``not_found`` must equal its failure count; both use the same aligner, so
    a mismatch means the walk over ``pred`` diverged and the row is not
    comparable with ``M_alignment_failures.csv``.
    """
    summary = summarise(model, classify_frame(df))
    n_total = n_failed = 0
    for _, row in df.iterrows():
        total, _aligned, failed = count_alignment_failures(row)
        n_total += total
        n_failed += failed
    if (summary["n_strings"], summary["not_found"]) != (n_total, n_failed):
        raise RuntimeError(
            f"{model}: literal-copy audit does not reconcile with block M "
            f"(n_strings {summary['n_strings']} vs {n_total}; "
            f"not_found {summary['not_found']} vs {n_failed})"
        )
    return summary


def load_llm_frames(input_dir: Path = paths.OUTPUT_CORRECTED_DIR) -> dict[str, pd.DataFrame]:
    """The nine LLM result frames, loaded and few-shot-filtered like block M."""
    out: dict[str, pd.DataFrame] = {}
    for m in MODELS:
        if _is_supervised_model(m):
            continue
        path = input_dir / f"models_results_decicontas_{m}.json"
        if not path.exists():
            logger.warning("missing %s", path)
            continue
        out[m] = _drop_fewshot(_load_llm_df(path))
    return out


def build_table(model_dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Per-model table, ordered like ``M_alignment_failures.csv``.

    Block M sorts by failure rate, descending, with ties kept in ``MODELS``
    order; ``not_found`` reconciles with that failure count, so sorting on it
    reproduces the same order.
    """
    rows = [summarise_frame(m, df) for m, df in model_dfs.items()]
    df = pd.DataFrame(rows, columns=COLUMNS)
    rate = df["not_found"] / df["n_strings"].where(df["n_strings"] > 0, 1)
    order = rate.sort_values(ascending=False, kind="stable").index
    return df.loc[order].reset_index(drop=True)


# ----- counterfactual: literal-first alignment ----------------------------


def literal_first_spans(row: pd.Series | dict[str, Any]) -> list[dict[str, Any]]:
    """``pred_as_golden`` (character units) under the exact-first aligner.

    This is the production aligner since the advisor review
    (:func:`research.ner_metrics.locate_span`): a string that is an exact
    substring of the document is placed at its literal occurrence (the one
    nearest the legacy fuzzy anchor when it repeats); only the others go
    through the fuzzy search, and strings it cannot place are dropped, so the
    only difference from the legacy spans is the artefact being priced.
    """
    return convert_pred_to_golden_format(row, exact_first=True)


def rescore_literal_first(model_dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Span F1 under the legacy fuzzy-first aligner vs. the exact-first aligner.

    Both scorings are rebuilt here from the raw ``pred`` strings: the
    ``*_aligner`` columns use the legacy aligner (``exact_first=False``, the
    one the dissertation used before the advisor review) and the
    ``*_literal_first`` columns use :func:`literal_first_spans`, i.e. the
    production aligner, so they reproduce ``K_iou_sensitivity.csv``. Macro F1
    is the dissertation's primary aggregation; micro is kept alongside.
    ``exact`` is IoU = 1 on the token grid, as in block K.
    """
    rows: list[dict[str, Any]] = []
    for m, df in model_dfs.items():
        legacy_pred: list[list[dict]] = []
        cf_pred: list[list[dict]] = []
        for _, row in df.iterrows():
            offsets = token_offsets(row["text"] or "")
            legacy_spans = convert_pred_to_golden_format(row, exact_first=False)
            legacy_pred.append(spans_to_token_units(offsets, legacy_spans)[0])
            cf_pred.append(spans_to_token_units(offsets, literal_first_spans(row))[0])
        current = span_metrics_multi_iou(df.assign(pred_as_golden=legacy_pred), [0.5, 1.0])
        counterfactual = span_metrics_multi_iou(df.assign(pred_as_golden=cf_pred), [0.5, 1.0])
        rows.append(
            {
                "model": m,
                "display": DISPLAY_NAMES.get(m, m),
                "span_f1_macro_aligner": round(current[0.5]["span_f1_macro"], 4),
                "span_f1_macro_literal_first": round(counterfactual[0.5]["span_f1_macro"], 4),
                "exact_f1_macro_aligner": round(current[1.0]["span_f1_macro"], 4),
                "exact_f1_macro_literal_first": round(counterfactual[1.0]["span_f1_macro"], 4),
                "span_f1_micro_aligner": round(current[0.5]["span_f1"], 4),
                "span_f1_micro_literal_first": round(counterfactual[0.5]["span_f1"], 4),
                "exact_f1_micro_aligner": round(current[1.0]["span_f1"], 4),
                "exact_f1_micro_literal_first": round(counterfactual[1.0]["span_f1"], 4),
            }
        )
    out = pd.DataFrame(rows)
    for scope in ("span_f1_macro", "exact_f1_macro", "span_f1_micro", "exact_f1_micro"):
        out[f"{scope}_delta"] = (
            out[f"{scope}_literal_first"] - out[f"{scope}_aligner"]
        ).round(4)
    return out


def run(out_path: Path = OUTPUT_CSV, rescore_path: Path = RESCORE_CSV) -> pd.DataFrame:
    model_dfs = load_llm_frames()
    table = build_table(model_dfs)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out_path, index=False)
    logger.info("wrote %s", out_path)
    shown = table.assign(display=table["model"].map(lambda m: DISPLAY_NAMES.get(m, m)))
    print(
        shown[
            [
                "display",
                "n_strings",
                "literal_pct",
                "literal_unique_pct",
                "fuzzy_only_pct",
                "not_found_pct",
                "aligner_same_bounds_pct",
                "aligner_diff_bounds",
                "aligner_diff_token_bounds",
            ]
        ].to_string(index=False)
    )

    rescore = rescore_literal_first({m: model_dfs[m] for m in table["model"]})
    rescore.to_csv(rescore_path, index=False)
    logger.info("wrote %s", rescore_path)
    print(
        rescore[
            [
                "display",
                "span_f1_macro_aligner",
                "span_f1_macro_literal_first",
                "span_f1_macro_delta",
                "exact_f1_macro_aligner",
                "exact_f1_macro_literal_first",
                "exact_f1_macro_delta",
            ]
        ].to_string(index=False)
    )
    return table


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
