"""Characterization tests for ``tools.fewshot.TOOL_USE_EXAMPLES``.

The entry count is load-bearing — ``tools/CLAUDE.md`` cites 12 hand-curated examples,
and ``test_role_sequence_snapshot`` in ``test_prompt.py`` depends on it.
"""

from __future__ import annotations

from tools.fewshot import TOOL_USE_EXAMPLES
from tools.schema import NERDecisao


def test_has_exactly_12_entries() -> None:
    assert len(TOOL_USE_EXAMPLES) == 12


def test_each_entry_is_tuple_of_str_and_ner_decisao() -> None:
    for i, entry in enumerate(TOOL_USE_EXAMPLES):
        assert isinstance(entry, tuple) and len(entry) == 2, (
            f"Example {i} is not a 2-tuple."
        )
        text, label = entry
        assert isinstance(text, str), f"Example {i}: text is not a str."
        assert isinstance(label, NERDecisao), (
            f"Example {i}: label is not a NERDecisao."
        )


def test_no_empty_texts() -> None:
    for i, (text, _) in enumerate(TOOL_USE_EXAMPLES):
        assert text.strip(), f"Example {i} has empty/whitespace-only text."


def test_positive_negative_split() -> None:
    """8 of 12 examples are positive (contain at least one entity); the
    remaining 4 are intentionally all-empty, teaching the model when *not*
    to extract. Locking in the current curated ratio — a follow-up refactor
    of the few-shot set should re-evaluate both numbers together.
    """
    positive = sum(
        1
        for _, label in TOOL_USE_EXAMPLES
        if any(
            len(getattr(label, field) or []) > 0
            for field in ("multas", "obrigacoes", "ressarcimentos", "recomendacoes")
        )
    )
    assert positive == 8
    assert len(TOOL_USE_EXAMPLES) - positive == 4
