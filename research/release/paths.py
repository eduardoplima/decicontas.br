"""Cycle-aware result paths.

A *cycle* is a self-contained tree of LLM-derived artifacts under
``dataset/results/cycles/<CYCLE>/``. Set the ``DECICONTAS_CYCLE`` env var to
switch between cycles (mirrors the existing ``DECICONTAS_RESULTS_SUFFIX``
pattern used by the k-fold orchestrator). Default is ``new_clean``.

Two cycles exist:
- ``old_leakage`` — the original LLM results produced with the prompt that
  carried the OBRIGACAO test-set leakage (archived).
- ``new_clean`` — clean prompt + the Brazil-region Azure model set.

Shared, prompt-independent artifacts (corrected gold, cleanlab audit, supervised
k-fold) live at fixed paths OUTSIDE any cycle and are read by both.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / "dataset"

CYCLE = os.getenv("DECICONTAS_CYCLE", "new_clean")
CYCLES_ROOT = DATASET / "results" / "cycles"
CYCLE_ROOT = CYCLES_ROOT / CYCLE

# --- cycle-specific (LLM-derived) ---
RAW_OUTPUT_DIR = CYCLE_ROOT / "output"  # raw few_shot leaderboard predictions
OUTPUT_CORRECTED_DIR = CYCLE_ROOT / "output_corrected"  # rescored vs corrected gold
RAW_PROMPT_ENG_DIR = CYCLE_ROOT / "experiments" / "prompt_engineering"  # raw cot/two_stage
RAW_EXPERIMENTS_DIR = CYCLE_ROOT / "experiments"  # parent of prompt_engineering, etc.
CORRECTED_EXPERIMENTS_DIR = CYCLE_ROOT / "experiments_corrected"  # has prompt_engineering/ subdir
CHAPTER5_DIR = CYCLE_ROOT / "chapter5"  # block A-M CSVs + REPORT.md
SIGNIFICANCE_DIR = CYCLE_ROOT / "significance"  # bootstrap CSVs/LaTeX
FIGURES_DIR = CYCLE_ROOT / "figures"
REPRODUCIBILITY_DIR = CYCLE_ROOT / "reproducibility"
EXPERIMENTS_SUMMARY_DIR = CYCLE_ROOT / "experiments_summary"  # rescore_experiments md tables

# --- shared (prompt-independent; read by every cycle) ---
RELEASE_DIR = DATASET / "release" / "decicontas-861-corrected"
RELEASE_PRE_DIR = DATASET / "release" / "decicontas-861"
CORRECTIONS_JSON = DATASET / "errors" / "dataset-corrections.json"
KFOLD_CORRECTED = DATASET / "results" / "supervised_kfold_corrected"
LABELED_CORPUS = DATASET / "labeled_data" / "decicontas.json"
CORRECTED_GOLD_JSON = RELEASE_DIR / "decicontas.json"


def ensure_cycle_dirs() -> None:
    """Create the cycle-specific directories (idempotent)."""
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
