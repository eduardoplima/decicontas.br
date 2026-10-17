"""Group person mentions into persons, across spellings.

A mention is ``{"id", "doc_id", "text"}``. Two spellings belong to the same
person when their first and last name tokens coincide, or when one spelling is
a subset of the other with the same first name and no other person fits.
Single-token spellings join a person only when exactly one person carries that
token. Manual merges and splits override the heuristics.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable

PARTICLES = {"de", "da", "do", "das", "dos", "e", "d", "del", "di", "y"}
_EDGE_PUNCT = re.compile(r"^[\W_]+|[\W_]+$")


def normalise_tokens(text: str) -> list[str]:
    """Lower-case, accent-free name tokens without particles or edge punctuation."""
    out = []
    for tok in text.split():
        tok = unicodedata.normalize("NFKD", tok)
        tok = "".join(c for c in tok if not unicodedata.combining(c)).lower()
        tok = _EDGE_PUNCT.sub("", tok)
        if tok and tok not in PARTICLES:
            out.append(tok)
    return out


class _UnionFind:
    def __init__(self, keys: Iterable):
        self.parent = {k: k for k in keys}

    def find(self, k):
        while self.parent[k] != k:
            self.parent[k] = self.parent[self.parent[k]]
            k = self.parent[k]
        return k

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _canonical(spellings: list[str]) -> str:
    """Longest spelling; among equals, the one with the most lower-case letters."""
    return max(spellings, key=lambda s: (len(normalise_tokens(s)), sum(c.islower() for c in s), -len(s)))


def group_mentions(
    mentions: list[dict],
    merges: list[list[str]] | None = None,
    splits: list[list[str]] | None = None,
) -> list[dict]:
    """``[{"id", "canonical", "tokens", "mentions"}]``, sorted by canonical name."""
    split_ids = {mid for group in (splits or []) for mid in group}
    free = [m for m in mentions if m["id"] not in split_ids]

    by_key: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for m in free:
        key = tuple(normalise_tokens(m["text"]))
        if key:
            by_key[key].append(m)
    keys = list(by_key)
    uf = _UnionFind(keys)

    full = [k for k in keys if len(k) >= 2]
    for i, a in enumerate(full):
        for b in full[i + 1 :]:
            if a[0] == b[0] and a[-1] == b[-1]:
                uf.union(a, b)
    for a in full:
        containers = [b for b in full if b != a and a[0] == b[0] and set(a) <= set(b)]
        if len({uf.find(b) for b in containers}) == 1:
            uf.union(containers[0], a)
    for k in keys:
        if len(k) == 1:
            owners = {uf.find(f) for f in full if k[0] in (f[0], f[-1])}
            if len(owners) == 1:
                uf.union(owners.pop(), k)

    groups: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for k in keys:
        groups[uf.find(k)].extend(by_key[k])
    result = list(groups.values())
    for group in splits or []:
        members = [m for m in mentions if m["id"] in group]
        if members:
            result.append(members)

    if merges:
        index = {m["id"]: gi for gi, group in enumerate(result) for m in group}
        guf = _UnionFind(range(len(result)))
        for group in merges:
            ids = [i for i in group if i in index]
            for other in ids[1:]:
                guf.union(index[ids[0]], index[other])
        merged: dict[int, list[dict]] = defaultdict(list)
        for gi, group in enumerate(result):
            merged[guf.find(gi)].extend(group)
        result = list(merged.values())

    out = []
    seen: dict[str, int] = {}
    for members in result:
        canonical = _canonical([m["text"] for m in members])
        tokens = normalise_tokens(canonical)
        base = "-".join(tokens) or "x"
        seen[base] = seen.get(base, 0) + 1
        gid = base if seen[base] == 1 else f"{base}-{seen[base]}"
        out.append({"id": gid, "canonical": canonical, "tokens": tokens, "mentions": members})
    out.sort(key=lambda g: g["canonical"].lower())
    return out
