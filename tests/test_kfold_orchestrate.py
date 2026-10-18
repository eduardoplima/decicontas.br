"""Reusing a previous run's configuration in the k-fold orchestrator."""

from __future__ import annotations

import json

from research.kfold.orchestrate import config_from_summary


def test_config_from_summary_reads_the_selected_configuration(tmp_path):
    cfg = {"model_name": "x/y", "lr": 5e-05, "warmup_ratio": 0.1, "stride": 320}
    (tmp_path / "cv_x_y.json").write_text(json.dumps({"model": "x/y", "config": cfg}))
    assert config_from_summary(tmp_path, "x/y") == cfg
