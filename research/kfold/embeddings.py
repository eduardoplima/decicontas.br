"""Build a frozen embedding matrix from spaCy ``pt_core_news_lg``.

The vectors are 300-dimensional, trained with Floret on Portuguese news
(spaCy 3.x, ``pt_core_news_lg``). Words missing from the spaCy vocab fall back
to a small zero-mean random vector so the model can still differentiate them.
"""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
from typing import Any

import numpy as np
import spacy

from .config import SEED

EMBEDDING_DIM = 300


@lru_cache(maxsize=1)
def _load_nlp():
    return spacy.load("pt_core_news_lg")


def build_vocab(samples: list[dict[str, Any]]) -> tuple[list[str], dict[str, int]]:
    """Return ``(vocab, word2id)`` covering every observed lowercased token."""
    counter = Counter(t.lower() for s in samples for t in s["tokens"])
    vocab = ["<PAD>", "<UNK>"] + [w for w, _ in counter.most_common()]
    word2id = {w: i for i, w in enumerate(vocab)}
    return vocab, word2id


def build_embedding_matrix(vocab: list[str]) -> tuple[np.ndarray, int]:
    """Return ``(matrix, hits)`` where matrix[i] is the spaCy vector for vocab[i].

    ``<PAD>`` is zero. Out-of-spaCy tokens (including ``<UNK>``) get a small
    Gaussian vector seeded with ``SEED`` so runs are reproducible.
    """
    nlp = _load_nlp()
    rng = np.random.default_rng(SEED)
    matrix = rng.normal(0.0, 0.1, size=(len(vocab), EMBEDDING_DIM)).astype(np.float32)
    matrix[0] = 0.0  # <PAD>
    hits = 0
    for i, w in enumerate(vocab):
        if w in ("<PAD>", "<UNK>"):
            continue
        lex = nlp.vocab[w]
        if lex.has_vector and lex.vector_norm > 0:
            matrix[i] = lex.vector.astype(np.float32)
            hits += 1
    return matrix, hits
