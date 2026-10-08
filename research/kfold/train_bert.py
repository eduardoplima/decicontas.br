"""Single-process BERT-style trainer for one (model, config, fold) pair.

Mirrors :mod:`train_bilstm`: read a JSON payload from stdin, train one model
on the requested split, write a result JSON line on stdout. The orchestrator
wraps each call in a subprocess so MPS memory is fully released between runs.
"""

from __future__ import annotations

import gc
import json
import os
import sys
import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
from torch.utils.data import Dataset

os.environ.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.0")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("WANDB_DISABLED", "true")
warnings.filterwarnings("ignore")

from .config import SEED  # noqa: E402
from .data import grid_split, kfold_splits, label_set, load_bio_samples  # noqa: E402
from .metrics import evaluate_oof  # noqa: E402
from .windows import Window, build_windows, merge_window_predictions  # noqa: E402


def _set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)


def checkpoint_dir(pid: int | None = None) -> str:
    """Scratch directory for the HF Trainer's per-epoch checkpoints.

    Defaults to ``/tmp``; ``DECICONTAS_TMP_DIR`` redirects it (e.g. to an external
    volume — bert-large rotates two ~4 GB checkpoints per epoch). Removed after
    each run.
    """
    base = os.environ.get("DECICONTAS_TMP_DIR", "/tmp")
    return os.path.join(base, f"decicontas_bert_{pid if pid is not None else os.getpid()}")


# Checkpoints with a sentence-transformers layout keep the encoder in a
# subfolder; the root config.json is not a model config.
HUB_SUBFOLDER: dict[str, str] = {
    "ulysses-camara/legal-bert-pt-br": "0_Transformer",
}


@dataclass
class BertConfig:
    model_name: str = "neuralmind/bert-base-portuguese-cased"
    lr: float = 3e-5
    warmup_ratio: float = 0.1
    epochs: int = 10
    per_device_batch_size: int = 2
    grad_accum: int = 8
    weight_decay: float = 0.01
    max_grad_norm: float = 1.0
    # Igual ao número de épocas: desativa na prática a parada antecipada.
    # Com a métrica estrita, F1 legitimamente vale 0 nas primeiras épocas de um
    # modelo que ainda não aprendeu a emitir tags de abertura; com paciência 5 o
    # treino era interrompido na época 6 antes que ele aprendesse. Nove dos dez
    # modelos já rodavam as 10 épocas, então isto uniformiza o orçamento de
    # treino em vez de privilegiar um modelo.
    early_stopping_patience: int = 10
    max_length: int = 512
    # Sliding window over documents longer than ``max_length`` subwords: windows
    # of 512 subwords overlapping by ``stride``. With 320 the longest gold entity
    # of the corpus (408 subwords) still fits whole inside at least one window
    # (guarded by tests/test_kfold_windows.py); 128 would leave seven entities
    # split in every window they touch.
    stride: int = 320


class _TokenDataset(Dataset):
    """One item per *window*, not per document (see :mod:`research.kfold.windows`)."""

    def __init__(self, samples: list[dict[str, Any]], tokenizer, label2id: dict[str, int],
                 max_length: int, stride: int) -> None:
        self.samples = samples
        self.windows: list[Window] = []
        for doc_idx, s in enumerate(samples):
            self.windows.extend(build_windows(
                s["tokens"], s["labels"], tokenizer, label2id,
                max_length=max_length, stride=stride, doc_idx=doc_idx,
            ))

    def __len__(self) -> int:
        return len(self.windows)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        w = self.windows[idx]
        item = {
            "input_ids": w.input_ids,
            "attention_mask": w.attention_mask,
            "labels": w.labels,
        }
        if w.token_type_ids is not None:
            item["token_type_ids"] = w.token_type_ids
        return {k: torch.tensor(v) for k, v in item.items()}


