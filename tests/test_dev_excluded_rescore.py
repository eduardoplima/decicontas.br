"""Repontuação sem os documentos de desenvolvimento (``scripts/dev_excluded_rescore.py``)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from dev_excluded_rescore import (  # noqa: E402
    keep_positions,
    micro_f1,
    read_dev_indices,
    subset_counts,
)


def _write_grid(root: Path, model: str, name: str, indices: list[int]) -> None:
    d = root / model
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps({"test_indices": indices}), encoding="utf-8")


def test_read_dev_indices_returns_sorted_shared_set(tmp_path: Path) -> None:
    _write_grid(tmp_path, "m1", "cfg_a", [5, 1, 3])
    _write_grid(tmp_path, "m2", "cfg_b", [3, 5, 1])
    assert read_dev_indices(tmp_path) == [1, 3, 5]


def test_read_dev_indices_rejects_disagreeing_artefacts(tmp_path: Path) -> None:
    _write_grid(tmp_path, "m1", "cfg_a", [1, 3])
    _write_grid(tmp_path, "m2", "cfg_b", [1, 4])
    with pytest.raises(ValueError, match="discordam"):
        read_dev_indices(tmp_path)


def test_read_dev_indices_rejects_empty_dir(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="nenhum"):
        read_dev_indices(tmp_path)


def test_keep_positions_is_the_complement_of_dev() -> None:
    keep = keep_positions(6, [0, 4])
    assert keep.tolist() == [1, 2, 3, 5]
    with pytest.raises(ValueError):
        keep_positions(3, [3])


def _counts() -> dict:
    return {
        "MULTA": {"tp": np.array([1, 0, 2]), "fp": np.array([0, 1, 0]), "fn": np.array([1, 0, 0])},
        "OBRIGACAO": {"tp": np.array([0, 1, 0]), "fp": np.array([0, 0, 1]), "fn": np.array([0, 1, 0])},
    }


def test_subset_counts_slices_every_array() -> None:
    sub = subset_counts(_counts(), np.array([0, 2]))
    assert sub["MULTA"]["tp"].tolist() == [1, 2]
    assert sub["OBRIGACAO"]["fp"].tolist() == [0, 1]


def test_micro_f1_sums_over_classes_and_respects_subset() -> None:
    # Full: tp=4, fp=2, fn=2 -> F1 = 8 / 12
    assert micro_f1(_counts()) == pytest.approx(8 / 12)
    # Docs 0 and 2: tp=3, fp=1, fn=1 -> F1 = 6 / 8
    assert micro_f1(_counts(), np.array([0, 2])) == pytest.approx(6 / 8)
