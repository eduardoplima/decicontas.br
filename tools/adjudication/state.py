"""Adjudication decisions, persisted to a JSON file after every change.

Items are not stored: they are rebuilt from the annotator files on load (their ids
depend only on the document and the token bounds), so the file holds decisions only.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from research.dataset_io import ENTITY_LABELS, char_span_to_token_span
from research.release import paths
from tools.adjudication import decisions as dec
from tools.adjudication.divergences import (
    FILES,
    SOURCES,
    DocView,
    Item,
    build_all,
    default_decision,
    load_annotators,
)

logger = logging.getLogger("tools.adjudication.state")

ACTIONS = {
    "add": ("include", "reject", "custom"),
    "gold_only": ("keep", "remove", "custom"),
    "label": ("keep", "relabel", "custom"),
}


def file_hashes(annotators_dir: Path) -> dict[str, str]:
    return {name: hashlib.sha256((Path(annotators_dir) / name).read_bytes()).hexdigest() for name in FILES.values()}


class AdjudicationState:
    def __init__(
        self,
        path: Path,
        docs: dict[int, DocView],
        items: dict[int, list[Item]],
        annotators_sha256: dict[str, str] | None = None,
        annotators_dir: Path | None = None,
    ):
        self.path = Path(path)
        self.docs = docs
        self.items = items
        self.annotators_dir = annotators_dir
        self.by_id = {item.id: item for doc_items in items.values() for item in doc_items}
        self.data: dict = {
            "version": "1",
            "annotators_sha256": dict(annotators_sha256 or {}),
            "decisions": {},
            "finished": False,
        }
        if self.path.exists():
            stored = json.loads(self.path.read_text(encoding="utf-8"))
            old = stored.get("annotators_sha256") or {}
            if annotators_sha256 and old and old != annotators_sha256:
                logger.warning("annotator files changed since the state was written (sha256 mismatch)")
            decisions = stored.get("decisions") or {}
            self.data["decisions"] = {k: v for k, v in decisions.items() if k in self.by_id}
            if dropped := len(decisions) - len(self.data["decisions"]):
                logger.warning("%d decisions refer to items that no longer exist and were dropped", dropped)
            self.data["finished"] = bool(stored.get("finished", False))
            if not annotators_sha256:
                self.data["annotators_sha256"] = old

    # ----- decisions ---------------------------------------------------------

    def decision(self, item_id: str) -> dict | None:
        """The explicit decision, else the default one, else ``None`` (pending)."""
        item = self.by_id[item_id]
        explicit = self.data["decisions"].get(item_id)
        return dict(explicit) if explicit else default_decision(item)

    def decide(
        self,
        item_id: str,
        action: str,
        *,
        source: str | None = None,
        label: str | None = None,
        start: int | None = None,
        end: int | None = None,
        char_start: int | None = None,
        char_end: int | None = None,
    ) -> None:
        """``custom`` takes the span bounds in tokens (``start``/``end``) or in characters."""
        item = self.by_id[item_id]
        if action == "pending":
            self.data["decisions"].pop(item_id, None)
            self.save()
            return
        if action not in ACTIONS[item.kind]:
            raise ValueError(f"{action!r} is not a decision for a {item.kind} item")
        record: dict = {"action": action, "decided_at": dec.now_iso()}
        if action == "include":
            if source is None:
                source = max(item.candidates, key=lambda c: c.end - c.start).source
            if source not in item.sources:
                raise ValueError(f"{source!r} did not mark this span")
            cand = dec.candidate_of(item, source)
            label = label or item.label
            if label not in ENTITY_LABELS:
                raise ValueError("a label is required: the annotators disagree")
            record.update(source=source, start=cand.start, end=cand.end, label=label)
        elif action == "relabel":
            if label not in ENTITY_LABELS or label == item.label:
                raise ValueError("relabel needs a label different from the gold one")
            record["label"] = label
        elif action == "custom":
            if label not in ENTITY_LABELS:
                raise ValueError("a label is required for a custom span")
            offsets = self.docs[item.doc_id].offsets
            if char_start is not None and char_end is not None:
                bounds = char_span_to_token_span(char_start, char_end, offsets)
                if bounds is None:
                    raise ValueError("the selection covers no token")
                start, end = bounds
            if start is None or end is None or not 0 <= start < end <= len(offsets):
                raise ValueError("custom needs a non-empty span inside the document")
            record.update(start=start, end=end, label=label)
        if action in ("include", "custom"):
            self._check_overlap(item, record)
        self.data["decisions"][item_id] = record
        self.save()

    def _check_overlap(self, item: Item, record: dict) -> None:
        """Refuse an inclusion that would overlap another included span of the document."""
        items = self.items[item.doc_id]
        tentative = {**self.data["decisions"], item.id: record}
        try:
            dec.final_spans(self.docs[item.doc_id].spans["A1"], items, dec.resolve(items, tentative))
        except dec.ConflictError as exc:
            others = sorted({other for pair in exc.conflicts for other in pair if other != item.id})
            raise ValueError(
                f"conflita com {', '.join(others)} (já incluído): rejeite-o ou escolha outro candidato"
            ) from exc

    # ----- views -------------------------------------------------------------

    def document(self, doc_id: int) -> dict:
        doc = self.docs[doc_id]
        items = self.items.get(doc_id, [])
        resolved = dec.resolve(items, self.data["decisions"])

        def span(s: int, e: int, label: str) -> dict:
            return {"start": s, "end": e, "char_start": doc.offsets[s][0], "char_end": doc.offsets[e - 1][1], "label": label}

        out_items = []
        for item in items:
            record = resolved.get(item.id)
            if record and "start" in record:
                record = {**record, "char_start": doc.offsets[record["start"]][0], "char_end": doc.offsets[record["end"] - 1][1]}
            out_items.append(
                {
                    "id": item.id,
                    "doc_id": item.doc_id,
                    "kind": item.kind,
                    "label": item.label,
                    "sources": item.sources,
                    "candidates": [
                        {
                            **span(c.start, c.end, c.label),
                            "source": c.source,
                            "replaces": c.replaces,
                            "also_adds": [span(*s) for s in c.also_adds],
                        }
                        for c in item.candidates
                    ],
                    "labels": item.labels,
                    "overlaps": item.overlaps,
                    "in_scope_clause": item.in_scope_clause,
                    "default": default_decision(item),
                    "decision": record,
                    "explicit": bool(record and record.get("explicit")),
                    "replaced_by": record.get("replaced_by") if record else None,
                }
            )
        return {
            "doc_id": doc_id,
            "text": doc.text,
            "layers": {source: [span(*s) for s in doc.spans[source]] for source in SOURCES},
            "items": out_items,
        }

    def documents(self) -> list[dict]:
        return [self.document(doc_id) for doc_id in sorted(self.items)]

    def changes(self) -> dict:
        """Every span the current decisions add, remove or relabel, plus unresolved conflicts."""
        changes: list[dict] = []
        conflicts: list[list[str]] = []
        for doc_id in sorted(self.items):
            items = self.items[doc_id]
            try:
                changes += dec.doc_changes(self.docs[doc_id], items, dec.resolve(items, self.data["decisions"]))
            except dec.ConflictError as exc:
                conflicts += [list(pair) for pair in exc.conflicts]
        totals = {kind: sum(1 for c in changes if c["change"] == kind) for kind in ("added", "removed", "relabelled")}
        return {"changes": changes, "conflicts": conflicts, "totals": totals}

    def finish(self, out_path: Path, gold_release: Path | str | None = dec.PRE_ADJUDICATION) -> dict:
        """Write the decisions file and return its summary."""
        payload = dec.build_decisions_file(self, gold_release=gold_release)
        Path(out_path).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        self.data["finished"] = True
        self.save()
        return payload["summary"]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")


def load_state(
    annotators_dir: Path = paths.ANNOTATORS_DIR, state_path: Path = paths.ADJUDICATION_STATE_JSON
) -> AdjudicationState:
    docs = load_annotators(annotators_dir)
    return AdjudicationState(state_path, docs, build_all(docs), file_hashes(annotators_dir), annotators_dir)
