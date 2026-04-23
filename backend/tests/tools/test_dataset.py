"""Characterization tests for ``tools.dataset.translate_golden``."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tools.dataset import translate_golden

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _annot(
    labels: list[str], start: int = 0, end: int = 10, text: str = "sample"
) -> list[dict]:
    """Build a Label Studio-shaped annotation list for a single result."""
    return [
        {
            "result": [
                {
                    "value": {
                        "start": start,
                        "end": end,
                        "text": text,
                        "labels": labels,
                    }
                }
            ]
        }
    ]


@pytest.mark.parametrize(
    "input_label,expected_label",
    [
        ("MULTA_FIXA", "MULTA"),
        ("MULTA_PERCENTUAL", "MULTA"),
        ("OBRIGACAO_MULTA", "OBRIGACAO"),
        ("MULTA", "MULTA"),
        ("OBRIGACAO", "OBRIGACAO"),
        ("RESSARCIMENTO", "RESSARCIMENTO"),
        ("RECOMENDACAO", "RECOMENDACAO"),
        ("ALGO_NOVO", "ALGO_NOVO"),
    ],
)
def test_translate_golden_label_mapping(input_label: str, expected_label: str) -> None:
    out = translate_golden(_annot([input_label]))
    assert out[0]["result"][0]["value"]["labels"] == [expected_label]


def test_translate_golden_preserves_start_end_text() -> None:
    out = translate_golden(
        _annot(["MULTA_FIXA"], start=12, end=42, text="MULTA no valor de R$ 500,00")
    )
    value = out[0]["result"][0]["value"]
    assert value["start"] == 12
    assert value["end"] == 42
    assert value["text"] == "MULTA no valor de R$ 500,00"


def test_translate_golden_mutates_in_place() -> None:
    """Reassigns ``r['value']`` on the caller's list and returns the same list."""
    annotations = _annot(["MULTA_FIXA"])
    returned = translate_golden(annotations)
    assert returned is annotations
    assert annotations[0]["result"][0]["value"]["labels"] == ["MULTA"]


def test_translate_golden_skips_empty_result() -> None:
    annotations = [{"result": []}]
    original = copy.deepcopy(annotations)
    assert translate_golden(annotations) == original


def test_translate_golden_skips_missing_result_key() -> None:
    annotations = [{"id": 1}]
    original = copy.deepcopy(annotations)
    assert translate_golden(annotations) == original


@pytest.mark.xfail(
    strict=True,
    reason=(
        "translate_golden consults only labels[0] and drops the rest. "
        "Follow-up: decide whether multi-label input is legal for this dataset."
    ),
)
def test_translate_golden_preserves_additional_labels() -> None:
    out = translate_golden(_annot(["MULTA_FIXA", "SOMETHING_ELSE"]))
    assert out[0]["result"][0]["value"]["labels"] == ["MULTA", "SOMETHING_ELSE"]


def test_labeled_sample_fixture_shape() -> None:
    with (FIXTURES_DIR / "labeled_sample.json").open(encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, list) and len(data) == 2
    for decision in data:
        assert "id" in decision
        assert "data" in decision and "text" in decision["data"]
        assert decision["annotations"]
        for annotation in decision["annotations"]:
            for r in annotation["result"]:
                assert set(r["value"]) >= {"start", "end", "text", "labels"}


def test_labeled_sample_translate_golden_end_to_end() -> None:
    with (FIXTURES_DIR / "labeled_sample.json").open(encoding="utf-8") as f:
        data = json.load(f)

    flat = [ann for decision in data for ann in decision["annotations"]]
    translate_golden(flat)

    labels_seen = {r["value"]["labels"][0] for ann in flat for r in ann["result"]}
    assert labels_seen == {"MULTA", "OBRIGACAO"}
