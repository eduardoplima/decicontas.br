"""Sliding windows for encoders with a fixed subword budget.

Encoders cap their input at ``max_length`` subwords (512 for every model in the
protocol). Instead of truncating a long decision, each document is split into
overlapping windows (``return_overflowing_tokens`` with ``stride``), every window
is trained on / predicted independently, and the per-window predictions are
merged back into one word-level BIO sequence per document.

Two conventions are fixed here and shared by training and inference:

* **Label alignment** (unchanged from the truncated protocol): special tokens get
  ``-100``; the first subword of a word gets the word's label; continuation
  subwords get ``I-X`` when the word label is ``B-X`` and the same label otherwise.
* **Overlap policy** (:func:`merge_window_predictions`): for a word covered by more
  than one window, the prediction of the window in which the word's first subword
  lies farthest from either edge wins; ties go to the earlier window.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Window:
    doc_idx: int
    input_ids: list[int]
    attention_mask: list[int]
    word_ids: list[int | None]
    labels: list[int]
    token_type_ids: list[int] | None = field(default=None)


def align_labels(word_ids: list[int | None], labels: list[str], label2id: dict[str, int]) -> list[int]:
    aligned: list[int] = []
    prev: int | None = None
    for wid in word_ids:
        if wid is None:
            aligned.append(-100)
        elif wid != prev:
            aligned.append(label2id[labels[wid]])
        else:
            lbl = labels[wid]
            aligned.append(label2id["I-" + lbl[2:]] if lbl.startswith("B-") else label2id[lbl])
        prev = wid
    return aligned


def build_windows(
    tokens: list[str],
    labels: list[str],
    tokenizer: Any,
    label2id: dict[str, int],
    *,
    max_length: int,
    stride: int,
    doc_idx: int,
) -> list[Window]:
    """Tokenise one document into overlapping windows of at most ``max_length`` subwords."""
    enc = tokenizer(
        tokens,
        is_split_into_words=True,
        max_length=max_length,
        stride=stride,
        truncation=True,
        padding=False,
        return_overflowing_tokens=True,
    )
    windows: list[Window] = []
    for j in range(len(enc["input_ids"])):
        word_ids = enc.word_ids(j)
        windows.append(
            Window(
                doc_idx=doc_idx,
                input_ids=list(enc["input_ids"][j]),
                attention_mask=list(enc["attention_mask"][j]),
                word_ids=list(word_ids),
                labels=align_labels(word_ids, labels, label2id),
                token_type_ids=list(enc["token_type_ids"][j]) if "token_type_ids" in enc else None,
            )
        )
    return windows


def merge_window_predictions(
    n_tokens: int,
    windows: list[tuple[list[int | None], list[str]]],
) -> list[str]:
    """Reduce per-window subword predictions to one label per word of the document.

    ``windows`` holds ``(word_ids, predicted_labels)`` pairs of equal length, one
    per window of the same document. Only the first subword of each word carries
    the word's prediction. Words no window covers stay ``"O"``.
    """
    merged = ["O"] * n_tokens
    best_margin = [-1] * n_tokens
    for word_ids, preds in windows:
        last = len(word_ids) - 1
        prev: int | None = None
        for pos, wid in enumerate(word_ids):
            if wid is not None and wid != prev:
                margin = min(pos, last - pos)
                if margin > best_margin[wid]:
                    best_margin[wid] = margin
                    merged[wid] = preds[pos]
            prev = wid
    return merged
