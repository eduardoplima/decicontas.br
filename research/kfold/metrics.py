"""Thin wrapper around :func:`research.ner_metrics.full_evaluation`.

Span F1 (IoU >= 0.5) and per-entity span F1 over a set of out-of-fold BIO
predictions, through the same metric pipeline used for the LLMs, so the two
paradigms are directly comparable.
"""

from __future__ import annotations

from typing import Any

from research.annotation_scope import clause_regions, mask_bio
from research.ner_metrics import full_evaluation


def _regions(sample: dict[str, Any]) -> list[tuple[int, int]]:
    offsets = [(t["start"], t["end"]) for t in sample.get("token_offsets") or []]
    return clause_regions(sample.get("text") or "", offsets or None)


def evaluate_oof(
    samples: list[dict[str, Any]],
    indices: list[int],
    true_bio: list[list[str]],
    pred_bio: list[list[str]],
    model_name: str = "model",
) -> dict[str, Any]:
    """Score a subset of out-of-fold predictions.

    ``indices`` are the original sample positions; ``true_bio`` and ``pred_bio``
    are aligned to them. Predictions on out-of-scope clauses are blanked first;
    training and checkpoint selection do not go through here.
    """
    selected = [samples[i] for i in indices]
    masked = [mask_bio(pred, _regions(sample)) for sample, pred in zip(selected, pred_bio)]
    raw = full_evaluation(selected, true_bio, masked, model_name=model_name)
    raw.pop("raw", None)
    return raw
