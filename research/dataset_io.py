"""Canonical tokenisation and Document model for the DeciContas dataset.

The cleanlab analysis (``notebooks/aed_decicontas.ipynb``) loads
``dataset/labeled_data/decicontas.json`` via :func:`research.dataset.get_decicontas_df`
(861 docs after the fewshot filter), tokenises each document with
``re.finditer(r'\\S+', text)``, and converts Label Studio spans to BIO tags
(``MULTA_FIXA`` / ``MULTA_PERCENTUAL`` / ``OBRIGACAO_MULTA`` collapse to
``MULTA`` / ``OBRIGACAO``).

This module is the single source of truth for that construction. Both the
backend's correction-review service and the academic release exporter
import from here, so the cleanlab CSV's ``sentenca_idx`` and the corrections
file's ``(document_id, token_idx_in_doc)`` keys map identically across
producers and consumers.

The CONLL file under ``dataset/labeled_data/decicontas.conll`` is intentionally
not used — it was produced by a different tokenizer in a separate experiment
and its sentence indices don't line up.
"""

from __future__ import annotations

import json
import re
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from pathlib import Path

from .fewshot import FEWSHOT_DATASET_IDS


_TOKEN_RE = re.compile(r"\S+")

# Same as ``research.dataset.translate_golden``: collapse fine-grained labels
# down to the four-class scheme used for evaluation.
LABEL_COLLAPSE = {
    "MULTA_FIXA": "MULTA",
    "MULTA_PERCENTUAL": "MULTA",
    "OBRIGACAO_MULTA": "OBRIGACAO",
}

ENTITY_LABELS = ("MULTA", "OBRIGACAO", "RESSARCIMENTO", "RECOMENDACAO")


@dataclass
class Token:
    text: str
    char_start: int
    char_end: int
    bio: str  # B-MULTA / I-OBRIGACAO / O / ...


@dataclass
class NerSpan:
    char_start: int
    char_end: int
    label: str  # collapsed


@dataclass
class Document:
    document_id: int
    text: str
    tokens: list[Token]
    ner_spans: list[NerSpan]


@dataclass
class Dataset:
    documents: list[Document]
    # ``sentencas_doc_ids[i]`` is the i-th document with at least one token —
    # this list's indexing matches the cleanlab CSV's ``sentenca_idx``.
    sentencas_doc_ids: list[int]


def collapse_label(label: str) -> str:
    return LABEL_COLLAPSE.get(label, label)


def tokenize(text: str) -> list[Token]:
    """Whitespace tokenisation (``\\S+``), all tokens initialised with BIO ``O``."""
    return [
        Token(text=m.group(), char_start=m.start(), char_end=m.end(), bio="O")
        for m in _TOKEN_RE.finditer(text or "")
    ]


TokenOffsets = list[tuple[int, int]]

# Every span-level metric in this repository is computed in whitespace token
# index units, over the tokenisation produced by :func:`tokenize`. Character
# offsets are an input format, never a scoring unit: an offset pair emitted by
# a generative model is located in the source by fuzzy string matching, so its
# right edge is an estimate, while an offset pair derived from a BIO sequence
# always lands on a token boundary. Comparing the two in character space
# measures that asymmetry rather than extraction quality.
SPAN_UNIT = "token"


def token_offsets(text: str) -> TokenOffsets:
    """``(char_start, char_end)`` for each canonical ``\\S+`` token of ``text``."""
    return [(m.start(), m.end()) for m in _TOKEN_RE.finditer(text or "")]


def char_span_to_token_span(
    char_start: int, char_end: int, offsets: TokenOffsets
) -> tuple[int, int] | None:
    """Map a character interval onto the half-open token range covering it.

    A token belongs to the span when it overlaps ``[char_start, char_end)`` at
    all, which is byte-for-byte the predicate :func:`assign_bio_from_spans`
    uses to lay down BIO tags. Keeping the two identical is what guarantees
    that a document's ``entities`` and its ``ner_tags`` describe the same
    spans, whichever one you convert from.

    A zero-length interval falls back to the token containing ``char_start``.
    Returns ``None`` when nothing overlaps — a span that lands in whitespace or
    past the end of the text — and also for an inverted interval, which is
    corrupt input and should be counted rather than quietly snapped to a token.
    """
    if not offsets or char_end < char_start:
        return None
    if char_end == char_start:
        for idx, (start, end) in enumerate(offsets):
            if start <= char_start < end:
                return (idx, idx + 1)
        return None
    starts = [start for start, _ in offsets]
    ends = [end for _, end in offsets]
    lo = bisect_right(ends, char_start)
    hi = bisect_left(starts, char_end)
    return (lo, hi) if hi > lo else None


