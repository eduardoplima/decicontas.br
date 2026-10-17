"""Token-preserving pseudonymisation of person names.

Every real name token maps to one synthetic token (Faker, pt-BR, fixed seed),
so a mention keeps its number of whitespace tokens and every token-unit span
and metric is unchanged. Replacement happens only inside the mentions marked
for a document and in further runs of that person's tokens in the same
document; particles (de, da, dos...) and generational suffixes stay.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable

from faker import Faker

from research.dataset_io import token_offsets
from tools.review.grouping import PARTICLES, normalise_tokens

SUFFIXES = {"junior", "filho", "neto", "sobrinho", "segundo", "terceiro"}
_EDGE = re.compile(r"^([\W_]*)(.*?)([\W_]*)$", re.S)


def normalise_token(token: str) -> str:
    """Lower-case, accent-free core of a whitespace token (punctuation at the edges dropped)."""
    core = _EDGE.match(token).group(2)
    core = unicodedata.normalize("NFKD", core)
    return "".join(c for c in core if not unicodedata.combining(c)).lower()


def infer_gender(name: str, declared: str | None) -> str:
    if declared in ("M", "F"):
        return declared
    first = normalise_tokens(name)[:1]
    return "F" if first and first[0].endswith("a") else "M"


def render_like(synthetic: str, like: str) -> str:
    core = _EDGE.match(like).group(2)
    if core.isupper() and len(core) > 1:
        return synthetic.upper()
    if core[:1].islower():
        return synthetic.lower()
    return synthetic[:1].upper() + synthetic[1:]


def _pool(draw: Callable[[], str], n: int = 3000) -> list[str]:
    seen: list[str] = []
    for _ in range(n):
        v = draw()
        if v.isalpha() and v not in seen:
            seen.append(v)
    return seen


LOCALES = ("pt_BR", "pt_PT", "es_ES", "it_IT")  # Portuguese first; the others widen the lengths


def _pools(seed: int) -> dict[str, list[str]]:
    pools: dict[str, list[str]] = {"M": [], "F": [], "S": []}
    for locale in LOCALES:
        fake = Faker(locale)
        fake.seed_instance(seed)
        pools["M"] += _pool(fake.first_name_male)
        pools["F"] += _pool(fake.first_name_female)
        pools["S"] += _pool(fake.last_name)
    return {k: list(dict.fromkeys(v)) for k, v in pools.items()}


def build_token_map(
    persons: Iterable[dict], seed: int = 1007, exclude: Iterable[str] = ()
) -> dict[str, str]:
    """``{normalised real token: synthetic token}`` over every marked person.

    A synthetic token has the same number of characters as the real one, so the
    text keeps every character offset (the fuzzy aligner used to score the LLM
    outputs works on character windows). ``exclude``: normalised tokens that must
    not be used as synthetic names (every word of the original corpus, so a
    pseudonym never reads as a common noun, a place or the name of someone who
    was kept).
    """
    Faker.seed(seed)
    rng = Faker("pt_BR").random
    persons = sorted(persons, key=lambda p: p["canonical"].lower())
    real = {t for p in persons for t in _name_tokens(p)} | set(exclude)
    pools = {k: [v for v in pool if normalise_token(v) not in real] for k, pool in _pools(seed).items()}
    # a token that opens some person's name is a first name everywhere (gender of that person)
    first_gender: dict[str, str] = {}
    for p in persons:
        first = normalise_tokens(p["canonical"])[:1]
        if first:
            first_gender.setdefault(first[0], infer_gender(p["canonical"], p.get("gender")))
    taken: set[str] = set()
    tmap: dict[str, str] = {}
    for person in persons:
        tokens = _name_tokens(person)
        used = {tmap[t] for t in tokens if t in tmap}
        for tok in tokens:
            if tok in tmap:
                continue
            pool = pools[first_gender[tok]] if tok in first_gender else pools["S"]
            same = [v for v in pool if len(v) == len(tok)]
            # one synthetic token per real token; reuse across persons only when the pool runs out
            free = [v for v in same if v not in taken and v not in used] or [v for v in same if v not in used]
            if free:
                choice = rng.choice(free)
            else:  # no name of this length: cut a longer one down to size
                longer = [v for v in pool if len(v) > len(tok)] or pool
                choice = rng.choice(longer)[: len(tok)]
                choice = choice[:1].upper() + choice[1:]
            tmap[tok] = choice
            used.add(choice)
            taken.add(choice)
    return tmap


def _name_tokens(person: dict) -> list[str]:
    tokens: list[str] = []
    for text in [person["canonical"]] + [m["text"] for m in person.get("mentions", [])]:
        for tok in normalise_tokens(text):
            if tok not in tokens and tok not in SUFFIXES:
                tokens.append(tok)
    return tokens


def _persons_in_doc(persons: Iterable[dict], mentions: Iterable[dict]) -> list[dict]:
    keys = {tuple(normalise_tokens(m["text"])) for m in mentions}
    return [p for p in persons if any(tuple(normalise_tokens(m["text"])) in keys for m in p.get("mentions", []))]


def _person_tokens(person: dict) -> set[str]:
    out = set(person.get("tokens") or normalise_tokens(person["canonical"]))
    for m in person.get("mentions", []):
        out.update(normalise_tokens(m["text"]))
    return out - SUFFIXES


def _replace_tokens(
    text: str, persons: list[dict], tmap: dict[str, str], spans: list[tuple[int, int]], singles: set[str]
) -> tuple[str, list[_Token], int]:
    """New text, ``(old_start, old_end, new_start, new_end)`` per token, replaced count."""
    offsets = token_offsets(text)
    raw = [text[s:e] for s, e in offsets]
    norm = [normalise_token(t) for t in raw]
    mark = [False] * len(raw)
    for i, (s, e) in enumerate(offsets):
        if norm[i] in tmap and any(s < e2 and e > s2 for s2, e2 in spans):
            mark[i] = True
    for person in persons:
        toks = _person_tokens(person)
        i = 0
        while i < len(raw):
            if norm[i] not in toks and norm[i] not in PARTICLES:
                i += 1
                continue
            j, names = i, 0
            while j < len(raw) and (norm[j] in toks or norm[j] in PARTICLES or norm[j] in SUFFIXES):
                names += norm[j] in toks
                j += 1
            run = list(range(i, j))
            if names >= 2 or (names == 1 and any(norm[k] in singles for k in run)):
                for k in run:
                    if norm[k] in toks and norm[k] in tmap:
                        mark[k] = True
            i = max(j, i + 1)
    pieces: list[str] = []
    table: list[_Token] = []
    pos = 0
    new_pos = 0
    replaced = 0
    for i, (s, e) in enumerate(offsets):
        pieces.append(text[pos:s])
        new_pos += s - pos
        tok = raw[i]
        lead, core, trail = _EDGE.match(tok).groups()
        if mark[i]:
            tok = lead + render_like(tmap[norm[i]], core) + trail
            replaced += 1
        pieces.append(tok)
        table.append(_Token(s, e, new_pos, new_pos + len(tok), len(lead), len(trail)))
        new_pos += len(tok)
        pos = e
    pieces.append(text[pos:])
    return "".join(pieces), table, replaced


class _Token:
    """Old and new character span of one token, with the punctuation kept at its edges."""

    def __init__(self, s: int, e: int, ns: int, ne: int, lead: int, trail: int):
        self.s, self.e, self.ns, self.ne, self.lead, self.trail = s, e, ns, ne, lead, trail

    def map(self, p: int) -> int:
        if p - self.s <= self.lead:  # inside the leading punctuation
            return self.ns + (p - self.s)
        if self.e - p <= self.trail:  # inside (or right before) the trailing punctuation
            return self.ne - (self.e - p)
        core_old = (self.e - self.trail) - (self.s + self.lead)
        core_new = (self.ne - self.trail) - (self.ns + self.lead)
        return self.ns + self.lead + (p - self.s - self.lead) * core_new // core_old


def _remapper(table: list[_Token], old_len: int, new_len: int) -> Callable[[int, int], tuple[int, int]]:
    """Positions between tokens shift with the text; positions inside a token stay at its edges."""

    def one(p: int) -> int:
        shift = 0
        for t in table:
            if p <= t.s:
                return p + shift
            if p <= t.e:
                return t.map(p)
            shift = t.ne - t.e
        return min(p + shift, new_len)

    return lambda start, end: (one(start), one(end))


def pseudonymise_text(
    text: str, persons: Iterable[dict], tmap: dict[str, str], mentions: list[dict]
) -> tuple[str, Callable[[int, int], tuple[int, int]], int]:
    """Replace the marked mentions (and other runs of the same persons' tokens) in ``text``.

    Returns the new text, a ``(start, end) -> (start, end)`` offset remapper and the
    number of tokens replaced. The token count never changes.
    """
    persons = _persons_in_doc(persons, mentions)
    spans = [(int(m["start"]), int(m["end"])) for m in mentions]
    singles = {t[0] for m in mentions for t in [normalise_tokens(m["text"])] if len(t) == 1}
    new, table, replaced = _replace_tokens(text, persons, tmap, spans, singles)
    assert len(token_offsets(new)) == len(token_offsets(text)), "token count changed"
    return new, _remapper(table, len(text), len(new)), replaced


def pseudonymise_string(text: str, persons: Iterable[dict], tmap: dict[str, str], mentions: list[dict]) -> str:
    """Same replacement for a free string (a predicted span) of the same document."""
    persons = _persons_in_doc(persons, mentions)
    singles = {t[0] for m in mentions for t in [normalise_tokens(m["text"])] if len(t) == 1}
    return _replace_tokens(text, persons, tmap, [], singles)[0]
