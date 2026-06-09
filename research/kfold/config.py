"""Constants shared by the supervised k-fold pipeline.

Two environment variables let an alternative dataset run side-by-side
with the original (no overwrite of the legacy artefacts):

- ``DECICONTAS_DATASET_PATH`` — path to the Label-Studio JSON to train
  on. Read by ``data.load_bio_samples``. Default: the master export.
- ``DECICONTAS_RESULTS_SUFFIX`` — suffix appended to the
  ``supervised_kfold`` results root so each variant lives in its own
  tree. Default: empty string (the canonical
  ``results/models_outputs/supervised_kfold/`` dir).
"""

from __future__ import annotations

import os
from pathlib import Path

SEED: int = 1007
N_FOLDS: int = 5

REPO_ROOT: Path = Path(__file__).resolve().parents[2]

_RESULTS_SUFFIX: str = os.environ.get("DECICONTAS_RESULTS_SUFFIX", "")
RESULTS_ROOT: Path = (
    REPO_ROOT
    / "dataset"
    / "results"
    / "models_outputs"
    / f"supervised_kfold{_RESULTS_SUFFIX}"
)
GRID_DIR: Path = RESULTS_ROOT / "grid"
CV_DIR: Path = RESULTS_ROOT / "cv"
LOGS_DIR: Path = RESULTS_ROOT / "logs"
SUMMARY_DIR: Path = RESULTS_ROOT / "summary"

DATASET_PATH: str | None = os.environ.get("DECICONTAS_DATASET_PATH")

for _d in (GRID_DIR, CV_DIR, LOGS_DIR, SUMMARY_DIR):
    _d.mkdir(parents=True, exist_ok=True)


SUPERVISED_MODELS: list[str] = [
    "bilstm-crf",
    "neuralmind/bert-base-portuguese-cased",
    "neuralmind/bert-large-portuguese-cased",
    "rufimelo/Legal-BERTimbau-base",
]


def safe_name(model: str) -> str:
    return model.replace("/", "_").replace(".", "-")
