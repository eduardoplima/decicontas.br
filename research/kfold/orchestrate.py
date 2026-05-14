"""Two-stage supervised training: grid search on a fixed dev split, then 5-fold CV.

Each (model, config, fold) trains in its own subprocess so MPS memory is fully
released between runs (the previous notebook crashed because BiLSTM ran the
entire k-fold loop in one kernel and accumulated state). Per-run JSON output is
cached on disk; rerunning the orchestrator skips finished runs.

Usage:
    python -m research.kfold.orchestrate                # all
    python -m research.kfold.orchestrate --models bilstm-crf
    python -m research.kfold.orchestrate --smoke        # tiny grid + 1 fold
    python -m research.kfold.orchestrate --models neuralmind/bert-base-portuguese-cased
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import statistics
import subprocess
import sys
import time
from itertools import product
from pathlib import Path
from typing import Any

from .config import (
    CV_DIR,
    GRID_DIR,
    LOGS_DIR,
    N_FOLDS,
    REPO_ROOT,
    SUMMARY_DIR,
    SUPERVISED_MODELS,
    safe_name,
)


def _bilstm_grid(smoke: bool = False) -> list[dict[str, Any]]:
    if smoke:
        return [{"hidden_dim": 128, "dropout": 0.5, "lr": 1e-3, "max_epochs": 2, "patience": 2}]
    return [
        {"hidden_dim": h, "dropout": d, "lr": lr}
        for h, d, lr in product([128, 256], [0.3, 0.5], [1e-3, 3e-3])
    ]


def _bert_grid(model_name: str, smoke: bool = False) -> list[dict[str, Any]]:
    if smoke:
        return [
            {"model_name": model_name, "lr": 3e-5, "warmup_ratio": 0.1, "epochs": 1,
             "early_stopping_patience": 1}
        ]
    return [
        {"model_name": model_name, "lr": lr, "warmup_ratio": w}
        for lr, w in product([2e-5, 3e-5, 5e-5], [0.0, 0.1])
    ]


def _config_id(cfg: dict[str, Any]) -> str:
    """Stable, filesystem-safe id for a config dict."""
    parts = []
    for k in sorted(cfg.keys()):
        v = cfg[k]
        if isinstance(v, float):
            v = f"{v:g}"
        parts.append(f"{k}={v}")
    return "_".join(parts).replace("/", "-")


def _run_one(
    trainer_module: str, cfg: dict[str, Any], mode: str, fold_idx: int,
    cache_path: Path, log_path: Path,
) -> dict[str, Any]:
    """Spawn the trainer subprocess; cache and return its result JSON.

    Re-uses the cached JSON when present so a crash mid-run doesn't lose work.
    """
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    payload = {"config": cfg, "mode": mode, "fold_idx": fold_idx}
    cmd = ["uv", "run", "python", "-m", trainer_module]
    started = time.time()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w") as logf:
        proc = subprocess.run(
            cmd, input=json.dumps(payload), capture_output=True, text=True,
            cwd=str(REPO_ROOT), check=False,
        )
        logf.write("# stdout\n")
        logf.write(proc.stdout)
        logf.write("\n# stderr\n")
        logf.write(proc.stderr)
    elapsed = time.time() - started
    if proc.returncode != 0:
        raise RuntimeError(
            f"Trainer subprocess failed (exit {proc.returncode}). See {log_path}\n"
            f"Last stderr lines:\n{(proc.stderr or '').strip()[-2000:]}"
        )
    # Last line of stdout is the result JSON
    last = (proc.stdout or "").strip().splitlines()
    if not last:
        raise RuntimeError(f"No JSON output from trainer; see {log_path}")
    result = json.loads(last[-1])
    result["_elapsed_seconds"] = elapsed
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(result))
    return result


def _grid_search(model: str, trainer_module: str, grid: list[dict[str, Any]]) -> dict[str, Any]:
    print(f"\n=== Grid search: {model} ({len(grid)} configs) ===")
    rows: list[dict[str, Any]] = []
    for cfg in grid:
        cid = _config_id(cfg)
        cache = GRID_DIR / safe_name(model) / f"{cid}.json"
        log = LOGS_DIR / safe_name(model) / "grid" / f"{cid}.log"
        print(f"  [grid] {cid}")
        result = _run_one(trainer_module, cfg, mode="grid", fold_idx=-1,
                          cache_path=cache, log_path=log)
        m = result["metrics"]
        rows.append({
            "config_id": cid, "config": cfg,
            "span_f1": m["span_f1"],
            "span_precision": m["span_precision"],
            "span_recall": m["span_recall"],
            "token_f1": m["token_f1"],
            "elapsed_seconds": result.get("_elapsed_seconds", 0.0),
        })
        print(f"          dev span F1 = {m['span_f1']:.4f}  ({result.get('_elapsed_seconds', 0):.0f}s)")
    rows.sort(key=lambda r: r["span_f1"], reverse=True)
    best = rows[0]
    summary = {"model": model, "rows": rows, "best": best}
    (SUMMARY_DIR / f"grid_{safe_name(model)}.json").write_text(json.dumps(summary, indent=2))
    print(f"  best: {best['config_id']}  dev span F1 = {best['span_f1']:.4f}")
    return summary


def _cv_run(model: str, trainer_module: str, best_cfg: dict[str, Any]) -> dict[str, Any]:
    print(f"\n=== 5-fold CV: {model} with {_config_id(best_cfg)} ===")
    fold_results: list[dict[str, Any]] = []
    for fold in range(N_FOLDS):
        cache = CV_DIR / safe_name(model) / f"fold{fold}.json"
        log = LOGS_DIR / safe_name(model) / "cv" / f"fold{fold}.log"
        print(f"  [cv] fold {fold + 1}/{N_FOLDS}")
        result = _run_one(trainer_module, best_cfg, mode="cv", fold_idx=fold,
                          cache_path=cache, log_path=log)
        m = result["metrics"]
        fold_results.append({
            "fold": fold, "metrics": m,
            "test_indices": result["test_indices"],
            "true_labels": result["true_labels"],
            "pred_labels": result["pred_labels"],
            "elapsed_seconds": result.get("_elapsed_seconds", 0.0),
        })
        print(f"        fold {fold + 1} span F1 = {m['span_f1']:.4f}  ({result.get('_elapsed_seconds', 0):.0f}s)")

    fold_span_f1 = [r["metrics"]["span_f1"] for r in fold_results]
    fold_token_f1 = [r["metrics"]["token_f1"] for r in fold_results]
    fold_span_prec = [r["metrics"]["span_precision"] for r in fold_results]
    fold_span_rec = [r["metrics"]["span_recall"] for r in fold_results]

    summary = {
        "model": model,
        "config": best_cfg,
        "n_folds": N_FOLDS,
        "fold_metrics": [r["metrics"] for r in fold_results],
        "span_f1": {
            "mean": statistics.fmean(fold_span_f1),
            "std": statistics.stdev(fold_span_f1) if len(fold_span_f1) > 1 else 0.0,
            "values": fold_span_f1,
        },
        "token_f1": {
            "mean": statistics.fmean(fold_token_f1),
            "std": statistics.stdev(fold_token_f1) if len(fold_token_f1) > 1 else 0.0,
            "values": fold_token_f1,
        },
        "span_precision": {
            "mean": statistics.fmean(fold_span_prec),
            "std": statistics.stdev(fold_span_prec) if len(fold_span_prec) > 1 else 0.0,
        },
        "span_recall": {
            "mean": statistics.fmean(fold_span_rec),
            "std": statistics.stdev(fold_span_rec) if len(fold_span_rec) > 1 else 0.0,
        },
        "fold_oof": [
            {
                "fold": r["fold"],
                "test_indices": r["test_indices"],
                "true_labels": r["true_labels"],
                "pred_labels": r["pred_labels"],
            }
            for r in fold_results
        ],
    }
    (SUMMARY_DIR / f"cv_{safe_name(model)}.json").write_text(json.dumps(summary, indent=2))
    mean = summary["span_f1"]["mean"]
    std = summary["span_f1"]["std"]
    print(f"  CV span F1 = {mean:.4f} ± {std:.4f}")
    return summary


def run_for_model(model: str, smoke: bool = False) -> None:
    if model == "bilstm-crf":
        trainer = "research.kfold.train_bilstm"
        grid = _bilstm_grid(smoke=smoke)
    else:
        trainer = "research.kfold.train_bert"
        grid = _bert_grid(model, smoke=smoke)

    grid_summary = _grid_search(model, trainer, grid)
    best_cfg = grid_summary["best"]["config"]
    _cv_run(model, trainer, best_cfg)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--models", nargs="+", default=SUPERVISED_MODELS)
    p.add_argument("--smoke", action="store_true",
                   help="Tiny grid + 1 epoch — for plumbing checks only.")
    args = p.parse_args()

    for m in args.models:
        try:
            run_for_model(m, smoke=args.smoke)
        except Exception as e:  # noqa: BLE001
            print(f"\n[FAIL] {m}: {e}", file=sys.stderr)
            raise


if __name__ == "__main__":
    main()
