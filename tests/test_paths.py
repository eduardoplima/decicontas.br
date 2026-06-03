"""Cycle-aware path resolution (research.release.paths)."""

from __future__ import annotations

import importlib


def _reload_paths(monkeypatch, cycle: str | None):
    if cycle is None:
        monkeypatch.delenv("DECICONTAS_CYCLE", raising=False)
    else:
        monkeypatch.setenv("DECICONTAS_CYCLE", cycle)
    import research.release.paths as p

    return importlib.reload(p)


def test_default_cycle_is_new_clean(monkeypatch):
    p = _reload_paths(monkeypatch, None)
    assert p.CYCLE == "new_clean"
    assert p.CHAPTER5_DIR == p.REPO_ROOT / "dataset/results/cycles/new_clean/chapter5"
    assert p.OUTPUT_CORRECTED_DIR.parts[-2:] == ("new_clean", "output_corrected")


def test_cycle_switch_via_env(monkeypatch):
    p = _reload_paths(monkeypatch, "old_leakage")
    assert p.CYCLE == "old_leakage"
    assert "cycles/old_leakage" in str(p.CHAPTER5_DIR)
    assert "cycles/old_leakage" in str(p.FIGURES_DIR)


def test_shared_dirs_are_cycle_independent(monkeypatch):
    a = _reload_paths(monkeypatch, "new_clean")
    shared_a = (a.KFOLD_CORRECTED, a.CORRECTED_GOLD_JSON, a.RELEASE_DIR, a.LABELED_CORPUS)
    b = _reload_paths(monkeypatch, "old_leakage")
    shared_b = (b.KFOLD_CORRECTED, b.CORRECTED_GOLD_JSON, b.RELEASE_DIR, b.LABELED_CORPUS)
    assert shared_a == shared_b  # shared artifacts do not move between cycles
    # restore default for other tests
    _reload_paths(monkeypatch, None)
