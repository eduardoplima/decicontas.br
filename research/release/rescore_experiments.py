"""Re-evaluate ``notebooks/ner_experiments.ipynb`` on the cleanlab-corrected gold.

Mirrors what the notebook does — load every result file in the three
experiment directories, compute span / token F1, and write the same
markdown summaries — but consumes the corrected gold (LLM rescores) and
the retrained supervised baselines we already produced. **No LLM API
calls.** Predictions are reused as-is; only the gold reference changes.

Inputs:
- LLM JSONs at ``dataset/experiments/{few_shot_and_supervised, function_calling_json_schema, prompt_engineering}/``
- Corrected gold at ``dataset/release/decicontas-861-corrected/decicontas.json``
- Retrained supervised CV at ``dataset/results/supervised_kfold_corrected/summary/cv_*.json``

Outputs:
- Rescored experiment files at ``dataset/experiments_corrected/<dir>/``
  (LLM JSONs with ``golden`` swapped, supervised PKLs with new
  ``true_labels``/``pred_labels`` from the corrected k-fold)
- Markdown tables at ``dataset/results/experiments_corrected/``:
  ``fewshot_results.md``, ``fc_vs_json_schema.md``,
  ``prompt_engineering_results.md``, ``strategy_summary.md``
"""

from __future__ import annotations

import argparse
import json
import logging
import pickle
from pathlib import Path
from typing import Any

import pandas as pd

from research.fewshot import FEWSHOT_RESULT_POSITIONS
from research.ner_metrics import evaluate_bio_results, evaluate_llm_results


from research.release import paths

REPO_ROOT = paths.REPO_ROOT

EXPERIMENTS_SRC = paths.RAW_EXPERIMENTS_DIR  # cycle-specific
EXPERIMENTS_DST = paths.CORRECTED_EXPERIMENTS_DIR  # cycle-specific
SUMMARY_DST = paths.EXPERIMENTS_SUMMARY_DIR  # cycle-specific
CORRECTED_JSON = paths.CORRECTED_GOLD_JSON  # shared corrected gold
KFOLD_CORRECTED = paths.KFOLD_CORRECTED  # shared

SUBDIRS = ("few_shot_and_supervised", "function_calling_json_schema", "prompt_engineering")


logger = logging.getLogger("research.release.rescore_experiments")


# ----- Gold lookup -------------------------------------------------------


def _load_gold_lookup(corrected_path: Path) -> dict[str, list[dict]]:
    docs = json.loads(corrected_path.read_text(encoding="utf-8"))
    lookup: dict[str, list[dict]] = {}
    for doc in docs:
        stripped = doc["text"].strip()
        if stripped in lookup:
            raise RuntimeError(f"text collision after strip on doc {doc['id']}")
        lookup[stripped] = [
            {
                "start": int(e["start"]),
                "end": int(e["end"]),
                "text": doc["text"][int(e["start"]) : int(e["end"])],
                "labels": [e["label"]],
            }
            for e in doc.get("entities", [])
        ]
    return lookup


# ----- LLM JSON rescoring ------------------------------------------------


def _rescore_llm_json(
    in_path: Path, out_path: Path, lookup: dict[str, list[dict]]
) -> dict[str, Any] | None:
    data = json.loads(in_path.read_text(encoding="utf-8"))
    if not (isinstance(data, list) and data and isinstance(data[0], dict) and "pred" in data[0]):
        return None
    miss = 0
    for entry in data:
        key = (entry.get("text") or "").strip()
        new_gold = lookup.get(key)
        if new_gold is None:
            miss += 1
            continue
        entry["golden"] = new_gold
    if miss:
        logger.warning("%s: %d/%d entries had no gold match", in_path.name, miss, len(data))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    df = pd.DataFrame(data)
    if not {"text", "pred", "golden"}.issubset(df.columns):
        return None
    return evaluate_llm_results(df.copy())


# ----- Supervised PKL replacement ----------------------------------------


_SUPERVISED_MAP = {
    # PKL stem in experiments dir → safe_name in supervised k-fold dir
    "bilstm-crf__supervised": "bilstm-crf",
    "neuralmind_bert-base-portuguese-cased__supervised": "neuralmind_bert-base-portuguese-cased",
    "neuralmind_bert-large-portuguese-cased__supervised": "neuralmind_bert-large-portuguese-cased",
    "rufimelo_Legal-BERTimbau-base__supervised": "rufimelo_Legal-BERTimbau-base",
}

