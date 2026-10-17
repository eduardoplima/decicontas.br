"""Build the person map from the finished review.

Persons marked *yes* in the review (grouped across spellings, with gender) get one
synthetic token per real name token; the map and the mentions per document go to
``docs/privacy/person_map.json`` (private — it re-identifies the pseudonyms).
``--extra`` adds persons that do not occur in the corpus (names inside the few-shot
exemplars), as a JSON list of ``{"canonical", "gender"}``.

    uv run python -m tools.review.build_map [--extra docs/privacy/extra_persons.json]
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from research.release import paths
from tools.review.app import load_state
from tools.review.find_persons import OUT_PATH as CANDIDATES_PATH
from tools.review.grouping import normalise_tokens
from tools.review.names import strip_role_prefix
from tools.review.pseudonymise import build_token_map, infer_gender, normalise_token

logger = logging.getLogger("tools.review.build_map")

STATE_PATH = paths.REPO_ROOT / "docs" / "privacy" / "review_state.json"
MAP_PATH = paths.REPO_ROOT / "docs" / "privacy" / "person_map.json"
SEED = 1007


def _mention(m: dict) -> dict:
    text, offset = strip_role_prefix(m["text"])
    return {"doc_id": m["doc_id"], "text": text, "start": m["start"] + offset, "end": m["end"]}


def build(
    persons: list[dict],
    extra: list[dict],
    seed: int = SEED,
    kept: set[tuple[str, ...]] = frozenset(),
    exclude: set[str] = frozenset(),
    overrides: dict[str, str] | None = None,
) -> dict:
    """``kept``: names that were also left untouched somewhere (homonyms); those mentions are
    replaced only inside their own documents, never in free text. ``exclude``: tokens that
    may not serve as pseudonyms (the vocabulary of the original corpus). ``overrides``: hand-picked
    pseudonyms for a few tokens (same length), used where the seeded choice shifted the fuzzy
    alignment of a stored prediction."""
    overrides = overrides or {}
    people = [
        {
            "id": p["id"],
            "canonical": p["canonical"],
            "gender": infer_gender(p["canonical"], p.get("gender")),
            "tokens": p["tokens"],
            "mentions": [_mention(m) for m in p["mentions"]],
        }
        for p in persons
    ]
    for person in people:
        person["canonical"], _ = strip_role_prefix(person["canonical"])
        person["tokens"] = normalise_tokens(person["canonical"])
    for e in extra:
        people.append(
            {
                "id": "extra:" + "-".join(normalise_tokens(e["canonical"])),
                "canonical": e["canonical"],
                "gender": infer_gender(e["canonical"], e.get("gender")),
                "tokens": normalise_tokens(e["canonical"]),
                "mentions": [{"doc_id": None, "text": e["canonical"], "start": -1, "end": -1}],
            }
        )
    for person in people:
        for m in person["mentions"]:
            m["ambiguous"] = tuple(normalise_tokens(m["text"])) in kept
    tokens = build_token_map(people, seed=seed, exclude=exclude)
    for real, synthetic in overrides.items():
        if len(synthetic) != len(real) or normalise_token(synthetic) in exclude | set(tokens):
            raise ValueError(f"override {real!r} -> {synthetic!r}: length or vocabulary clash")
        tokens[real] = synthetic
    return {"seed": seed, "n_persons": len(people), "tokens": tokens, "persons": people}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--candidates", type=Path, default=CANDIDATES_PATH)
    parser.add_argument("--state", type=Path, default=STATE_PATH)
    parser.add_argument("--extra", type=Path)
    parser.add_argument("--overrides", type=Path, help="JSON {real token: synthetic token}")
    parser.add_argument("--out", type=Path, default=MAP_PATH)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    state = load_state(args.candidates, args.state)
    extra = json.loads(args.extra.read_text(encoding="utf-8")) if args.extra else []
    kept = {
        tuple(normalise_tokens(m["text"]))
        for m in state.candidates.values()
        if state.decision(m["id"]) != "yes"
    }
    # run on the original export: its vocabulary is what the pseudonyms must avoid
    vocabulary = {normalise_token(t) for doc in state.docs.values() for t in doc.split()}
    overrides = json.loads(args.overrides.read_text(encoding="utf-8")) if args.overrides else {}
    data = build(state.persons(), extra, kept=kept, exclude=vocabulary, overrides=overrides)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    logger.info(
        "%d persons (%d extra), %d real tokens -> %d synthetic tokens; %s",
        data["n_persons"], len(extra), len(data["tokens"]), len(set(data["tokens"].values())), args.out,
    )


if __name__ == "__main__":
    main()
