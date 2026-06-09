"""Result paths for the released pipeline.

All LLM-derived artifacts live under a single canonical tree,
``dataset/results/models_outputs/`` (the temperature-0 run that the
dissertation reports). Superseded runs are archived under
``dataset/results/old_experiments/`` and are not addressed by this module.

Shared, prompt-independent inputs (raw corpus, cleanlab corrections) and the
supervised k-fold results live at fixed paths read by the whole pipeline.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / "dataset"

RESULTS_ROOT = DATASET / "results" / "models_outputs"

# --- LLM-derived results ---
RAW_OUTPUT_DIR = RESULTS_ROOT / "output"  # raw few_shot leaderboard predictions
OUTPUT_CORRECTED_DIR = RESULTS_ROOT / "output_corrected"  # rescored vs corrected gold
RAW_PROMPT_ENG_DIR = RESULTS_ROOT / "experiments" / "prompt_engineering"  # raw cot/two_stage
RAW_EXPERIMENTS_DIR = RESULTS_ROOT / "experiments"  # parent of prompt_engineering, etc.
CORRECTED_EXPERIMENTS_DIR = RESULTS_ROOT / "experiments_corrected"  # has prompt_engineering/ subdir
CHAPTER5_DIR = RESULTS_ROOT / "chapter5"  # block A-M CSVs + REPORT.md
SIGNIFICANCE_DIR = RESULTS_ROOT / "significance"  # bootstrap CSVs
FIGURES_DIR = RESULTS_ROOT / "figures"
REPRODUCIBILITY_DIR = RESULTS_ROOT / "reproducibility"
EXPERIMENTS_SUMMARY_DIR = RESULTS_ROOT / "experiments_summary"  # rescore_experiments md tables

# --- shared inputs / supervised results ---
RELEASE_DIR = DATASET / "release" / "decicontas"
RELEASE_PRE_DIR = DATASET / "release" / "decicontas-before-correction"
CORRECTIONS_JSON = DATASET / "errors" / "dataset-corrections.json"
KFOLD_CORRECTED = RESULTS_ROOT / "supervised_kfold"
LABELED_CORPUS = DATASET / "labeled_data" / "decicontas.json"
CORRECTED_GOLD_JSON = RELEASE_DIR / "decicontas.json"


def ensure_results_dirs() -> None:
    """Create the result directories (idempotent)."""
    for d in (
        RAW_OUTPUT_DIR,
        OUTPUT_CORRECTED_DIR,
        RAW_PROMPT_ENG_DIR,
        CORRECTED_EXPERIMENTS_DIR,
        CHAPTER5_DIR,
        SIGNIFICANCE_DIR,
        FIGURES_DIR,
        REPRODUCIBILITY_DIR,
        EXPERIMENTS_SUMMARY_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)
