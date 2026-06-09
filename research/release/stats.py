"""Aggregate counts for the DeciContas release.

A single utility per stat — kept boring on purpose so the numbers are
easy to audit against the JSON outputs.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from research.dataset_io import Document, ENTITY_LABELS


def count_entities(documents: Iterable[Document]) -> dict[str, int]:
    """Number of entity spans per label."""
    counter: Counter[str] = Counter()
    for doc in documents:
        for span in doc.ner_spans:
            counter[span.label] += 1
    return {label: counter.get(label, 0) for label in ENTITY_LABELS}


def count_docs_with_entity(documents: Iterable[Document]) -> dict[str, int]:
    """Number of distinct documents containing at least one span of each label."""
    seen: dict[str, set[int]] = {label: set() for label in ENTITY_LABELS}
    for doc in documents:
        for span in doc.ner_spans:
            if span.label in seen:
                seen[span.label].add(doc.document_id)
    return {label: len(ids) for label, ids in seen.items()}


def count_docs_with_any_entity(documents: Iterable[Document]) -> int:
    return sum(1 for doc in documents if doc.ner_spans)


def total_tokens(documents: Iterable[Document]) -> int:
    return sum(len(doc.tokens) for doc in documents)


def total_chars(documents: Iterable[Document]) -> int:
    return sum(len(doc.text) for doc in documents)
