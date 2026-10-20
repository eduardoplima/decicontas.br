"""From adjudication decisions to a token-level corrections file.

The file has the schema of ``dataset/errors/dataset-corrections.json`` (v2), so
``research.release.apply_corrections`` applies it as a second pass over the
corrected gold. Every record is the BIO tag a token ends up with; ``group_id``
is the item that decided it.

    uv run python -m tools.adjudication.decisions [--state PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from research.annotation_scope import clause_regions, inside
from research.dataset_io import ENTITY_LABELS
from research.release import paths
from research.release.annotator_agreement import load_pre_adjudication_spans, load_release_spans
from tools.adjudication.divergences import Candidate, DocView, Item, Span, default_decision

if TYPE_CHECKING:
    from tools.adjudication.state import AdjudicationState

logger = logging.getLogger("tools.adjudication.decisions")


class ConflictError(ValueError):
    """Two included spans overlap; ``conflicts`` lists the owning item ids."""

    def __init__(self, conflicts: list[tuple[str, str]]):
        self.conflicts = conflicts
        super().__init__(f"overlapping spans: {conflicts}")


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def candidate_of(item: Item, source: str) -> Candidate:
    return next(c for c in item.candidates if c.source == source)


def resolve(items: list[Item], decisions: dict[str, dict]) -> dict[str, dict]:
    """Effective decision per item: explicit, else the default; nothing for pending items.

    A gold span overlapped by an included candidate is ``replaced`` whatever its
    own decision says — the candidate takes its place.
    """
    resolved: dict[str, dict] = {}
    for item in items:
        record = decisions.get(item.id)
        if record:
            resolved[item.id] = {**record, "explicit": True}
        elif default := default_decision(item):
            resolved[item.id] = {**default, "explicit": False}
    gold_items = {(c.start, c.end): item.id for item in items if item.kind != "add" for c in item.candidates}
    for item in items:
        record = resolved.get(item.id)
        if item.kind != "add" or not record or record["action"] not in ("include", "custom"):
            continue
        if record["action"] == "include":
            refs = [(r["start"], r["end"]) for r in candidate_of(item, record["source"]).replaces]
        else:  # a hand-drawn span replaces every gold span it touches
            refs = [b for b in gold_items if b[0] < record["end"] and b[1] > record["start"]]
        for ref in refs:
            target = gold_items.get(ref)
            if target:
                resolved[target] = {"action": "replaced", "replaced_by": item.id, "explicit": False}
    return resolved


def final_spans(
    gold: list[Span], items: list[Item], resolved: dict[str, dict]
) -> tuple[list[Span], dict[int, str]]:
    """The document's spans after the decisions, and the item that owns each changed token."""
    kept: dict[Span, str | None] = {g: None for g in gold}
    removed: dict[Span, str] = {}
    for item in items:
        record = resolved.get(item.id)
        if not record or item.kind == "add":
            continue
        (c,) = item.candidates
        old = (c.start, c.end, c.label)
        if item.kind == "label" and record["action"] == "relabel":
            kept.pop(old, None)
            kept[(c.start, c.end, record["label"])] = item.id
        elif item.kind == "gold_only" and record["action"] == "remove":
            kept.pop(old, None)
            removed[old] = item.id
        elif record["action"] == "custom":  # the gold span gives way to a hand-drawn one
            kept.pop(old, None)
            removed[old] = item.id
            kept[(record["start"], record["end"], record["label"])] = item.id
    for item in items:
        record = resolved.get(item.id)
        if item.kind != "add" or not record or record["action"] not in ("include", "custom"):
            continue
        if record["action"] == "custom":
            s, e = record["start"], record["end"]
            for old in [k for k, owner in kept.items() if owner is None and k[0] < e and k[1] > s]:
                kept.pop(old)
                removed[old] = item.id
            kept[(s, e, record["label"])] = item.id
            continue
        cand = candidate_of(item, record["source"])
        for ref in cand.replaces:
            old = (ref["start"], ref["end"], ref["label"])
            if old in kept:
                kept.pop(old)
                removed[old] = item.id
        kept[(cand.start, cand.end, record.get("label") or cand.label)] = item.id
        for span in cand.also_adds:
            kept[span] = item.id
    spans = sorted(kept)
    conflicts = [(kept[a] or "gold", kept[b] or "gold") for a, b in zip(spans, spans[1:]) if b[0] < a[1]]
    if conflicts:
        raise ConflictError(conflicts)
    owners: dict[int, str] = {}
    for (s, e, _), owner in kept.items():
        if owner:
            for t in range(s, e):
                owners[t] = owner
    for (s, e, _), owner in removed.items():
        for t in range(s, e):
            owners.setdefault(t, owner)
    return spans, owners


