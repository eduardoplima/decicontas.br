"""Single-process BiLSTM-CRF trainer for one (config, fold) pair.

Runnable as ``python -m research.kfold.train_bilstm`` so the
orchestrator can spawn one subprocess per training run and let MPS reclaim
memory between runs.

Inputs are passed as a single JSON blob on stdin. The trainer prints a result
JSON line on stdout containing the fitted span/token F1 plus the indexed BIO
predictions on the held-out split.
"""

from __future__ import annotations

import gc
import json
import os
import sys
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader, Dataset

# Lower MPS memory pressure before any tensor is allocated
os.environ.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.0")

from .config import SEED  # noqa: E402
from .data import grid_split, kfold_splits, label_set, load_bio_samples  # noqa: E402
from .embeddings import EMBEDDING_DIM, build_embedding_matrix, build_vocab  # noqa: E402
from .metrics import evaluate_oof  # noqa: E402


def _set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)


def _device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


@dataclass
class BiLSTMConfig:
    hidden_dim: int = 256
    dropout: float = 0.5
    lr: float = 1e-3
    weight_decay: float = 1e-4
    batch_size: int = 8
    max_epochs: int = 50
    patience: int = 10
    grad_clip: float = 5.0
    max_len: int = 512


class _SeqDataset(Dataset):
    def __init__(self, samples: list[dict[str, Any]], word2id: dict[str, int],
                 label2id: dict[str, int], max_len: int) -> None:
        self.samples = samples
        self.word2id = word2id
        self.label2id = label2id
        self.max_len = max_len

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, i: int) -> dict[str, torch.Tensor]:
        s = self.samples[i]
        toks = s["tokens"][: self.max_len]
        labs = s["labels"][: self.max_len]
        unk = self.word2id["<UNK>"]
        ids = [self.word2id.get(t.lower(), unk) for t in toks]
        return {
            "input_ids": torch.tensor(ids, dtype=torch.long),
            "labels": torch.tensor([self.label2id[l] for l in labs], dtype=torch.long),
            "length": len(ids),
        }


def _collate(batch: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    n = len(batch)
    L = max(b["length"] for b in batch)
    input_ids = torch.zeros(n, L, dtype=torch.long)
    labels = torch.zeros(n, L, dtype=torch.long)
    mask = torch.zeros(n, L, dtype=torch.bool)
    for i, b in enumerate(batch):
        l = b["length"]
        input_ids[i, :l] = b["input_ids"]
        labels[i, :l] = b["labels"]
        mask[i, :l] = True
    return {"input_ids": input_ids, "labels": labels, "mask": mask}


class BiLSTMCRF(nn.Module):
    def __init__(self, embedding_matrix: np.ndarray, hidden_dim: int, num_labels: int, dropout: float) -> None:
        from torchcrf import CRF

        super().__init__()
        vocab_size, embed_dim = embedding_matrix.shape
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.embedding.weight.data.copy_(torch.from_numpy(embedding_matrix))
        self.embedding.weight.requires_grad = False  # frozen pre-trained vectors
        self.lstm = nn.LSTM(
            embed_dim, hidden_dim // 2, num_layers=2,
            bidirectional=True, batch_first=True, dropout=dropout,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, num_labels)
        self.crf = CRF(num_labels, batch_first=True)

    def forward(self, input_ids, labels=None, mask=None):
        embeds = self.dropout(self.embedding(input_ids))
        lstm_out, _ = self.lstm(embeds)
        emissions = self.fc(self.dropout(lstm_out))
        if labels is not None:
            return -self.crf(emissions, labels, mask=mask, reduction="mean")
        return self.crf.decode(emissions, mask=mask)


def _split_indices(samples, mode: str, fold_idx: int) -> tuple[list[int], list[int], list[int]]:
    if mode == "grid":
        train_full, dev_idx = grid_split(samples)
        # carve a small val out of train_full for early stopping
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


def train_one(cfg: BiLSTMConfig, mode: str, fold_idx: int) -> dict[str, Any]:
    _set_seed(SEED)
    samples = load_bio_samples()
    _, label2id, id2label = label_set(samples)
    vocab, word2id = build_vocab(samples)
    matrix, vec_hits = build_embedding_matrix(vocab)

    train_idx, val_idx, test_idx = _split_indices(samples, mode, fold_idx)
    train_data = [samples[i] for i in train_idx]
    val_data = [samples[i] for i in val_idx]
    test_data = [samples[i] for i in test_idx]

    device = _device()
    model = BiLSTMCRF(matrix, cfg.hidden_dim, len(label2id), cfg.dropout).to(device)
    optimizer = AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=cfg.lr, weight_decay=cfg.weight_decay,
    )
    scheduler = ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=3)

    train_loader = DataLoader(
        _SeqDataset(train_data, word2id, label2id, cfg.max_len),
        batch_size=cfg.batch_size, shuffle=True, collate_fn=_collate,
    )
    val_loader = DataLoader(
        _SeqDataset(val_data, word2id, label2id, cfg.max_len),
        batch_size=cfg.batch_size, shuffle=False, collate_fn=_collate,
    )

    best_val = float("inf")
    best_state: dict[str, torch.Tensor] | None = None
    bad_epochs = 0
    epochs_run = 0

    for epoch in range(cfg.max_epochs):
        model.train()
        for batch in train_loader:
            optimizer.zero_grad()
            loss = model(
                batch["input_ids"].to(device),
                batch["labels"].to(device),
                batch["mask"].to(device),
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
            optimizer.step()

        model.eval()
        v_loss = 0.0
        with torch.no_grad():
            for batch in val_loader:
                loss = model(
                    batch["input_ids"].to(device),
                    batch["labels"].to(device),
                    batch["mask"].to(device),
                )
                v_loss += float(loss.item())
        v_loss = v_loss / max(1, len(val_loader))
        scheduler.step(v_loss)
        epochs_run = epoch + 1

        if v_loss < best_val:
            best_val = v_loss
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            bad_epochs = 0
        else:
            bad_epochs += 1
        if bad_epochs >= cfg.patience:
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()

    pred_bio: list[list[str]] = []
    true_bio: list[list[str]] = []
    with torch.no_grad():
        for s in test_data:
            toks = s["tokens"][: cfg.max_len]
            true_bio.append(s["labels"][: cfg.max_len])
            ids = torch.tensor(
                [[word2id.get(t.lower(), word2id["<UNK>"]) for t in toks]],
                dtype=torch.long,
            ).to(device)
            mask = torch.ones_like(ids, dtype=torch.bool).to(device)
            pred_ids = model(ids, mask=mask)[0]
            pred_bio.append([id2label[p] for p in pred_ids])

    metrics = evaluate_oof(samples, test_idx, true_bio, pred_bio, model_name="bilstm-crf")

    del model, optimizer, scheduler
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

    return {
        "config": cfg.__dict__,
        "mode": mode,
        "fold_idx": fold_idx,
        "epochs_run": epochs_run,
        "best_val_loss": best_val,
        "embedding_hits": vec_hits,
        "embedding_vocab": len(vocab),
        "test_indices": test_idx,
        "true_labels": true_bio,
        "pred_labels": pred_bio,
        "metrics": metrics,
    }


def main() -> None:
    payload = json.loads(sys.stdin.read())
    cfg = BiLSTMConfig(**payload["config"])
    out = train_one(cfg, mode=payload["mode"], fold_idx=int(payload.get("fold_idx", -1)))
    sys.stdout.write(json.dumps(out) + "\n")


if __name__ == "__main__":
    main()