def _split_indices(samples, mode: str, fold_idx: int) -> tuple[list[int], list[int], list[int]]:
    if mode == "grid":
        train_full, dev_idx = grid_split(samples)
        rng = np.random.default_rng(SEED)
        train_arr = np.array(train_full)
        rng.shuffle(train_arr)
        val_size = max(1, len(train_arr) // 9)
        val_idx = train_arr[:val_size].tolist()
        train_idx = train_arr[val_size:].tolist()
        return train_idx, val_idx, dev_idx
    if mode == "cv":
        folds = kfold_splits(samples)
        train_val_idx, test_idx = folds[fold_idx]
        rng = np.random.default_rng(SEED + fold_idx)
        train_val = np.array(train_val_idx)
        rng.shuffle(train_val)
        val_size = max(1, len(train_val) // 9)
        val_idx = train_val[:val_size].tolist()
        train_idx = train_val[val_size:].tolist()
        return train_idx, val_idx, test_idx
    raise ValueError(f"unknown mode: {mode}")


def train_one(cfg: BertConfig, mode: str, fold_idx: int) -> dict[str, Any]:
    from transformers import (
        AutoModelForTokenClassification,
        AutoTokenizer,
        DataCollatorForTokenClassification,
        EarlyStoppingCallback,
        Trainer,
        TrainingArguments,
    )
    from seqeval.metrics import f1_score as seq_f1
    from seqeval.metrics import precision_score as seq_p
    from seqeval.metrics import recall_score as seq_r
    from seqeval.scheme import IOB2

    _set_seed(SEED)
    samples = load_bio_samples()
    _, label2id, id2label = label_set(samples)

    train_idx, val_idx, test_idx = _split_indices(samples, mode, fold_idx)
    train_data = [samples[i] for i in train_idx]
    val_data = [samples[i] for i in val_idx]
    test_data = [samples[i] for i in test_idx]

    subfolder = HUB_SUBFOLDER.get(cfg.model_name, "")
    tokenizer = AutoTokenizer.from_pretrained(cfg.model_name, subfolder=subfolder)
    model = AutoModelForTokenClassification.from_pretrained(
        cfg.model_name,
        subfolder=subfolder,
        num_labels=len(label2id),
        id2label=id2label,
        label2id=label2id,
        ignore_mismatched_sizes=True,
    )

    train_ds = _TokenDataset(train_data, tokenizer, label2id, cfg.max_length, cfg.stride)
    val_ds = _TokenDataset(val_data, tokenizer, label2id, cfg.max_length, cfg.stride)
    test_ds = _TokenDataset(test_data, tokenizer, label2id, cfg.max_length, cfg.stride)

    def _compute_metrics(eval_pred):
        preds, labs = eval_pred
        preds = np.argmax(preds, axis=2)
        true_seqs, pred_seqs = [], []
        for p_seq, l_seq in zip(preds, labs):
            t, q = [], []
            for p_, l_ in zip(p_seq, l_seq):
                if l_ != -100:
                    t.append(id2label[int(l_)])
                    q.append(id2label[int(p_)])
            true_seqs.append(t)
            pred_seqs.append(q)
        # Strict IOB2, matching the decoder that scores the released results
        # (:func:`research.ner_metrics.extract_spans_from_bio`, which requires a
        # ``B-`` to open a span). seqeval's default scheme is lenient: it treats
        # a leading ``I-X`` as a span start, so an all-``I-`` sequence scores
        # 1.0 there and 0.0 under the reporting decoder. Selecting checkpoints
        # with the lenient metric picked models that never emit ``B-`` at all,
        # which is what produced the fold collapses to F1 = 0.
        strict = dict(mode="strict", scheme=IOB2, zero_division=0)
        return {
            "f1": seq_f1(true_seqs, pred_seqs, **strict),
            "precision": seq_p(true_seqs, pred_seqs, **strict),
            "recall": seq_r(true_seqs, pred_seqs, **strict),
        }

    output_dir = checkpoint_dir()
    args = TrainingArguments(
        output_dir=output_dir,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=cfg.lr,
        per_device_train_batch_size=cfg.per_device_batch_size,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=cfg.grad_accum,
        num_train_epochs=cfg.epochs,
        weight_decay=cfg.weight_decay,
        warmup_ratio=cfg.warmup_ratio,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        save_total_limit=1,
        logging_steps=50,
        fp16=False,
        bf16=False,
        gradient_checkpointing=True,
        max_grad_norm=cfg.max_grad_norm,
        dataloader_pin_memory=False,
        dataloader_num_workers=0,
        eval_accumulation_steps=1,
        report_to="none",
        seed=SEED,
        disable_tqdm=True,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=DataCollatorForTokenClassification(tokenizer, padding=True),
        compute_metrics=_compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=cfg.early_stopping_patience)],
    )
    trainer.train()

    # Predictions come back one row per *window* (padded to the longest window in
    # each batch). Group the rows by document and merge them into one word-level
    # sequence per document; the gold is the full document, never a truncation.
    pred_out = trainer.predict(test_ds)
    preds_arr = np.argmax(pred_out.predictions, axis=2)
    assert preds_arr.shape[0] == len(test_ds.windows)

    per_doc: dict[int, list[tuple[list[int | None], list[str]]]] = {}
    for row, w in zip(preds_arr, test_ds.windows):
        labels_row = [id2label[int(p_)] for p_ in row[: len(w.word_ids)]]
        per_doc.setdefault(w.doc_idx, []).append((w.word_ids, labels_row))

    pred_bio: list[list[str]] = []
    true_bio: list[list[str]] = []
    for local_i, s in enumerate(test_data):
        pred_bio.append(merge_window_predictions(len(s["tokens"]), per_doc.get(local_i, [])))
        true_bio.append(list(s["labels"]))

    metrics = evaluate_oof(samples, test_idx, true_bio, pred_bio, model_name=cfg.model_name)

    del trainer, model, tokenizer
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

    # best-effort cleanup of HF intermediate checkpoints
    try:
        import shutil
        shutil.rmtree(output_dir, ignore_errors=True)
    except Exception:
        pass

    return {
        "config": cfg.__dict__,
        "mode": mode,
        "fold_idx": fold_idx,
        "test_indices": test_idx,
        "true_labels": true_bio,
        "pred_labels": pred_bio,
        "metrics": metrics,
    }


def main() -> None:
    payload = json.loads(sys.stdin.read())
    cfg = BertConfig(**payload["config"])
    out = train_one(cfg, mode=payload["mode"], fold_idx=int(payload.get("fold_idx", -1)))
    sys.stdout.write(json.dumps(out) + "\n")


if __name__ == "__main__":
    main()
