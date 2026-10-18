"""Divergence items between annotator 1 (the gold) and annotators 2 and 3.

Spans are compared in token units with the same IoU >= 0.5 label-agnostic
matching as the agreement study. Three kinds of item come out of a document:

- ``add``: a span of A2 and/or A3 with no gold counterpart (matching spans of
  the two annotators form one item with two candidates);
- ``gold_only``: a gold span that neither annotator marked;
- ``label``: a gold span matched by an annotator under another label.

Same-label boundary differences at IoU >= 0.5 are agreements and produce nothing.
A candidate that partially overlaps gold spans lists them in ``replaces``:
including it means replacing them, so the annotator's own spans matched to
those gold spans (``also_adds``) must come back with it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from research.annotation_scope import clause_regions, inside
from research.dataset_io import token_offsets
from research.ner_metrics import bipartite_greedy_match, compute_iou_raw
from research.release import paths
from research.release.annotator_agreement import load_annotator

Span = tuple[int, int, str]

SOURCES = ("A1", "A2", "A3")
ANNOTATORS = ("A2", "A3")
FILES = {"A1": "anotador1.jsonl", "A2": "anotador2.jsonl", "A3": "anotador3.jsonl"}
IOU_THRESHOLD = 0.5
KINDS = ("add", "gold_only", "label")
# Pre-mark only additions that touch no gold span; the rest re-segments the gold and
# deserves a look. Flip to pre-mark every span both annotators agree on.
PREMARK_ONLY_PURE_ADDITIONS = True


@dataclass
class DocView:
    doc_id: int
    text: str
    offsets: list[tuple[int, int]]
    spans: dict[str, list[Span]]  # token spans per source


@dataclass
class Candidate:
    source: str
    start: int
    end: int
    label: str
    replaces: list[dict] = field(default_factory=list)  # gold spans overlapped: start/end/label/iou
    also_adds: list[Span] = field(default_factory=list)  # own spans matched to a replaced gold span


@dataclass
class Item:
    id: str
    doc_id: int
    kind: str
    label: str | None  # add: the annotators' label (None when they differ); else the gold label
    sources: list[str]
    candidates: list[Candidate]
    labels: dict[str, str | None] | None = None  # label items: what each source wrote
    overlaps: list[dict] = field(default_factory=list)  # gold_only: annotator spans with IoU > 0
    in_scope_clause: bool = False


def item_id(doc_id: int, kind: str, start: int, end: int) -> str:
    prefix = {"add": "add", "gold_only": "gold", "label": "label"}[kind]
    return f"{doc_id}:{prefix}:{start}-{end}"


def load_annotators(annotators_dir: Path = paths.ANNOTATORS_DIR) -> dict[int, DocView]:
    """The three annotator files as one :class:`DocView` per document (ids and texts must agree)."""
    loaded = {source: load_annotator(Path(annotators_dir) / name) for source, name in FILES.items()}
    ids = sorted(loaded["A1"])
    for source in ANNOTATORS:
        if sorted(loaded[source]) != ids:
            raise ValueError(f"{source}: document ids differ from A1")
        bad = [i for i in ids if loaded[source][i]["text"] != loaded["A1"][i]["text"]]
        if bad:
            raise ValueError(f"{source}: texts differ from A1 on documents {bad[:5]}")
    return {
        i: DocView(
            i,
            loaded["A1"][i]["text"],
            token_offsets(loaded["A1"][i]["text"]),
            {source: list(loaded[source][i]["token_spans"]) for source in SOURCES},
        )
        for i in ids
    }


def match_to_gold(spans: list[Span], gold: list[Span]) -> dict[int, int]:
    """``{span index: gold index}`` at IoU >= 0.5, ignoring labels."""
    pairs = bipartite_greedy_match(spans, gold, IOU_THRESHOLD, require_label_match=False)
    return {p: g for p, g in pairs}


def _overlapping(span: tuple[int, int], others: list[Span]) -> list[dict]:
    out = []
    for s, e, label in others:
        iou = compute_iou_raw(span, (s, e))
        if iou > 0:
            out.append({"start": s, "end": e, "label": label, "iou": iou})
    return out


def build_items(doc: DocView) -> list[Item]:
    gold = doc.spans["A1"]
    regions = clause_regions(doc.text, doc.offsets)
    matched = {k: match_to_gold(doc.spans[k], gold) for k in ANNOTATORS}
    by_gold = {k: {g: p for p, g in matched[k].items()} for k in ANNOTATORS}
    items: list[Item] = []

    for gi, (gs, ge, gl) in enumerate(gold):
        labels: dict[str, str | None] = {"A1": gl}
        proposals: dict[str, str] = {}
        for k in ANNOTATORS:
            pi = by_gold[k].get(gi)
            labels[k] = doc.spans[k][pi][2] if pi is not None else None
            if pi is not None and labels[k] != gl:
                proposals[k] = labels[k]  # type: ignore[assignment]
        anchor = Candidate("A1", gs, ge, gl)
        if proposals:
            items.append(
                Item(item_id(doc.doc_id, "label", gs, ge), doc.doc_id, "label", gl, sorted(proposals), [anchor], labels)
            )
        elif all(gi not in by_gold[k] for k in ANNOTATORS):
            overlaps = [{"source": k, **ref} for k in ANNOTATORS for ref in _overlapping((gs, ge), doc.spans[k])]
            items.append(
                Item(item_id(doc.doc_id, "gold_only", gs, ge), doc.doc_id, "gold_only", gl, [], [anchor], overlaps=overlaps)
            )

    extras = {k: [s for i, s in enumerate(doc.spans[k]) if i not in matched[k]] for k in ANNOTATORS}
    pairs = sorted(bipartite_greedy_match(extras["A2"], extras["A3"], IOU_THRESHOLD, require_label_match=False))
    groups = [[("A2", extras["A2"][p]), ("A3", extras["A3"][g])] for p, g in pairs]
    groups += [[("A2", s)] for i, s in enumerate(extras["A2"]) if i not in {p for p, _ in pairs}]
    groups += [[("A3", s)] for i, s in enumerate(extras["A3"]) if i not in {g for _, g in pairs}]
    for group in groups:
        candidates = []
        for source, (s, e, label) in group:
            replaces = _overlapping((s, e), gold)
            also: list[Span] = []
            for ref in replaces:
                gi = next(i for i, g in enumerate(gold) if (g[0], g[1]) == (ref["start"], ref["end"]))
                pi = by_gold[source].get(gi)
                if pi is not None:
                    also.append(doc.spans[source][pi])
            candidates.append(Candidate(source, s, e, label, replaces, also))
        labels_seen = {c.label for c in candidates}
        start, end = min(c.start for c in candidates), max(c.end for c in candidates)
        items.append(
            Item(
                item_id(doc.doc_id, "add", start, end),
                doc.doc_id,
                "add",
                labels_seen.pop() if len(labels_seen) == 1 else None,
                [c.source for c in candidates],
                candidates,
                in_scope_clause=any(inside((c.start, c.end), regions) for c in candidates),
            )
        )
    items.sort(key=lambda i: (i.candidates[0].start, i.kind))
    return items


def build_all(docs: dict[int, DocView]) -> dict[int, list[Item]]:
    """Items per document, for the documents that have any."""
    out = {}
    for doc_id in sorted(docs):
        items = build_items(docs[doc_id])
        if items:
            out[doc_id] = items
    return out


def default_decision(item: Item) -> dict | None:
    """``include`` with the longer candidate when both annotators agree on a span in scope."""
    if item.kind != "add" or item.sources != list(ANNOTATORS) or item.label is None or item.in_scope_clause:
        return None
    if PREMARK_ONLY_PURE_ADDITIONS and any(c.replaces for c in item.candidates):
        return None
    best = max(item.candidates, key=lambda c: c.end - c.start)  # ties keep A2 (first)
    return {"action": "include", "source": best.source, "start": best.start, "end": best.end, "label": best.label}
