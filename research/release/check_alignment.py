"""Fail loudly when the prediction layouts disagree about documents or tokens.

The paired bootstrap and every per-model table join predictions by *row
position*, never by document id. Three layouts have to agree for that join to
mean anything:

* the LLM result JSONs, one dict per master position (866 rows);
* the supervised out-of-fold JSONs, one record whose ``true_labels`` and
  ``pred_labels`` are 866 lists, empty at the few-shot positions;
* the released gold, 861 documents sorted by id.

Nothing in the pipeline checked this before. A mismatch would silently pair
one model's document with another's and still produce plausible-looking F1.

Run it as ``uv run python -m research.release.check_alignment``; it exits
non-zero when a problem is found.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from research.dataset_io import token_offsets
from research.fewshot import FEWSHOT_RESULT_POSITIONS
from research.release import paths

logger = logging.getLogger(__name__)

N_MASTER = 866


def master_to_release_index() -> dict[int, int]:
    """Map master row position (0..865) to release index (0..860).

    The raw Label Studio export carries ids 1..866 in order, so master
    position ``p`` is dataset id ``p + 1``; the release drops the five
    few-shot exemplars.
    """
    skipped = set(FEWSHOT_RESULT_POSITIONS)
    mapping: dict[int, int] = {}
    release_idx = 0
    for position in range(N_MASTER):
        if position in skipped:
            continue
        mapping[position] = release_idx
        release_idx += 1
    return mapping


def _check_supervised(
    record: dict, release: list[dict], m2r: dict[int, int], name: str
) -> tuple[list[str], list[str], int]:
    """Return ``(fatal, warnings, n_truncated)`` for one supervised layout."""
    problems: list[str] = []
    warnings: list[str] = []
    stale: list[int] = []
    truncated = 0
    true_labels = record["true_labels"]
    pred_labels = record["pred_labels"]
    if len(true_labels) != N_MASTER or len(pred_labels) != N_MASTER:
        problems.append(
            f"{name}: expected {N_MASTER} rows, got "
            f"{len(true_labels)}/{len(pred_labels)}"
        )
        return problems, warnings, truncated
    for position in FEWSHOT_RESULT_POSITIONS:
        if true_labels[position]:
            problems.append(f"{name}: few-shot position {position} is not empty")
    for position, release_idx in m2r.items():
        gold_tags = release[release_idx]["ner_tags"]
        doc_id = release[release_idx]["id"]
        seq = true_labels[position]
        n = len(seq)
        if n > len(gold_tags):
            problems.append(
                f"{name}: doc {doc_id} has more BIO tags ({n}) than gold "
                f"({len(gold_tags)})"
            )
        elif n < len(gold_tags):
            truncated += 1
        if seq[:n] != gold_tags[:n]:
            stale.append(doc_id)
    if stale:
        warnings.append(
            f"{name}: trained against a stale gold on document(s) "
            f"{stale} — predictions are rescored against the current gold"
        )
    return problems, warnings, truncated


def _check_llm(
    rows: list[dict], release: list[dict], m2r: dict[int, int], name: str
) -> tuple[list[str], list[str]]:
    """Return ``(fatal, warnings)`` for one LLM layout."""
    problems: list[str] = []
    warnings: list[str] = []
    shifted: list[int] = []
    if len(rows) != N_MASTER:
        problems.append(f"{name}: expected {N_MASTER} rows, got {len(rows)}")
        return problems, warnings
    for position, release_idx in m2r.items():
        doc = release[release_idx]
        doc_id = doc["id"]
        llm_text = rows[position].get("text") or ""
        if llm_text.strip() != doc["text"].strip():
            problems.append(f"{name}: doc {doc_id} text differs from the release")
            continue
        if len(token_offsets(llm_text)) != len(doc["tokens"]):
            problems.append(f"{name}: doc {doc_id} token count differs from the release")
        if llm_text != doc["text"]:
            leading = len(doc["text"]) - len(doc["text"].lstrip())
            if leading and not llm_text.startswith(doc["text"][:leading]):
                shifted.append(doc_id)
    if shifted:
        warnings.append(
            f"{name}: document(s) {shifted} have leading whitespace in the gold "
            "text that the prediction text lacks; offsets are shifted to compensate"
        )
    return problems, warnings


def check(
    input_dir: Path | None = None,
    gold_path: Path | None = None,
) -> tuple[list[str], list[str], dict[str, int]]:
    """Return ``(fatal_problems, warnings, truncation_counts)``.

    A fatal problem means predictions cannot be joined to documents at all:
    wrong row count, a document whose text or token count does not match the
    release. A warning means the numbers are still computable but something
    about them has to be reported — a model trained against a stale gold, or
    a text whose leading whitespace shifts the offsets it was predicted in.
    """
    input_dir = input_dir or paths.OUTPUT_CORRECTED_DIR
    gold_path = gold_path or paths.CORRECTED_GOLD_JSON

    release = json.loads(Path(gold_path).read_text(encoding="utf-8"))
    release.sort(key=lambda d: d["id"])
    m2r = master_to_release_index()

    problems: list[str] = []
    warnings: list[str] = []
    truncation: dict[str, int] = {}

    if len(release) != len(m2r):
        problems.append(
            f"release has {len(release)} documents, expected {len(m2r)}"
        )
        return problems, warnings, truncation

    for doc in release:
        offsets = token_offsets(doc["text"])
        if len(offsets) != len(doc["tokens"]) or len(offsets) != len(
            doc["token_offsets"]
        ):
            problems.append(f"release doc {doc['id']}: token counts disagree")

    for path in sorted(Path(input_dir).glob("models_results_decicontas_*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        name = path.stem.replace("models_results_decicontas_", "")
        record = raw[0] if isinstance(raw, list) and len(raw) == 1 else raw
        if isinstance(record, dict) and "true_labels" in record:
            found, warned, truncated = _check_supervised(record, release, m2r, name)
            problems.extend(found)
            warnings.extend(warned)
            truncation[name] = truncated
        else:
            found, warned = _check_llm(raw, release, m2r, name)
            problems.extend(found)
            warnings.extend(warned)

    return problems, warnings, truncation


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    problems, warnings, truncation = check()
    for name, count in sorted(truncation.items()):
        if count:
            logger.info(
                "%s: %d document(s) truncated by the encoder's input limit; "
                "scored against the full gold, so the tail counts as recall loss",
                name,
                count,
            )
    for warning in warnings:
        logger.warning("ALIGNMENT: %s", warning)
    if problems:
        for problem in problems:
            logger.error("ALIGNMENT: %s", problem)
        logger.error("%d alignment problem(s) found", len(problems))
        return 1
    logger.info("alignment OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