def bio_from_spans(spans: list[Span], n_tokens: int) -> list[str]:
    tags = ["O"] * n_tokens
    for s, e, label in spans:
        for t in range(s, min(e, n_tokens)):
            tags[t] = ("B-" if t == s else "I-") + label
    return tags


def token_changes_for_doc(
    doc_id: int,
    gold: list[Span],
    final: list[Span],
    n_tokens: int,
    owners: dict[int, str],
    resolved: dict[str, dict],
    generated_at: str,
) -> list[dict]:
    """One record per token whose BIO tag differs between the gold and the final spans."""
    out = []
    for i, (before, after) in enumerate(zip(bio_from_spans(gold, n_tokens), bio_from_spans(final, n_tokens))):
        if before == after:
            continue
        owner = owners.get(i)
        record = resolved.get(owner, {}) if owner else {}
        out.append(
            {
                "document_id": doc_id,
                "token_idx_in_doc": i,
                "label_final": after,
                "decision": "accept",
                "group_id": owner,
                "decided_by": "author" if record.get("explicit") else "default",
                "decided_at": record.get("decided_at") or generated_at,
            }
        )
    return out


def _changes(doc: DocView, final: list[Span], owners: dict[int, str], resolved: dict[str, dict]) -> list[dict]:
    gold = {(s, e): label for s, e, label in doc.spans["A1"]}
    after = {(s, e): label for s, e, label in final}
    out = []
    for (s, e), label in sorted(after.items()):
        if (s, e) not in gold:
            out.append(("added", s, e, label, None))
        elif gold[(s, e)] != label:
            out.append(("relabelled", s, e, label, gold[(s, e)]))
    for (s, e), label in sorted(gold.items()):
        if (s, e) not in after:
            out.append(("removed", s, e, label, None))
    changes = []
    for change, s, e, label, old_label in sorted(out, key=lambda c: (c[1], c[2])):
        owner = owners.get(s)
        record = resolved.get(owner, {}) if owner else {}
        changes.append(
            {
                "doc_id": doc.doc_id,
                "change": change,
                "start": s,
                "end": e,
                "char_start": doc.offsets[s][0],
                "char_end": doc.offsets[e - 1][1],
                "label": label,
                "old_label": old_label,
                "excerpt": doc.text[doc.offsets[s][0] : doc.offsets[e - 1][1]],
                "item": owner,
                "explicit": bool(record.get("explicit")),
            }
        )
    return changes


def doc_changes(doc: DocView, items: list[Item], resolved: dict[str, dict]) -> list[dict]:
    """Spans added, removed or relabelled in ``doc`` by the resolved decisions, with excerpts."""
    final, owners = final_spans(doc.spans["A1"], items, resolved)
    return _changes(doc, final, owners, resolved)


PRE_ADJUDICATION = "pre-adjudication"


def verify_gold_alignment(docs: dict[int, DocView], gold: Path | str | dict[int, dict]) -> list[int]:
    """Documents where annotator 1 no longer matches ``gold`` (token spans).

    ``gold`` is a release JSON path, spans in the release shape, or
    :data:`PRE_ADJUDICATION` for the audited gold before the adjudication pass.
    """
    if gold == PRE_ADJUDICATION:
        release = load_pre_adjudication_spans()
    elif isinstance(gold, dict):
        release = gold
    else:
        release = load_release_spans(Path(gold))
    return sorted(i for i, d in docs.items() if i in release and release[i]["token_spans"] != d.spans["A1"])


