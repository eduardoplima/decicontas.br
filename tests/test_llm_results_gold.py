"""The gold embedded in every LLM result file equals the release."""

from __future__ import annotations

import json

import pytest

from research.release import paths

LLM_RESULT_FILES = [
    *sorted(
        p
        for p in paths.OUTPUT_CORRECTED_DIR.glob("models_results_decicontas_*.json")
        if "__supervised" not in p.name
    ),
    *sorted((paths.CORRECTED_EXPERIMENTS_DIR / "function_calling_json_schema").glob("*.json")),
    *sorted((paths.CORRECTED_EXPERIMENTS_DIR / "prompt_engineering").glob("*.json")),
]


@pytest.fixture(scope="module")
def release_by_text() -> dict[str, list[tuple[int, int, str]]]:
    if not paths.CORRECTED_GOLD_JSON.exists():
        pytest.skip("release not available")
    docs = json.loads(paths.CORRECTED_GOLD_JSON.read_text(encoding="utf-8"))
    return {
        d["text"].strip(): sorted((e["start"], e["end"], e["label"]) for e in d["entities"])
        for d in docs
    }


@pytest.mark.parametrize("path", LLM_RESULT_FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_embedded_gold_equals_the_release(path, release_by_text):
    rows = json.loads(path.read_text(encoding="utf-8"))
    matched = 0
    for row in rows:
        expected = release_by_text.get((row.get("text") or "").strip())
        if expected is None:
            continue  # few-shot exemplars are not in the release
        golden = sorted(
            (int(g["start"]), int(g["end"]), g["labels"][0]) for g in row.get("golden") or []
        )
        assert golden == expected, f"{path.name}: gold differs from the release"
        matched += 1
    assert matched == 861
