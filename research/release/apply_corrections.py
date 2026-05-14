"""Apply cleanlab correction decisions to the canonical 861-doc dataset.

The corrections file (``dataset/errors/dataset-corrections.json``, v2)
contains a ``token_changes[]`` list with one record per token whose BIO
label changed. Each record carries the resolved final label
(``label_final``) — accept/reject/custom semantics have already been
applied upstream by the review service. This module overrides the BIO
sequence and rebuilds character-level entity spans from the result.

Tokens belonging to groups that are still ``pending`` (not yet decided
by a reviewer) are not present in ``token_changes`` and stay at their
gold annotation.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Iterable

from research.dataset_io import Document, NerSpan, Token


def load_corrections(path: Path) -> dict[tuple[int, int], str]:
    """Read the corrections JSON and return ``{(doc_id, token_idx): label_final}``.

    Only ``token_changes`` is consumed; ``unmapped_changes`` references
    cleanlab rows that couldn't be located in the master JSON and so
    cannot be applied at the token level.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    overrides: dict[tuple[int, int], str] = {}
    for change in payload.get("token_changes") or []:
        key = (int(change["document_id"]), int(change["token_idx_in_doc"]))
        overrides[key] = str(change["label_final"])
    return overrides


def _entity_of(bio: str) -> str | None:
    if bio == "O" or not bio:
        return None
    if bio[:2] in ("B-", "I-"):
        return bio[2:]
    return None


def _spans_from_bio(tokens: list[Token]) -> list[NerSpan]:
    """Reconstruct contiguous character spans from a BIO-tagged token list.

    Tolerant of malformed BIO: an ``I-X`` that follows ``O`` or a different
    entity is treated as a span start, matching the de facto behaviour of
    most NER evaluation libraries (seqeval ``IOB2`` mode).
    """
    spans: list[NerSpan] = []
    current_label: str | None = None
    current_start: int = -1
    current_end: int = -1

    def flush() -> None:
        nonlocal current_label, current_start, current_end
        if current_label is not None:
            spans.append(
                NerSpan(
                    char_start=current_start,
                    char_end=current_end,
                    label=current_label,
                )
            )
        current_label = None
        current_start = -1
        current_end = -1

    for tok in tokens:
        bio = tok.bio
        if bio == "O" or not bio:
            flush()
            continue
        prefix = bio[:2]
        entity = _entity_of(bio)
        if entity is None:
            flush()
            continue
        if prefix == "B-" or current_label != entity:
            flush()
            current_label = entity
            current_start = tok.char_start
            current_end = tok.char_end
        else:  # I- continuation of same entity
            current_end = tok.char_end
    flush()
    return spans


def apply_corrections(
    documents: Iterable[Document],
    overrides: dict[tuple[int, int], str],
) -> list[Document]:
    """Return a deep-copied list with BIO labels overridden and spans rebuilt.

    Inputs are not mutated. Tokens not in ``overrides`` keep their gold BIO.
    """
    out: list[Document] = []
    for doc in documents:
        new_tokens = [copy.replace(t) for t in doc.tokens] if False else [
            Token(text=t.text, char_start=t.char_start, char_end=t.char_end, bio=t.bio)
            for t in doc.tokens
        ]
        for idx, tok in enumerate(new_tokens):
            key = (doc.document_id, idx)
            if key in overrides:
                tok.bio = overrides[key]
        new_spans = _spans_from_bio(new_tokens)
        out.append(
            Document(
                document_id=doc.document_id,
                text=doc.text,
                tokens=new_tokens,
                ner_spans=new_spans,
            )
        )
    return out