# Few-shot positions to pad. The supervised k-fold runs on 861 docs (post
# fewshot filter); we pad with empty sequences at the leaked positions
# to keep the 866-document positional alignment shared with the LLM
# prediction files (which carry all 866 docs). FEWSHOT_RESULT_POSITIONS is
# imported at module top.


def _expand_to_866(values: list[list[str]]) -> list[list[str]]:
    out: list[list[str]] = []
    src = iter(values)
    fewshot = set(FEWSHOT_RESULT_POSITIONS)
    for pos in range(866):
        out.append([] if pos in fewshot else next(src))
    return out


def _supervised_dict_from_cv(cv_summary_path: Path) -> dict:
    cv = json.loads(cv_summary_path.read_text(encoding="utf-8"))
    pairs: list[tuple[int, list[str], list[str]]] = []
    for fold in cv["fold_oof"]:
        for gi, t, p in zip(fold["test_indices"], fold["true_labels"], fold["pred_labels"]):
            pairs.append((gi, t, p))
    pairs.sort(key=lambda x: x[0])
    if len(pairs) != 861:
        raise RuntimeError(
            f"{cv_summary_path.name}: expected 861 OOF entries, got {len(pairs)}"
        )
    return {
        "true_labels": _expand_to_866([t for _, t, _ in pairs]),
        "pred_labels": _expand_to_866([p for _, _, p in pairs]),
        "results": {
            "model": cv["model"],
            "span_f1_mean": cv["span_f1"]["mean"],
            "span_f1_std": cv["span_f1"]["std"],
            "n_folds": cv["n_folds"],
            "config": cv["config"],
        },
    }


