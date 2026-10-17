"""Review decisions, persisted to a JSON file after every change."""

from __future__ import annotations

import json
import re
from pathlib import Path

from tools.review.grouping import group_mentions, normalise_tokens
from tools.review.names import strip_role_prefix

_FEMALE = re.compile(r"(?:\bSra\.?|\bSr[ªa]\b|\bSenhora\b|\bDra\.?|\bExma\.?)\s*$", re.I)
_MALE = re.compile(r"(?:\bSr\.?|\bSenhor\b|\bDr\.?|\bExmo\.?)\s*$", re.I)


class ReviewState:
    def __init__(self, path: Path, candidates: list[dict], docs: dict[int, str]):
        self.path = Path(path)
        self.docs = {int(k): v for k, v in docs.items()}
        self.candidates = {c["id"]: dict(c) for c in candidates}
        self.data = {"decisions": {}, "manual": [], "merges": [], "splits": [], "genders": {}, "finished": False}
        if self.path.exists():
            self.data.update(json.loads(self.path.read_text(encoding="utf-8")))
        for m in self.data["manual"]:
            self.candidates[m["id"]] = dict(m)

    # ----- decisions ---------------------------------------------------------

    def decision(self, mention_id: str) -> str | None:
        if mention_id in self.data["decisions"]:
            return self.data["decisions"][mention_id]
        sources = self.candidates[mention_id].get("sources") or []
        return "yes" if len(sources) >= 2 else None

    def decide(self, mention_id: str, value: str) -> list[str]:
        """Record the decision for this mention and for its repeats in the same document."""
        if value not in ("yes", "no"):
            raise ValueError(value)
        target = self.candidates[mention_id]
        key = (int(target["doc_id"]), normalise_tokens(target["text"]))
        updated = [
            m["id"]
            for m in self.candidates.values()
            if (int(m["doc_id"]), normalise_tokens(m["text"])) == key
        ]
        for mid in updated:
            self.data["decisions"][mid] = value
        self.save()
        return updated

    def add_mention(self, doc_id: int, text: str) -> dict:
        haystack = self.docs[doc_id]
        text, _ = strip_role_prefix(text.strip())
        start = haystack.find(text)
        if start < 0:
            raise ValueError(f"'{text}' not found in document {doc_id}")
        n = sum(1 for m in self.data["manual"] if m["doc_id"] == doc_id)
        mention = {
            "id": f"{doc_id}:m{n}",
            "doc_id": doc_id,
            "text": text,
            "start": start,
            "end": start + len(text),
            "sources": ["manual"],
        }
        self.data["manual"].append(mention)
        self.candidates[mention["id"]] = dict(mention)
        self.data["decisions"][mention["id"]] = "yes"
        self.save()
        return mention

    # ----- persons -----------------------------------------------------------

    def persons(self) -> list[dict]:
        marked = [m for m in self.candidates.values() if self.decision(m["id"]) == "yes"]
        groups = group_mentions(marked, self.data["merges"], self.data["splits"])
        for g in groups:
            g["gender"] = self.data["genders"].get(g["id"]) or self._guess_gender(g["mentions"])
        return groups

    def _guess_gender(self, mentions: list[dict]) -> str | None:
        for m in mentions:
            before = self.docs.get(m["doc_id"], "")[max(0, m["start"] - 12) : m["start"]]
            if _FEMALE.search(before):
                return "F"
            if _MALE.search(before):
                return "M"
        return None

    def set_gender(self, group_id: str, gender: str | None) -> None:
        if gender not in ("M", "F", None):
            raise ValueError(gender)
        self.data["genders"][group_id] = gender
        self.save()

    def merge(self, mention_ids: list[str]) -> None:
        """Join the groups holding these mentions; undoes earlier splits of them."""
        ids = set(mention_ids)
        self.data["splits"] = [[i for i in s if i not in ids] for s in self.data["splits"]]
        self.data["splits"] = [s for s in self.data["splits"] if s]
        self.data["merges"].append(list(mention_ids))
        self.save()

    def split(self, mention_ids: list[str]) -> None:
        """Move these mentions into a group of their own; undoes earlier merges of them."""
        ids = set(mention_ids)
        self.data["merges"] = [[i for i in m if i not in ids] for m in self.data["merges"]]
        self.data["merges"] = [m for m in self.data["merges"] if len(m) > 1]
        self.data["splits"].append(list(mention_ids))
        self.save()

    def finish(self, value: bool = True) -> None:
        self.data["finished"] = value
        self.save()

    # ----- views -------------------------------------------------------------

    def documents(self) -> list[dict]:
        by_doc: dict[int, list[dict]] = {}
        for m in self.candidates.values():
            by_doc.setdefault(int(m["doc_id"]), []).append({**m, "decision": self.decision(m["id"])})
        out = []
        for doc_id in sorted(by_doc):
            mentions = sorted(by_doc[doc_id], key=lambda m: m["start"])
            out.append({"doc_id": doc_id, "text": self.docs.get(doc_id, ""), "mentions": mentions})
        return out

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")