def _rel(path: Path | str | None) -> str | None:
    if path is None:
        return None
    path = Path(path)
    try:
        return str(path.resolve().relative_to(paths.REPO_ROOT))
    except ValueError:
        return str(path)


def _gold_source(gold: Path | str | dict | None) -> str | None:
    if gold is None or isinstance(gold, str):
        return gold
    return "in-memory spans" if isinstance(gold, dict) else _rel(gold)


def build_decisions_file(
    state: AdjudicationState,
    *,
    gold_release: Path | str | dict[int, dict] | None = PRE_ADJUDICATION,
    generated_at: str | None = None,
) -> dict:
    """The corrections-file payload (``token_changes`` + ``summary``) for the current decisions."""
    generated_at = generated_at or now_iso()
    if gold_release is not None:
        bad = verify_gold_alignment({i: state.docs[i] for i in state.items}, gold_release)
        if bad:
            raise ValueError(f"annotator 1 differs from the release gold on documents {bad[:5]}")
    before: Counter = Counter(label for doc in state.docs.values() for _, _, label in doc.spans["A1"])
    after = Counter(before)
    changes: list[dict] = []
    actions: Counter = Counter()
    added: Counter = Counter()
    removed: Counter = Counter()
    relabelled: Counter = Counter()
    items_total = items_decided = in_scope_included = 0
    for doc_id, items in state.items.items():
        doc = state.docs[doc_id]
        gold = doc.spans["A1"]
        resolved = resolve(items, state.data["decisions"])
        final, owners = final_spans(gold, items, resolved)
        changes += token_changes_for_doc(doc_id, gold, final, len(doc.offsets), owners, resolved, generated_at)
        items_total += len(items)
        for item in items:
            if record := resolved.get(item.id):
                items_decided += 1
                actions[record["action"]] += 1
        regions = clause_regions(doc.text, doc.offsets)
        in_scope = [s for s in final if s not in gold and inside((s[0], s[1]), regions)]
        in_scope_included += len(in_scope)
        after.subtract(label for _, _, label in gold)
        after.update(label for s in final if s not in in_scope for label in [s[2]])
        for change in _changes(doc, final, owners, resolved):
            if change["change"] == "added":
                added[change["label"]] += 1
            elif change["change"] == "removed":
                removed[change["label"]] += 1
            else:
                relabelled[(change["old_label"], change["label"])] += 1
    summary = {
        "items_total": items_total,
        "items_decided": items_decided,
        "items_pending": items_total - items_decided,
        **{action: actions[action] for action in ("include", "reject", "keep", "remove", "relabel", "custom", "replaced")},
        "token_changes": len(changes),
        "in_scope_included": in_scope_included,
        "entities_before": {label: before[label] for label in ENTITY_LABELS},
        "entities_after": {label: after[label] for label in ENTITY_LABELS},
        "added_per_label": dict(sorted(added.items())),
        "removed_per_label": dict(sorted(removed.items())),
        "relabelled": [{"from": a, "to": b, "n": n} for (a, b), n in sorted(relabelled.items())],
    }
    return {
        "version": "2",
        "generated_at": generated_at,
        "source": {
            "annotators_dir": _rel(state.annotators_dir),
            "annotators_sha256": state.data["annotators_sha256"],
            "state": _rel(state.path),
            "gold": _gold_source(gold_release),
        },
        "token_changes": changes,
        "summary": summary,
    }


def main() -> None:
    from tools.adjudication.state import load_state

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--annotators", type=Path, default=paths.ANNOTATORS_DIR)
    parser.add_argument("--state", type=Path, default=paths.ADJUDICATION_STATE_JSON)
    parser.add_argument("--out", type=Path, default=paths.ADJUDICATION_DECISIONS_JSON)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    payload = build_decisions_file(load_state(args.annotators, args.state))
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    s = payload["summary"]
    logger.info(
        "%d/%d items decided, %d token changes, entities %s -> %s; %s",
        s["items_decided"], s["items_total"], s["token_changes"],
        sum(s["entities_before"].values()), sum(s["entities_after"].values()), args.out,
    )


if __name__ == "__main__":
    main()
