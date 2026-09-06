"""Apply cleanlab correction decisions to the canonical 861-doc dataset.

The corrections file (``dataset/errors/dataset-corrections.json``, v2)
contains a ``token_changes[]`` list with one record per token whose BIO
label changed, together with the reviewer ``decision`` that produced it.

Only ``accept`` and ``custom`` decisions are applied. A ``reject`` means
the reviewer kept the original annotation, so it must be a no-op; 24 of
the reject records carry a stale ``label_final`` that predates the gold
they would be written over, and applying them shattered intact spans in
six documents (ids 90, 204, 232, 338, 410, 580).

After overriding the BIO sequence this module rebuilds character-level
entity spans and then **re-derives the BIO tags from those spans**, so
that the ``entities`` and ``ner_tags`` views of a released document can
never disagree. Skipping that step previously left 17 spans beginning
with ``I-``: visible to the tolerant span reconstruction here, invisible
to any strict IOB2 consumer.

Tokens belonging to groups that are still ``pending`` (not yet decided
by a reviewer) are not present in ``token_changes`` and stay at their
gold annotation.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Iterable

from research.dataset_io import Document, NerSpan, Token, assign_bio_from_spans


APPLIED_DECISIONS = frozenset({"accept", "custom"})

# Residual fragments left by ``accept`` decisions whose cleanlab group did not
# cover the whole span, adjudicated by hand and removed. Keyed by
# ``(document_id, char_start, char_end, label)`` so that a change upstream stops
# matching and is re-flagged by :func:`find_suspicious_spans` instead of being
# dropped silently.
#
#   90  "Ramalho Cortez, dos termos desta Decisao." — tail of a summons
#       ("Intime-se ... na pessoa da sua atual gestora, Sra. Lyane Ramalho
#       Cortez, dos termos desta Decisao"), not a registrable recommendation,
#       and it names a private individual.
#   371 "no item" — leftover of a MULTA the reviewer deleted. The decision
#       *excludes* a fine ("excluindo a multa imposta no item a"), so the
#       document carries no MULTA at all.
ADJUDICATED_SPAN_DELETIONS: frozenset[tuple[int, int, int, str]] = frozenset(
    {
        (90, 2162, 2203, "RECOMENDACAO"),
        (371, 309, 316, "MULTA"),
    }
)

# A span shorter than this is treated as suspicious by
# :func:`find_suspicious_spans`. The shortest genuine entity in the corpus is
# well above it; this is a tripwire, not a filter.
MIN_PLAUSIBLE_SPAN_CHARS = 60


def load_corrections(path: Path) -> dict[tuple[int, int], str]:
    """Read the corrections JSON and return ``{(doc_id, token_idx): label_final}``.

    Records whose ``decision`` is not in :data:`APPLIED_DECISIONS` are
    skipped. A ``reject`` decision means the reviewer kept the original
    annotation, so writing its ``label_final`` back is at best a no-op and
    at worst — for the 24 records whose ``label_final`` is stale — silent
    corruption of a span the reviewer never touched.

    A record with no ``decision`` field is applied, so that older
    corrections files without the field keep working.

    Only ``token_changes`` is consumed; ``unmapped_changes`` references
    cleanlab rows that couldn't be located in the master JSON and so
    cannot be applied at the token level.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    overrides: dict[tuple[int, int], str] = {}
    for change in payload.get("token_changes") or []:
        decision = change.get("decision")
        if decision is not None and decision not in APPLIED_DECISIONS:
            continue
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
        new_spans = [
            sp
            for sp in _spans_from_bio(new_tokens)
            if (doc.document_id, sp.char_start, sp.char_end, sp.label)
            not in ADJUDICATED_SPAN_DELETIONS
        ]
        # Re-derive BIO from the reconstructed spans. ``_spans_from_bio`` is
        # deliberately tolerant of an ``I-X`` that starts a span, but it does
        # not write the normalised prefix back, which used to leave the
        # ``entities`` and ``ner_tags`` views of a document disagreeing.
        for tok in new_tokens:
            tok.bio = "O"
        assign_bio_from_spans(new_tokens, new_spans)
        out.append(
            Document(
                document_id=doc.document_id,
                text=doc.text,
                tokens=new_tokens,
                ner_spans=new_spans,
            )
        )
    return out


def find_suspicious_spans(
    documents: Iterable[Document],
    *,
    min_chars: int = MIN_PLAUSIBLE_SPAN_CHARS,
) -> list[tuple[int, str, int, str]]:
    """Return spans that look like correction residue rather than annotation.

    A span is suspicious when it is shorter than ``min_chars``. Applying the
    cleanlab decisions used to shatter intact spans into fragments this small
    (a one-character ``MULTA``, among others); this is the tripwire that keeps
    that from happening again unnoticed.

    Returns ``(document_id, label, n_chars, text)`` tuples.
    """
    out: list[tuple[int, str, int, str]] = []
    for doc in documents:
        for sp in doc.ner_spans:
            n = sp.char_end - sp.char_start
            if n < min_chars:
                out.append(
                    (doc.document_id, sp.label, n, doc.text[sp.char_start : sp.char_end])
                )
    return out


def check_bio_matches_spans(documents: Iterable[Document]) -> list[int]:
    """Return the ids of documents whose BIO tags and spans disagree.

    A released document exposes its annotation twice, as ``entities`` and as
    ``ner_tags``. They must describe the same spans under strict IOB2, or the
    JSON and CoNLL exports ship different datasets.
    """
    bad: list[int] = []
    for doc in documents:
        recovered: list[tuple[int, int, str]] = []
        current: list[Token] = []
        label: str | None = None
        for tok in doc.tokens:
            if tok.bio.startswith("B-"):
                if current and label is not None:
                    recovered.append((current[0].char_start, current[-1].char_end, label))
                current, label = [tok], tok.bio[2:]
            elif label is not None and tok.bio == f"I-{label}":
                current.append(tok)
            else:
                if current and label is not None:
                    recovered.append((current[0].char_start, current[-1].char_end, label))
                current, label = [], None
        if current and label is not None:
            recovered.append((current[0].char_start, current[-1].char_end, label))
        declared = sorted((sp.char_start, sp.char_end, sp.label) for sp in doc.ner_spans)
        if sorted(recovered) != declared:
            bad.append(doc.document_id)
    return bad
