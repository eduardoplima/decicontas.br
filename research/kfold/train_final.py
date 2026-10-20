"""Train one encoder on the whole corpus and save it for production use.

Unlike :mod:`train_bert` (one fold, weights discarded), this trains on every
document with a fixed number of epochs — there is no held-out split left for
early stopping — and writes the model, the tokenizer and a ``training.json``
with the configuration and the corpus fingerprint.

    DECICONTAS_DATASET_PATH=dataset/release/decicontas-adjudicated/decicontas/decicontas-labelstudio.json \\
    uv run python -m research.kfold.train_final \\
        --model raquelsilveira/legalbertpt_fp --lr 5e-5 --warmup 0.1 --epochs 8 \\
        --out /Volumes/PortableSSD/decicontas/models/legalbertpt_fp-decicontas
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .config import DATASET_PATH, REPO_ROOT, SEED
from .data import label_set, load_bio_samples
from .train_bert import HUB_SUBFOLDER, BertConfig, _set_seed, _TokenDataset, checkpoint_dir


def _sha256(path: str | None) -> str | None:
    if not path or not Path(path).exists():
        return None
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def train_final(cfg: BertConfig, out_dir: Path) -> dict:
    from transformers import (
        AutoModelForTokenClassification,
        AutoTokenizer,
        DataCollatorForTokenClassification,
        Trainer,
        TrainingArguments,
    )

    _set_seed(SEED)
    samples = load_bio_samples()
    _, label2id, id2label = label_set(samples)

    subfolder = HUB_SUBFOLDER.get(cfg.model_name, "")
    tokenizer = AutoTokenizer.from_pretrained(cfg.model_name, subfolder=subfolder)
    model = AutoModelForTokenClassification.from_pretrained(
        cfg.model_name, subfolder=subfolder, num_labels=len(label2id),
        id2label=id2label, label2id=label2id, ignore_mismatched_sizes=True,
    )
    train_ds = _TokenDataset(samples, tokenizer, label2id, cfg.max_length, cfg.stride)

    args = TrainingArguments(
        output_dir=checkpoint_dir(),
        eval_strategy="no",
        save_strategy="no",
        learning_rate=cfg.lr,
        per_device_train_batch_size=cfg.per_device_batch_size,
        gradient_accumulation_steps=cfg.grad_accum,
        num_train_epochs=cfg.epochs,
        weight_decay=cfg.weight_decay,
        warmup_ratio=cfg.warmup_ratio,
        logging_steps=50,
        gradient_checkpointing=True,
        max_grad_norm=cfg.max_grad_norm,
        dataloader_pin_memory=False,
        dataloader_num_workers=0,
        report_to="none",
        seed=SEED,
        disable_tqdm=True,
    )
    trainer = Trainer(
        model=model, args=args, train_dataset=train_ds,
        data_collator=DataCollatorForTokenClassification(tokenizer, padding=True),
    )
    result = trainer.train()

    out_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    meta = {
        "base_model": cfg.model_name,
        "config": cfg.__dict__,
        "documents": len(samples),
        "windows": len(train_ds),
        "labels": sorted(label2id),
        "dataset_path": DATASET_PATH,
        "dataset_sha256": _sha256(DATASET_PATH),
        "git_commit": _git_commit(),
        "seed": SEED,
        "train_loss": result.training_loss,
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (out_dir / "training.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", required=True)
    p.add_argument("--lr", type=float, required=True)
    p.add_argument("--warmup", type=float, required=True)
    p.add_argument("--epochs", type=int, required=True)
    p.add_argument("--stride", type=int, default=320)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if not DATASET_PATH:
        raise SystemExit("set DECICONTAS_DATASET_PATH to the release Label Studio JSON to train on")
    os.environ.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.0")
    cfg = BertConfig(model_name=args.model, lr=args.lr, warmup_ratio=args.warmup,
                     epochs=args.epochs, stride=args.stride)
    meta = train_final(cfg, args.out)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
