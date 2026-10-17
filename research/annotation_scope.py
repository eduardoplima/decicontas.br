"""Annotation scope: deliberations addressed to the Tribunal's own units.

Recommendations and notices that a ruling addresses to the external-control
secretariat (SECEX) or to the legal counsel (CONJU) are internal acts, not
entities. One clause detector serves the release, where entities inside such
a clause are dropped, and the evaluation, where predictions touching one are
ignored for every model alike.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Any

from research.dataset_io import (
    Document,
    Token,
    assign_bio_from_spans,
    char_span_to_token_span,
    token_offsets,
)
from research.ner_metrics import extract_spans_from_bio

CLAUSE_RE = re.compile(
    r"(recomend\w*|cientifica\w*)[^.;]{0,60}?"
    r"\b(SECEX|Secretaria\s+de\s+Controle\s+Externo|Consultoria\s+Jur[ií]dica|CONJU)\b",
    re.IGNORECASE,
)
CLAUSE_END_RE = re.compile(r"[.;](?=\s|$)")

Region = tuple[int, int]


def internal_unit_clauses(text: str) -> list[tuple[int, int]]:
    """Character intervals of the clauses: from the verb to the next ``.`` or ``;``."""
    text = text or ""
    out: list[tuple[int, int]] = []
    for m in CLAUSE_RE.finditer(text):
        end = CLAUSE_END_RE.search(text, m.end())
        out.append((m.start(), end.end() if end else len(text)))
    return out


def clause_regions(text: str, offsets: Sequence[tuple[int, int]] | None = None) -> list[Region]:
    """The clauses as half-open token ranges (canonical tokenisation unless ``offsets`` is given)."""
    offsets = list(offsets) if offsets is not None else token_offsets(text)
    regions: list[Region] = []
    for c0, c1 in internal_unit_clauses(text):
        tok = char_span_to_token_span(c0, c1, offsets)
        if tok is not None:
            regions.append(tok)
    return regions


def _bounds(span: Any) -> tuple[int, int]:
    if isinstance(span, dict):
        return int(span["start"]), int(span["end"])
    return int(span[0]), int(span[1])


def inside(span: Any, regions: Iterable[Region]) -> bool:
    s, e = _bounds(span)
    return any(r0 <= s and e <= r1 for r0, r1 in regions)


def overlaps(span: Any, regions: Iterable[Region]) -> bool:
    s, e = _bounds(span)
    return any(s < r1 and e > r0 for r0, r1 in regions)


def apply_scope(documents: Iterable[Document]) -> list[Document]:
    """Drop the entities that lie inside a clause. Documents without one are returned as they are."""
    out: list[Document] = []
    for doc in documents:
        offsets = [(t.char_start, t.char_end) for t in doc.tokens]
        regions = clause_regions(doc.text, offsets)
        kept = []
        for sp in doc.ner_spans:
            tok = char_span_to_token_span(sp.char_start, sp.char_end, offsets)
            if tok is not None and inside(tok, regions):
                continue
            kept.append(sp)
        if len(kept) == len(doc.ner_spans):
            out.append(doc)
            continue
        tokens = [
            Token(text=t.text, char_start=t.char_start, char_end=t.char_end, bio="O")
            for t in doc.tokens
        ]
        assign_bio_from_spans(tokens, kept)
        out.append(
            Document(document_id=doc.document_id, text=doc.text, tokens=tokens, ner_spans=kept)
        )
    return out


def filter_spans(spans: Iterable[Any], regions: Sequence[Region]) -> tuple[list, int]:
    """Token-unit spans minus those touching a region, whatever their label, and how many went."""
    spans = list(spans or [])
    if not regions:
        return spans, 0
    kept = [sp for sp in spans if not overlaps(sp, regions)]
    return kept, len(spans) - len(kept)


def mask_bio(tags: Sequence[str], regions: Sequence[Region]) -> list[str]:
    """BIO sequence with every span that touches a region set to ``O``."""
    out = list(tags)
    if not regions:
        return out
    for s, e, _label in list(extract_spans_from_bio(out)):
        if overlaps((s, e), regions):
            out[s:e] = ["O"] * (e - s)
    return out


def filter_frame(df: Any) -> Any:
    """Copy of an evaluation frame without the predictions that touch a clause.

    Rows carry ``text``, ``golden`` and token-unit ``pred_as_golden``. The
    counts land in ``attrs["scope_filter"]``: ``n_dropped`` predictions were
    discarded, ``n_dropped_on_gold`` of which overlapped a gold entity.
    """
    out = df.copy()
    kept_rows: list[list] = []
    n_dropped = n_on_gold = 0
    for _, row in out.iterrows():
        regions = clause_regions(row.get("text") or "")
        preds = row.get("pred_as_golden") or []
        kept, n = filter_spans(preds, regions)
        if n:
            gold = [_bounds(g) for g in row.get("golden") or []]
            n_on_gold += sum(1 for sp in preds if overlaps(sp, regions) and overlaps(sp, gold))
        n_dropped += n
        kept_rows.append(kept)
    out["pred_as_golden"] = kept_rows
    out.attrs["scope_filter"] = {"n_dropped": n_dropped, "n_dropped_on_gold": n_on_gold}
    return out
