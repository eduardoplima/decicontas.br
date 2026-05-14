"""Data loading, BIO conversion, fold/dev splits for supervised NER.

The dataset is loaded via :func:`research.dataset.get_decicontas_df` (which already
excludes the leaked few-shot ids — see ``tools/fewshot.py``). All 861 documents
are kept; unannotated ones contribute all-O sequences so the supervised models
see the same document distribution that the LLMs were evaluated on.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.model_selection import KFold, train_test_split

from research.dataset import get_decicontas_df

from .config import DATASET_PATH, N_FOLDS, SEED


@dataclass
class BioSample:
    tokens: list[str]
    labels: list[str]
    token_offsets: list[dict[str, int]]
    text: str
    spans: list[dict[str, Any]]


def _tokenize(text: str) -> list[dict[str, Any]]:
    return [{"text": m.group(), "start": m.start(), "end": m.end()} for m in re.finditer(r"\S+", text)]


def _spans_to_bio(tokens: list[dict[str, Any]], spans: list[dict[str, Any]]) -> list[str]:
    labels = ["O"] * len(tokens)
    for span in spans:
        s_start, s_end, s_label = span["start"], span["end"], span["label"]
        first = True
        for i, tok in enumerate(tokens):
            if tok["start"] < s_end and tok["end"] > s_start:
                labels[i] = f"B-{s_label}" if first else f"I-{s_label}"
                first = False
    return labels


def load_bio_samples() -> list[dict[str, Any]]:
    df = get_decicontas_df(path=DATASET_PATH)
    samples: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        text = row["data"]["text"]
        annotations = row["annotations"]
        results: list[dict[str, Any]] = []
        for ann in annotations:
            if isinstance(ann, dict) and "result" in ann:
                results.extend(ann["result"])
            elif isinstance(ann, dict) and "value" in ann:
                results.append(ann)
        spans: list[dict[str, Any]] = []
        for r in results:
            if "value" in r and "labels" in r["value"]:
                v = r["value"]
                spans.append({"start": v["start"], "end": v["end"], "label": v["labels"][0]})
        tokens = _tokenize(text)
        labels = _spans_to_bio(tokens, spans)
        samples.append(
            {
                "tokens": [t["text"] for t in tokens],
                "token_offsets": tokens,
                "labels": labels,
                "text": text,
                "spans": spans,
            }
        )
    return samples


def label_set(samples: list[dict[str, Any]]) -> tuple[list[str], dict[str, int], dict[int, str]]:
    """Return the sorted unique BIO label vocabulary and id<->label dicts."""
    all_labels = [lbl for s in samples for lbl in s["labels"]]
    unique = sorted(set(all_labels))
    label2id = {l: i for i, l in enumerate(unique)}
    id2label = {i: l for l, i in label2id.items()}
    return unique, label2id, id2label


def grid_split(samples: list[dict[str, Any]], dev_ratio: float = 0.20) -> tuple[list[int], list[int]]:
    """Fixed 80/20 train/dev indices for hyperparameter selection.

    The split is stratified by whether the document carries any annotation, so
    train and dev keep the same proportion of annotated docs as the full set.
    """
    has_ann = np.array([1 if s["spans"] else 0 for s in samples])
    idx = np.arange(len(samples))
    train_idx, dev_idx = train_test_split(
        idx, test_size=dev_ratio, random_state=SEED, stratify=has_ann
    )
    return train_idx.tolist(), dev_idx.tolist()


def kfold_splits(samples: list[dict[str, Any]]) -> list[tuple[list[int], list[int]]]:
    """5-fold splits over all documents, with seed pinned for reproducibility."""
    kf = KFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    return [(train.tolist(), test.tolist()) for train, test in kf.split(samples)]


def label_counts(samples: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(lbl for s in samples for lbl in s["labels"]))
