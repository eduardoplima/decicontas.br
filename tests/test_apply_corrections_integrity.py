"""Integrity guarantees for the corrected gold standard.

Three defects in :mod:`research.release.apply_corrections` corrupted the
canonical release and are fenced off here:

1. ``reject`` decisions were applied like any other record. For 24 of them the
   stored ``label_final`` was stale, which shattered intact spans in six
   documents and left entities as short as a single character.
2. The BIO prefixes were never re-derived after the spans were rebuilt, so the
   ``entities`` and ``ner_tags`` views of a document disagreed: 459 spans under
   the tolerant reconstruction against 442 under strict IOB2.
3. Two ``accept`` decisions whose cleanlab group did not cover the whole span
   left orphan fragments behind.
"""

from __future__ import annotations

import pathlib

import pytest

from research.dataset_io import load_dataset
from research.release import paths
from research.release.apply_corrections import (
    ADJUDICATED_SPAN_DELETIONS,
    MIN_PLAUSIBLE_SPAN_CHARS,
    apply_corrections,
    check_bio_matches_spans,
    find_suspicious_spans,
    load_corrections,
)

MASTER = paths.LABELED_CORPUS
CORRECTIONS = paths.CORRECTIONS_JSON


def _corrected():
    dataset = load_dataset(pathlib.Path(MASTER))
    overrides = load_corrections(pathlib.Path(CORRECTIONS))
    return apply_corrections(dataset.documents, overrides)


requires_corpus = pytest.mark.skipif(
    not (MASTER.exists() and CORRECTIONS.exists()),
    reason="master corpus or corrections file not available",
)


@requires_corpus
def test_reject_decisions_are_not_applied() -> None:
    """A reject keeps the reviewer's original annotation, so it is a no-op."""
    import json

    payload = json.loads(pathlib.Path(CORRECTIONS).read_text(encoding="utf-8"))
    overrides = load_corrections(pathlib.Path(CORRECTIONS))
    rejects = [c for c in payload["token_changes"] if c.get("decision") == "reject"]
    assert rejects, "fixture no longer exercises the reject path"
    for change in rejects:
        key = (int(change["document_id"]), int(change["token_idx_in_doc"]))
        assert key not in overrides


@requires_corpus
def test_no_fragment_sized_entities() -> None:
    """No entity is short enough to be correction residue rather than annotation."""
    assert find_suspicious_spans(_corrected()) == []


@requires_corpus
def test_bio_and_spans_describe_the_same_annotation() -> None:
    """The ``entities`` and ``ner_tags`` views must never diverge."""
    assert check_bio_matches_spans(_corrected()) == []


@requires_corpus
def test_every_span_starts_with_a_b_prefix() -> None:
    """Strict IOB2: an ``I-`` may only continue a span of the same label."""
    offenders: list[tuple[int, int, str]] = []
    for doc in _corrected():
        previous = "O"
        for idx, tok in enumerate(doc.tokens):
            if tok.bio.startswith("I-") and (
                previous == "O" or previous[2:] != tok.bio[2:]
            ):
                offenders.append((doc.document_id, idx, tok.bio))
            previous = tok.bio
    assert offenders == []


@requires_corpus
def test_adjudicated_deletions_all_still_apply() -> None:
    """Each hand-adjudicated key must match something, or it is silently dead."""
    docs = {d.document_id: d for d in _corrected()}
    raw = {d.document_id: d for d in load_dataset(pathlib.Path(MASTER)).documents}
    for doc_id, start, end, label in ADJUDICATED_SPAN_DELETIONS:
        assert doc_id in raw, f"adjudicated document {doc_id} is gone"
        assert end <= len(raw[doc_id].text), f"offsets out of range for doc {doc_id}"
        present = {
            (s.char_start, s.char_end, s.label) for s in docs[doc_id].ner_spans
        }
        assert (start, end, label) not in present


@requires_corpus
def test_released_gold_matches_the_pipeline() -> None:
    """The shipped release must be what the pipeline currently produces."""
    import json

    release_path = paths.CORRECTED_GOLD_JSON
    if not release_path.exists():
        pytest.skip("release not exported yet")
    released = {d["id"]: d for d in json.loads(release_path.read_text(encoding="utf-8"))}
    for doc in _corrected():
        shipped = released.get(doc.document_id)
        assert shipped is not None, f"document {doc.document_id} missing from release"
        expected = sorted((s.char_start, s.char_end, s.label) for s in doc.ner_spans)
        actual = sorted((e["start"], e["end"], e["label"]) for e in shipped["entities"])
        assert actual == expected, f"document {doc.document_id} differs from release"


def test_min_plausible_span_is_a_tripwire_not_a_filter() -> None:
    assert MIN_PLAUSIBLE_SPAN_CHARS > 0
