"""Entity recognition with a model saved by :mod:`train_final` (first stage of the pipeline).

Same input handling as training and evaluation: whitespace tokens, sliding
windows of ``max_length`` subwords with ``stride`` overlap, per-window
predictions merged by :func:`research.kfold.windows.merge_window_predictions`,
and strict IOB2 decoding. Each span comes back with its character offsets.

    uv run python -m research.kfold.infer --model /path/to/legalbertpt_fp-decicontas < decisao.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from research.dataset_io import token_offsets
from research.ner_metrics import extract_spans_from_bio

from .windows import build_windows, merge_window_predictions


def bio_to_char_spans(text: str, tags: list[str]) -> list[dict[str, Any]]:
    """Word-level BIO tags (one per whitespace token of ``text``) to character spans."""
    offsets = token_offsets(text)
    spans = []
    for s, e, label in extract_spans_from_bio(tags):
        cs, ce = offsets[s][0], offsets[e - 1][1]
        spans.append({"label": label, "start": cs, "end": ce, "text": text[cs:ce],
                      "token_start": s, "token_end": e})
    return spans


class Recognizer:
    """Loads the model once; :meth:`__call__` returns the spans of one decision."""

    def __init__(self, model_dir: str | Path, device: str | None = None):
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        model_dir = Path(model_dir)
        meta_path = model_dir / "training.json"
        cfg = json.loads(meta_path.read_text(encoding="utf-8"))["config"] if meta_path.exists() else {}
        self.max_length = int(cfg.get("max_length", 512))
        self.stride = int(cfg.get("stride", 320))
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForTokenClassification.from_pretrained(model_dir)
        if device is None:
            device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.model.to(device).eval()
        self.id2label = {int(k): v for k, v in self.model.config.id2label.items()}
        self.label2id = {v: k for k, v in self.id2label.items()}

    def tags(self, text: str) -> list[str]:
        import torch

        words = [text[s:e] for s, e in token_offsets(text)]
        if not words:
            return []
        windows = build_windows(words, ["O"] * len(words), self.tokenizer, self.label2id,
                                max_length=self.max_length, stride=self.stride, doc_idx=0)
        per_window = []
        with torch.no_grad():
            for w in windows:
                batch = {"input_ids": torch.tensor([w.input_ids], device=self.device),
                         "attention_mask": torch.tensor([w.attention_mask], device=self.device)}
                if w.token_type_ids is not None:
                    batch["token_type_ids"] = torch.tensor([w.token_type_ids], device=self.device)
                ids = self.model(**batch).logits[0].argmax(-1).tolist()
                per_window.append((w.word_ids, [self.id2label[i] for i in ids]))
        return merge_window_predictions(len(words), per_window)

    def __call__(self, text: str) -> list[dict[str, Any]]:
        return bio_to_char_spans(text, self.tags(text))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", required=True, type=Path)
    p.add_argument("--device")
    args = p.parse_args()
    rec = Recognizer(args.model, args.device)
    print(json.dumps(rec(sys.stdin.read()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