def _replace_supervised_pkl(in_path: Path, out_path: Path) -> dict[str, Any] | None:
    name = in_path.stem
    safe = _SUPERVISED_MAP.get(name)
    if safe is None:
        logger.warning("no corrected counterpart for %s; skipping", name)
        return None
    cv_path = KFOLD_CORRECTED / "summary" / f"cv_{safe}.json"
    if not cv_path.exists():
        logger.warning("missing %s; skipping", cv_path)
        return None
    data = _supervised_dict_from_cv(cv_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as fh:
        pickle.dump(data, fh)
    return evaluate_bio_results(data)


# ----- Notebook-mirroring evaluation -------------------------------------


def _load_dir(directory: Path, lookup: dict[str, list[dict]]) -> dict[str, dict]:
    """Walk one experiment subdirectory; rescore + evaluate each file."""
    results: dict[str, dict] = {}
    if not directory.exists():
        logger.warning("missing source dir %s", directory)
        return results
    out_dir = EXPERIMENTS_DST / directory.name
    out_dir.mkdir(parents=True, exist_ok=True)
    for jf in sorted(directory.glob("*.json")):
        name = jf.stem.replace("models_results_decicontas_", "")
        out_path = out_dir / jf.name
        try:
            metrics = _rescore_llm_json(jf, out_path, lookup)
        except Exception as exc:  # noqa: BLE001
            logger.error("rescoring %s failed: %s", jf.name, exc)
            continue
        if metrics is None:
            continue
        results[name] = metrics
        logger.info(
            "  %s  token_f1=%.4f  span_f1=%.4f", name, metrics["token_f1"], metrics["span_f1"]
        )
    for pf in sorted(directory.glob("*.pkl")):
        name = pf.stem
        out_path = out_dir / pf.name
        metrics = _replace_supervised_pkl(pf, out_path)
        if metrics is None:
            continue
        results[name] = metrics
        logger.info(
            "  %s  token_f1=%.4f  span_f1=%.4f (corrected supervised)",
            name,
            metrics["token_f1"],
            metrics["span_f1"],
        )
    return results


def _results_to_dataframe(
    results: dict[str, dict], parse_model_strategy: bool = True
) -> pd.DataFrame:
    df = pd.DataFrame(results).T
    df.index.name = "experiment"
    if parse_model_strategy:
        df["model"] = df.index.map(lambda x: x.rsplit("__", 1)[0] if "__" in x else x)
        df["strategy"] = df.index.map(
            lambda x: x.rsplit("__", 1)[1] if "__" in x else "few_shot"
        )
    main_cols = ["model", "strategy"] if parse_model_strategy else []
    metric_cols = [
        "token_f1",
        "token_precision",
        "token_recall",
        "span_f1",
        "span_precision",
        "span_recall",
    ]
    entity_cols = sorted(
        c
        for c in df.columns
        if c.startswith(("f1_", "precision_", "recall_")) and c not in metric_cols
    )
    ordered = main_cols + [c for c in metric_cols if c in df.columns] + entity_cols
    remaining = [c for c in df.columns if c not in ordered]
    df = df[ordered + remaining]
    return df.sort_values("span_f1", ascending=False)


def _parse_technique(name: str) -> tuple[str, str]:
    techniques = ["dynamic_few_shot", "two_stage", "few_shot", "cot"]
    for t in techniques:
        if name.endswith(f"_{t}"):
            return name[: -(len(t) + 1)], t
    return name, "unknown"


def run() -> None:
    SUMMARY_DST.mkdir(parents=True, exist_ok=True)
    EXPERIMENTS_DST.mkdir(parents=True, exist_ok=True)

    lookup = _load_gold_lookup(CORRECTED_JSON)

    # Each experiment subdir is optional per cycle (the new_clean cycle only has
    # prompt_engineering; few_shot_and_supervised / function_calling_json_schema
    # are old-cycle, archived in old_leakage). Skip summaries for absent dirs.

    # ---------- Experiment 1: few-shot vs supervised (optional) ----------
    results_fewshot = _load_dir(EXPERIMENTS_SRC / "few_shot_and_supervised", lookup)
    df_fewshot = _results_to_dataframe(results_fewshot) if results_fewshot else pd.DataFrame()
    if not df_fewshot.empty:
        df_fewshot["paradigm"] = df_fewshot["strategy"].apply(
            lambda s: "supervised" if s == "supervised" else "few-shot"
        )
        df_fewshot.to_markdown(SUMMARY_DST / "fewshot_results.md", index=True)
        df_fewshot.groupby("paradigm")[["token_f1", "span_f1"]].agg(
            ["mean", "std", "max"]
        ).to_markdown(SUMMARY_DST / "paradigm_summary.md", index=True)

    # ---------- Experiment 2: function calling vs JSON schema (optional) ----------
    results_fcjs = _load_dir(EXPERIMENTS_SRC / "function_calling_json_schema", lookup)
    df_method_cmp = pd.DataFrame()
    if results_fcjs:
        df_fcjs = _results_to_dataframe(results_fcjs, parse_model_strategy=False)
        df_fcjs["method"] = df_fcjs.index.map(
            lambda x: "function_calling" if x.endswith("_fc") else "json_schema"
        )
        df_fcjs["model_clean"] = df_fcjs.index.map(
            lambda x: x.replace("_fc", "").replace("_json", "").replace("_few_shot", "")
        )
        df_method_cmp = df_fcjs.sort_values(["model_clean", "method"]).reset_index(drop=True)
        df_method_cmp.to_markdown(SUMMARY_DST / "fc_vs_json_schema.md", index=False)

    # ---------- Experiment 3: prompt engineering techniques ----------
    results_prompt = _load_dir(EXPERIMENTS_SRC / "prompt_engineering", lookup)
    df_prompt = (
        _results_to_dataframe(results_prompt, parse_model_strategy=False)
        if results_prompt else pd.DataFrame()
    )
    strategy_summary = pd.DataFrame()
    if not df_prompt.empty:
        parsed = df_prompt.index.map(_parse_technique)
        df_prompt["model"] = [p[0] for p in parsed]
        df_prompt["technique"] = [p[1] for p in parsed]
        df_prompt.to_markdown(SUMMARY_DST / "prompt_engineering_results.md", index=True)
        strategy_summary = df_prompt.groupby("technique")[["token_f1", "span_f1"]].agg(
            ["mean", "std", "max"]
        )
        strategy_summary.to_markdown(SUMMARY_DST / "strategy_summary.md", index=True)

    # ---------- Console leaderboard (skip empty blocks) ----------
    if not df_fewshot.empty:
        print("\n=== Experiment 1 — Few-shot vs Supervised (corrected) ===")
        print(df_fewshot[["model", "strategy", "paradigm", "token_f1", "span_f1"]]
              .head(15).round(4).to_string())
    if not df_method_cmp.empty:
        print("\n=== Experiment 2 — FC vs JSON Schema (corrected) ===")
        print(df_method_cmp[["model_clean", "method", "token_f1", "span_f1"]]
              .round(4).to_string(index=False))
    if not df_prompt.empty:
        print("\n=== Experiment 3 — Prompt techniques (corrected) ===")
        print(df_prompt[["model", "technique", "token_f1", "span_f1"]].round(4).to_string())
    if not strategy_summary.empty:
        print("\n=== Strategy summary ===")
        print(strategy_summary.round(4))


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