def spans_to_token_units(
    text_or_offsets: str | TokenOffsets,
    spans: list[dict],
    *,
    shift: int = 0,
) -> tuple[list[dict], int]:
    """Convert ``{"start", "end", "labels"}`` dicts from characters to tokens.

    ``shift`` is added to both offsets first, for the case where the offsets
    were computed against a text that differs from the canonical one by a
    leading-whitespace prefix.

    Returns the converted spans and the number that could not be placed on any
    token. Callers must report that count rather than discard it: a silent drop
    is indistinguishable from a model that predicted nothing.
    """
    offsets = (
        token_offsets(text_or_offsets)
        if isinstance(text_or_offsets, str)
        else text_or_offsets
    )
    out: list[dict] = []
    dropped = 0
    for span in spans or []:
        converted = char_span_to_token_span(
            int(span["start"]) + shift, int(span["end"]) + shift, offsets
        )
        if converted is None:
            dropped += 1
            continue
        start, end = converted
        new = dict(span)
        new["start"], new["end"] = start, end
        out.append(new)
    return out, dropped


def assign_bio_from_spans(tokens: list[Token], spans: list[NerSpan]) -> None:
    """Mutate ``tokens`` so each token overlapping a span gets ``B-X`` / ``I-X``.

    For each span: the first overlapping token gets ``B-X``, subsequent
    overlapping tokens get ``I-X``. Tokens not covered by any span keep ``O``.
    """
    for span in spans:
        first = True
        for tok in tokens:
            if tok.char_start < span.char_end and tok.char_end > span.char_start:
                tok.bio = ("B-" if first else "I-") + span.label
                first = False


def build_document(raw_id: int, text: str, raw_spans: list[dict]) -> Document:
    spans: list[NerSpan] = []
    for s in raw_spans:
        start = s.get("start")
        end = s.get("end")
        labels = s.get("labels") or []
        if start is None or end is None or not labels:
            continue
        spans.append(
            NerSpan(
                char_start=int(start),
                char_end=int(end),
                label=collapse_label(labels[0]),
            )
        )
    spans.sort(key=lambda s: (s.char_start, s.char_end))
    tokens = tokenize(text)
    assign_bio_from_spans(tokens, spans)
    return Document(document_id=raw_id, text=text or "", tokens=tokens, ner_spans=spans)


def extract_raw_spans(item: dict) -> list[dict]:
    """Pull span dicts out of a Label Studio annotation item."""
    spans: list[dict] = []
    for ann in item.get("annotations", []) or []:
        for r in ann.get("result", []) or []:
            value = r.get("value") or {}
            if "start" in value and "end" in value and "labels" in value:
                spans.append(
                    {
                        "start": value["start"],
                        "end": value["end"],
                        "labels": value["labels"],
                    }
                )
    return spans


def load_dataset(path: Path, *, exclude_fewshot: bool = True) -> Dataset:
    """Load the Label Studio export, tokenise canonically, optionally filter
    out the few-shot leak documents.

    With ``exclude_fewshot=True`` (default), drops the 5 IDs in
    :data:`research.fewshot.FEWSHOT_DATASET_IDS` to avoid evaluation contamination
    (these documents appear inside LLM prompts). The resulting list is the
    "861-doc" dataset used by the cleanlab analysis and the supervised CV.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    fewshot = set(FEWSHOT_DATASET_IDS) if exclude_fewshot else set()

    docs: list[Document] = []
    sentencas_doc_ids: list[int] = []
    for item in raw:
        doc_id = item.get("id")
        if doc_id is None or doc_id in fewshot:
            continue
        text = (item.get("data", {}) or {}).get("text", "") or ""
        raw_spans = extract_raw_spans(item)
        document = build_document(int(doc_id), text, raw_spans)
        docs.append(document)
        # Mirror the notebook's loop: only append to sentencas when tokens
        # is non-empty so cleanlab's sentenca_idx aligns.
        if document.tokens:
            sentencas_doc_ids.append(document.document_id)

    return Dataset(documents=docs, sentencas_doc_ids=sentencas_doc_ids)


def available_bio_labels(dataset: Dataset) -> list[str]:
    """Sorted union of BIO labels observed across all documents, plus ``O``."""
    labels: set[str] = {"O"}
    for d in dataset.documents:
        for tok in d.tokens:
            labels.add(tok.bio)
    return sorted(labels, key=lambda x: (x != "O", x))
