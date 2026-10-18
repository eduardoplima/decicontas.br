"""Result path resolution (research.release.paths)."""

from __future__ import annotations

import research.release.paths as p


def test_results_root_is_models_outputs():
    assert p.RESULTS_ROOT == p.REPO_ROOT / "dataset/results/models_outputs"
    assert p.EVALUATION_DIR == p.RESULTS_ROOT / "model_evaluation"
    assert p.OUTPUT_CORRECTED_DIR == p.RESULTS_ROOT / "output_corrected"
    assert p.FIGURES_DIR == p.REPO_ROOT / "figures"
    assert p.SIGNIFICANCE_DIR == p.RESULTS_ROOT / "significance"


def test_release_dirs_are_renamed():
    assert p.RELEASE_DIR == p.REPO_ROOT / "dataset/release/decicontas"
    assert p.RELEASE_PRE_DIR == p.REPO_ROOT / "dataset/release/decicontas-before-correction"
    assert p.CORRECTED_GOLD_JSON == p.RELEASE_DIR / "decicontas.json"


def test_shared_inputs_and_kfold():
    assert p.KFOLD_CORRECTED == p.RESULTS_ROOT / "supervised_kfold"
    assert p.CORRECTIONS_JSON == p.REPO_ROOT / "dataset/errors/dataset-corrections.json"
    assert p.LABELED_CORPUS == p.REPO_ROOT / "dataset/labeled_data/decicontas.json"


def test_a_variant_moves_every_derived_tree_and_leaves_the_inputs_alone(monkeypatch):
    import importlib

    monkeypatch.setenv("DECICONTAS_VARIANT", "adjudicated")
    try:
        v = importlib.reload(p)
        root = v.REPO_ROOT
        assert v.VARIANT == "adjudicated"
        assert v.RELEASE_DIR == root / "dataset/release/decicontas-adjudicated/decicontas"
        assert v.RELEASE_PRE_DIR == root / "dataset/release/decicontas-adjudicated/decicontas-before-correction"
        assert v.CORRECTED_GOLD_JSON == v.RELEASE_DIR / "decicontas.json"
        assert v.CANONICAL_GOLD_JSON == root / "dataset/release/decicontas/decicontas.json"
        assert v.OUTPUT_CORRECTED_DIR == v.RESULTS_ROOT / "output_adjudicated"
        assert v.CORRECTED_EXPERIMENTS_DIR == v.RESULTS_ROOT / "experiments_adjudicated"
        assert v.EVALUATION_DIR == v.RESULTS_ROOT / "model_evaluation_adjudicated"
        assert v.SIGNIFICANCE_DIR == v.RESULTS_ROOT / "significance_adjudicated"
        assert v.CORPUS_DIR == v.RESULTS_ROOT / "corpus_and_agreement_adjudicated"
        assert v.EXPERIMENTS_SUMMARY_DIR == v.RESULTS_ROOT / "experiments_summary_adjudicated"
        assert v.REPRODUCIBILITY_DIR == v.RESULTS_ROOT / "reproducibility_adjudicated"
        assert v.KFOLD_CORRECTED == v.RESULTS_ROOT / "supervised_kfold_adjudicated"
        assert v.FIGURES_DIR == root / "figures/adjudicated"
        # inputs shared by every variant
        assert v.RAW_OUTPUT_DIR == v.RESULTS_ROOT / "output"
        assert v.RAW_EXPERIMENTS_DIR == v.RESULTS_ROOT / "experiments"
        assert v.LABELED_CORPUS == root / "dataset/labeled_data/decicontas.json"
        assert v.CORRECTIONS_JSON == root / "dataset/errors/dataset-corrections.json"
        assert v.ANNOTATORS_DIR == root / "dataset/annotators"
    finally:
        monkeypatch.delenv("DECICONTAS_VARIANT")
        importlib.reload(p)
    assert p.VARIANT == "" and p.OUTPUT_CORRECTED_DIR == p.RESULTS_ROOT / "output_corrected"
