"""Result path resolution (research.release.paths)."""

from __future__ import annotations

import research.release.paths as p


def test_results_root_is_models_outputs():
    assert p.RESULTS_ROOT == p.REPO_ROOT / "dataset/results/models_outputs"
    assert p.CHAPTER5_DIR == p.RESULTS_ROOT / "chapter5"
    assert p.OUTPUT_CORRECTED_DIR == p.RESULTS_ROOT / "output_corrected"
    assert p.FIGURES_DIR == p.RESULTS_ROOT / "figures"
    assert p.SIGNIFICANCE_DIR == p.RESULTS_ROOT / "significance"


def test_release_dirs_are_renamed():
    assert p.RELEASE_DIR == p.REPO_ROOT / "dataset/release/decicontas"
    assert p.RELEASE_PRE_DIR == p.REPO_ROOT / "dataset/release/decicontas-before-correction"
    assert p.CORRECTED_GOLD_JSON == p.RELEASE_DIR / "decicontas.json"


def test_shared_inputs_and_kfold():
    assert p.KFOLD_CORRECTED == p.RESULTS_ROOT / "supervised_kfold"
    assert p.CORRECTIONS_JSON == p.REPO_ROOT / "dataset/errors/dataset-corrections.json"
    assert p.LABELED_CORPUS == p.REPO_ROOT / "dataset/labeled_data/decicontas.json"
