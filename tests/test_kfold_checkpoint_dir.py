"""The BERT trainer's transient HF checkpoints go to ``DECICONTAS_TMP_DIR`` when set.

The internal disk filled up mid-run (each bert-large epoch rotates two ~4 GB
checkpoints), so the scratch location must be redirectable to an external volume
without touching the results tree.
"""

from __future__ import annotations


def test_checkpoint_dir_defaults_to_tmp_with_pid(monkeypatch):
    from research.kfold.train_bert import checkpoint_dir

    monkeypatch.delenv("DECICONTAS_TMP_DIR", raising=False)
    assert checkpoint_dir(pid=4242) == "/tmp/decicontas_bert_4242"


def test_checkpoint_dir_honours_decicontas_tmp_dir(monkeypatch):
    from research.kfold.train_bert import checkpoint_dir

    monkeypatch.setenv("DECICONTAS_TMP_DIR", "/Volumes/PortableSSD/decicontas/tmp")
    assert checkpoint_dir(pid=4242) == "/Volumes/PortableSSD/decicontas/tmp/decicontas_bert_4242"
