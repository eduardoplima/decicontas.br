"""Replace stale supervised JSONs in ``dataset/results/output/`` with the new
5-fold OOF predictions, so the bootstrap notebook computes CIs on honest
held-out predictions instead of train-equals-test inference.

Output JSONs follow the BIO layout the bootstrap notebook auto-detects:
``[{"true_labels": [...], "pred_labels": [...], "model": ..., "results": {...}}]``

To keep positional alignment with the LLM JSONs (866 entries, with the bootstrap
notebook dropping rows at ``FEWSHOT_RESULT_POSITIONS``), we pad the OOF arrays
back to length 866 by inserting empty sequences at the 5 leaked positions —
those rows are filtered out by the notebook before any metric is computed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from research.fewshot import FEWSHOT_RESULT_POSITIONS

from .config import REPO_ROOT, SUMMARY_DIR, SUPERVISED_MODELS, safe_name

# Supervised OOF predictions land beside the LLM leaderboard so they get
# scored together. ``DECICONTAS_RESULTS_SUFFIX`` keeps variant runs separate.
_SUFFIX = os.environ.get("DECICONTAS_RESULTS_SUFFIX", "")
OUT_DIR = REPO_ROOT / "dataset" / "results" / "models_outputs" / f"output{_SUFFIX}"


def _expand_to_866(values: list[list[str]]) -> list[list[str]]:
    """Insert empty sequences at the 5 fewshot positions to restore 866-length.

    The CV pipeline already loads the dataset post-filter (861 docs), so
    ``values`` has length 861. The bootstrap notebook then re-applies the
    same fewshot filter; padding with empty sequences makes positional
    alignment with the LLM JSONs trivial.
    """
    out: list[list[str]] = []
    src_iter = iter(values)
    fewshot_set = set(FEWSHOT_RESULT_POSITIONS)
    for pos in range(866):
        if pos in fewshot_set:
            out.append([])
        else:
            out.append(next(src_iter))
    if len(out) != 866:
        raise RuntimeError(f"expected 866 entries, got {len(out)}")
    return out


def export_one(model: str) -> Path:
    cv = json.loads((SUMMARY_DIR / f"cv_{safe_name(model)}.json").read_text())
    # Concatenate per-fold OOF predictions, sorted by global doc index.
    pairs: list[tuple[int, list[str], list[str]]] = []
    for fold in cv["fold_oof"]:
        for gi, t, p in zip(fold["test_indices"], fold["true_labels"], fold["pred_labels"]):
            pairs.append((gi, t, p))
    pairs.sort(key=lambda x: x[0])
    if len(pairs) != 861:
        raise RuntimeError(f"{model}: expected 861 OOF entries, got {len(pairs)}")
    true_seqs = [t for _, t, _ in pairs]
    pred_seqs = [p for _, _, p in pairs]

    record = {
        "true_labels": _expand_to_866(true_seqs),
        "pred_labels": _expand_to_866(pred_seqs),
        "model": model,
        "results": {
            "model": model,
            "span_f1_mean": cv["span_f1"]["mean"],
            "span_f1_std": cv["span_f1"]["std"],
            "n_folds": cv["n_folds"],
            "config": cv["config"],
        },
    }
    out_path = OUT_DIR / f"models_results_decicontas_{safe_name(model)}__supervised.json"
    out_path.write_text(json.dumps([record]))
    return out_path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for m in SUPERVISED_MODELS:
        try:
            p = export_one(m)
            print(f"[wrote] {p}")
        except FileNotFoundError:
            print(f"[skip] {m}: no CV summary on disk yet")


if __name__ == "__main__":
    main()
