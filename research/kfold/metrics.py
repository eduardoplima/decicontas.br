"""Thin wrapper around :func:`research.ner_metrics.full_evaluation`.

We compute span F1 (IoU >= 0.5) and per-entity span F1 over a set of out-of-fold
BIO predictions, against the same spaCy-based pipeline used for the LLMs (so the
two paradigms are directly comparable).
"""

from __future__ import annotations

from typing import Any

from research.ner_metrics import full_evaluation


def evaluate_oof(
    samples: list[dict[str, Any]],
    indices: list[int],
    true_bio: list[list[str]],
    pred_bio: list[list[str]],
    model_name: str = "model",
) -> dict[str, Any]:
    """Run the spaCy metric pipeline on a subset of out-of-fold predictions.

    ``indices`` is the list of original sample positions; ``true_bio`` and
    ``pred_bio`` are aligned to ``indices`` (one BIO sequence each).
    """
    selected = [samples[i] for i in indices]
    raw = full_evaluation(selected, true_bio, pred_bio, model_name=model_name)
    raw.pop("raw", None)
    return raw
