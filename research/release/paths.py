"""Result paths for the released pipeline.

All LLM-derived artifacts live under a single canonical tree,
``dataset/results/models_outputs/`` (the temperature-0 run that the
dissertation reports). Superseded runs are archived under
``dataset/results/old_experiments/`` and are not addressed by this module.

Shared, prompt-independent inputs (raw corpus, cleanlab corrections) and the
supervised k-fold results live at fixed paths read by the whole pipeline.

``DECICONTAS_VARIANT=<name>`` evaluates another version of the corpus side by
side: the release is read from ``dataset/release/decicontas-<name>/`` and every
derived tree gets the ``_<name>`` suffix (``output_<name>``,
``model_evaluation_<name>``, ``supervised_kfold_<name>``, ...). The inputs and
the canonical release (``CANONICAL_*``) never move.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / "dataset"

RESULTS_ROOT = DATASET / "results" / "models_outputs"

VARIANT = os.environ.get("DECICONTAS_VARIANT", "")
_SFX = f"_{VARIANT}" if VARIANT else ""

# --- LLM-derived results ---
RAW_OUTPUT_DIR = RESULTS_ROOT / "output"  # raw few_shot leaderboard predictions
OUTPUT_CORRECTED_DIR = RESULTS_ROOT / (f"output{_SFX}" if VARIANT else "output_corrected")
RAW_PROMPT_ENG_DIR = RESULTS_ROOT / "experiments" / "prompt_engineering"  # raw cot/two_stage
RAW_EXPERIMENTS_DIR = RESULTS_ROOT / "experiments"  # parent of prompt_engineering, etc.
CORRECTED_EXPERIMENTS_DIR = RESULTS_ROOT / (f"experiments{_SFX}" if VARIANT else "experiments_corrected")
CORPUS_DIR = RESULTS_ROOT / f"corpus_and_agreement{_SFX}"  # corpus_analysis CSVs + REPORT.md
EVALUATION_DIR = RESULTS_ROOT / f"model_evaluation{_SFX}"  # block A-M CSVs + REPORT.md
SIGNIFICANCE_DIR = RESULTS_ROOT / f"significance{_SFX}"  # bootstrap CSVs
FIGURES_DIR = REPO_ROOT / "figures" / VARIANT if VARIANT else REPO_ROOT / "figures"
REPRODUCIBILITY_DIR = RESULTS_ROOT / f"reproducibility{_SFX}"
EXPERIMENTS_SUMMARY_DIR = RESULTS_ROOT / f"experiments_summary{_SFX}"  # rescore_experiments md tables

# --- shared inputs / supervised results ---
CANONICAL_RELEASE_DIR = DATASET / "release" / "decicontas"
CANONICAL_RELEASE_PRE_DIR = DATASET / "release" / "decicontas-before-correction"
CANONICAL_GOLD_JSON = CANONICAL_RELEASE_DIR / "decicontas.json"
_VARIANT_RELEASE = DATASET / "release" / f"decicontas-{VARIANT}"
RELEASE_DIR = _VARIANT_RELEASE / "decicontas" if VARIANT else CANONICAL_RELEASE_DIR
RELEASE_PRE_DIR = _VARIANT_RELEASE / "decicontas-before-correction" if VARIANT else CANONICAL_RELEASE_PRE_DIR
CORRECTIONS_JSON = DATASET / "errors" / "dataset-corrections.json"
CLEANLAB_ERRORS_CSV = DATASET / "errors" / "erros_anotacao_decicontas.csv"
ADJUDICATION_STATE_JSON = DATASET / "errors" / "adjudication-state.json"  # tools.adjudication
ADJUDICATION_DECISIONS_JSON = DATASET / "errors" / "adjudication-decisions.json"
KFOLD_CORRECTED = RESULTS_ROOT / f"supervised_kfold{_SFX}"
LABELED_CORPUS = DATASET / "labeled_data" / "decicontas.json"
CORRECTED_GOLD_JSON = RELEASE_DIR / "decicontas.json"
ANNOTATORS_DIR = DATASET / "annotators"  # independent annotations (agreement study)


def ensure_results_dirs() -> None:
    """Create the result directories (idempotent)."""
    for d in (
        RAW_OUTPUT_DIR,
        OUTPUT_CORRECTED_DIR,
        RAW_PROMPT_ENG_DIR,
        CORRECTED_EXPERIMENTS_DIR,
        EVALUATION_DIR,
        SIGNIFICANCE_DIR,
        FIGURES_DIR,
        REPRODUCIBILITY_DIR,
        EXPERIMENTS_SUMMARY_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)
