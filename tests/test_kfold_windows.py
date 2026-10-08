"""Sliding-window input for the supervised k-fold.

Encoders are capped at 512 subwords. Instead of truncating long decisions, the
trainer splits each document into overlapping windows (``research.kfold.windows``),
trains/predicts on windows and merges the per-window predictions back to one
word-level BIO sequence per document. These tests pin down that contract and the
two corpus-level guarantees the dissertation states: every gold entity fits in at
least one window, and the BiLSTM-CRF sees every document whole.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RELEASE_LS = REPO / "dataset" / "release" / "decicontas" / "decicontas-labelstudio.json"
TOKENIZER_NAME = "neuralmind/bert-base-portuguese-cased"

LABELS = ["O", "B-MULTA", "I-MULTA", "B-OBRIGACAO", "I-OBRIGACAO"]
LABEL2ID = {lab: i for i, lab in enumerate(LABELS)}


@pytest.fixture(scope="module")
def tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(TOKENIZER_NAME)


@pytest.fixture(scope="module")
def corpus_samples():
    import research.kfold.data as kdata

    previous = kdata.DATASET_PATH
    kdata.DATASET_PATH = str(RELEASE_LS)
    try:
        return kdata.load_bio_samples()
    finally:
        kdata.DATASET_PATH = previous


def _long_doc(n_words: int = 1200) -> tuple[list[str], list[str]]:
    # "ressarcimento" splits into several subwords, so 1200 words >> 512 subwords.
    tokens = ["ressarcimento" if i % 3 else "R$" for i in range(n_words)]
    return tokens, ["O"] * n_words


# --------------------------------------------------------------------------- build_windows


def test_windows_cover_every_word_of_a_long_document(tokenizer):
    from research.kfold.windows import build_windows

    tokens, labels = _long_doc()
    windows = build_windows(tokens, labels, tokenizer, LABEL2ID,
                            max_length=512, stride=320, doc_idx=7)

    assert len(windows) > 1
    assert all(len(w.input_ids) <= 512 for w in windows)
    assert all(len(w.input_ids) == len(w.word_ids) == len(w.labels) for w in windows)
    covered = {wid for w in windows for wid in w.word_ids if wid is not None}
    assert covered == set(range(len(tokens)))
    assert {w.doc_idx for w in windows} == {7}


def test_short_document_yields_a_single_window(tokenizer):
    from research.kfold.windows import build_windows

    windows = build_windows(["aplicar", "multa"], ["O", "B-MULTA"], tokenizer, LABEL2ID,
                            max_length=512, stride=320, doc_idx=0)
    assert len(windows) == 1


def test_window_labels_follow_the_subword_convention(tokenizer):
    """Specials -> -100; first subword -> word label; continuations of B-X -> I-X."""
    from research.kfold.windows import build_windows

    tokens = ["aplicar", "ressarcimento", "ressarcimento"]
    labels = ["O", "B-MULTA", "I-MULTA"]
    [w] = build_windows(tokens, labels, tokenizer, LABEL2ID,
                        max_length=512, stride=320, doc_idx=0)

    assert w.labels[0] == -100 and w.labels[-1] == -100
    seen: set[int] = set()
    for wid, lab in zip(w.word_ids, w.labels):
        if wid is None:
            continue
        if wid not in seen:
            assert lab == LABEL2ID[labels[wid]]
            seen.add(wid)
        elif labels[wid].startswith("B-"):
            assert lab == LABEL2ID["I-" + labels[wid][2:]]
        else:
            assert lab == LABEL2ID[labels[wid]]
    assert len(seen) == 3
    # the multi-subword words really did produce continuations
    assert len(w.word_ids) > 5


# ------------------------------------------------------------------ merge_window_predictions


def test_merge_keeps_prediction_of_the_window_where_the_word_is_farthest_from_an_edge():
    from research.kfold.windows import merge_window_predictions

    # window A covers words 0..3 (word 3 sits one position from its edge),
    # window B covers words 2..5 (word 3 sits two positions from either edge).
    window_a = ([None, 0, 1, 2, 3, None], ["O", "O", "O", "B-OBRIGACAO", "B-MULTA", "O"])
    window_b = ([None, 2, 3, 4, 5, None], ["O", "O", "O", "O", "O", "O"])

    merged = merge_window_predictions(6, [window_a, window_b])

    assert merged[3] == "O"            # B wins word 3 (margin 2 > 1)
    assert merged[2] == "B-OBRIGACAO"  # A wins word 2 (margin 2 > 1)
    assert merged == ["O", "O", "B-OBRIGACAO", "O", "O", "O"]


def test_merge_fills_words_covered_by_no_window_with_O():
    from research.kfold.windows import merge_window_predictions

    merged = merge_window_predictions(4, [([None, 0, 1, None], ["O", "B-MULTA", "I-MULTA", "O"])])
    assert merged == ["B-MULTA", "I-MULTA", "O", "O"]


def test_merge_uses_the_first_subword_prediction_of_each_word():
    from research.kfold.windows import merge_window_predictions

    merged = merge_window_predictions(1, [([None, 0, 0, 0, None], ["O", "B-MULTA", "I-MULTA", "O", "O"])])
    assert merged == ["B-MULTA"]


# ------------------------------------------------------------------------------ trainers


def test_token_dataset_length_is_the_number_of_windows(tokenizer):
    from research.kfold.train_bert import _TokenDataset
    from research.kfold.windows import build_windows

    long_tokens, long_labels = _long_doc()
    samples = [
        {"tokens": ["aplicar", "multa"], "labels": ["O", "B-MULTA"]},
        {"tokens": long_tokens, "labels": long_labels},
    ]
    n_long = len(build_windows(long_tokens, long_labels, tokenizer, LABEL2ID,
                               max_length=512, stride=320, doc_idx=1))

    ds = _TokenDataset(samples, tokenizer, LABEL2ID, max_length=512, stride=320)

    assert len(ds) == 1 + n_long
    item = ds[len(ds) - 1]
    assert set(item) <= {"input_ids", "token_type_ids", "attention_mask", "labels"}
    assert "overflow_to_sample_mapping" not in item


def test_default_stride_keeps_every_gold_entity_inside_one_window(tokenizer, corpus_samples):
    """Corpus guarantee behind the choice of stride: no entity is split across all windows."""
    from research.kfold.train_bert import BertConfig
    from research.kfold.windows import build_windows

    cfg = BertConfig()
    label2id = {lab: i for i, lab in enumerate(sorted({lab for s in corpus_samples for lab in s["labels"]}))}
    orphans = 0
    for doc_idx, s in enumerate(corpus_samples):
        if len(s["tokens"]) < 200:  # cannot exceed 512 subwords; skip for speed
            continue
        windows = build_windows(s["tokens"], s["labels"], tokenizer, label2id,
                                max_length=cfg.max_length, stride=cfg.stride, doc_idx=doc_idx)
        covered = [{wid for wid in w.word_ids if wid is not None} for w in windows]
        for start, end in _entity_word_ranges(s["labels"]):
            words = set(range(start, end))
            if not any(words <= c for c in covered):
                orphans += 1
    assert orphans == 0


def test_bilstm_default_max_len_covers_the_longest_corpus_document(corpus_samples):
    from research.kfold.train_bilstm import BiLSTMConfig

    longest = max(len(s["tokens"]) for s in corpus_samples)
    assert BiLSTMConfig().max_len >= longest


def _entity_word_ranges(labels: list[str]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start = None
    for i, lab in enumerate(labels + ["O"]):
        if lab.startswith("B-") or lab == "O":
            if start is not None:
                ranges.append((start, i))
                start = None
            if lab.startswith("B-"):
                start = i
    return ranges
