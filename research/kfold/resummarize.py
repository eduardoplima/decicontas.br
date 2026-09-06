"""Recompute the k-fold summary metrics without retraining.

``cv_<model>.json`` stores two different things: the metrics as they were
computed at training time, and the raw out-of-fold predictions under
``fold_oof``. Only the metrics depend on the scoring protocol, so a change to
the protocol — the span unit, the gold standard — can be propagated by
rescoring the stored predictions.

Without this, ``C_supervised_fold_std.csv`` keeps reporting per-fold numbers
from the old protocol while ``C_main_results.csv`` moves to the new one, and
the reproducibility table quietly contradicts the main table.

Gold comes from the canonical release, never from the ``true_labels`` frozen
into the file: an encoder trained against a superseded gold must still be
scored against the current one.

    uv run python -m research.kfold.resummarize
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
from pathlib import Path
from typing import Any

from research.kfold.config import SUMMARY_DIR
from research.kfold.data import load_bio_samples
from research.kfold.metrics import evaluate_oof

logger = logging.getLogger(__name__)

METRIC_KEYS = ("span_f1", "token_f1", "span_precision", "span_recall")


def _aggregate(values: list[float]) -> dict[str, Any]:
    return {
        "mean": statistics.fmean(values),
        "std": statistics.stdev(values) if len(values) > 1 else 0.0,
        "values": values,
    }


def resummarize_one(path: Path, samples: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Rescore one ``cv_*.json`` in place; return the new summary."""
    summary = json.loads(path.read_text(encoding="utf-8"))
    folds = summary.get("fold_oof")
    if not folds:
        logger.warning("%s has no fold_oof; cannot rescore", path.name)
        return None

    fold_metrics: list[dict[str, Any]] = []
    for fold in folds:
        indices = fold["test_indices"]
        gold = [samples[i]["labels"] for i in indices]
        metrics = evaluate_oof(
            samples,
            indices,
            gold,
            fold["pred_labels"],
            model_name=f"{summary.get('model', path.stem)} fold {fold['fold']}",
        )
        fold_metrics.append(metrics)

    summary["fold_metrics"] = fold_metrics
    for key in METRIC_KEYS:
        values = [m[key] for m in fold_metrics]
        aggregated = _aggregate(values)
        if key in ("span_precision", "span_recall"):
            aggregated.pop("values")
        summary[key] = aggregated

    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def run(summary_dir: Path | None = None) -> dict[str, float]:
    summary_dir = summary_dir or SUMMARY_DIR
    samples = load_bio_samples()
    logger.info("loaded %d gold samples", len(samples))
    out: dict[str, float] = {}
    for path in sorted(Path(summary_dir).glob("cv_*.json")):
        summary = resummarize_one(path, samples)
        if summary is None:
            continue
        mean = summary["span_f1"]["mean"]
        std = summary["span_f1"]["std"]
        out[summary.get("model", path.stem)] = mean
        logger.info("%-46s span F1 = %.4f +/- %.4f", path.stem, mean, std)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-dir", type=Path, default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run(args.summary_dir)


if __name__ == "__main__":
    main()
