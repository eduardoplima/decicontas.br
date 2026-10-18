"""Decisions kept by tools.adjudication.state.AdjudicationState."""

from __future__ import annotations

import json
import logging

import pytest
from tests.adjudication_fixture import MULTA, char_span, view

from tools.adjudication.divergences import build_all
from tools.adjudication.state import AdjudicationState

REC = (28, 35, "RECOMENDACAO")


def _state(tmp_path, a1, a2, a3, sha=None):
    docs = {7: view(a1, a2, a3)}
    return AdjudicationState(tmp_path / "state.json", docs, build_all(docs), sha)


def test_default_decision_until_an_explicit_one_and_pending_clears_it(tmp_path):
    state = _state(tmp_path, [MULTA], [MULTA, REC], [MULTA, REC])
    assert state.decision("7:add:28-35")["action"] == "include"
    state.decide("7:add:28-35", "reject")
    assert state.decision("7:add:28-35")["action"] == "reject"
    state.decide("7:add:28-35", "pending")
    assert state.decision("7:add:28-35")["action"] == "include"


def test_actions_are_validated_against_the_item_kind(tmp_path):
    gold_obr = (12, 16, "OBRIGACAO")
    state = _state(
        tmp_path,
        [MULTA, gold_obr, (17, 21, "RESSARCIMENTO")],
        [MULTA, REC, (17, 21, "MULTA")],
        [MULTA, (28, 35, "OBRIGACAO")],
    )
    with pytest.raises(ValueError):
        state.decide("7:gold:12-16", "include")
    with pytest.raises(ValueError):
        state.decide("7:add:28-35", "include", source="A1")
    with pytest.raises(ValueError):
        state.decide("7:add:28-35", "include")  # A2 and A3 disagree on the label: it must be given
    state.decide("7:add:28-35", "include", source="A3", label="OBRIGACAO")
    assert state.decision("7:add:28-35") == {
        "action": "include", "source": "A3", "start": 28, "end": 35, "label": "OBRIGACAO",
        "decided_at": state.decision("7:add:28-35")["decided_at"],
    }
    with pytest.raises(ValueError):
        state.decide("7:label:17-21", "relabel", label="RESSARCIMENTO")
    state.decide("7:label:17-21", "relabel", label="MULTA")
    state.decide("7:gold:12-16", "remove")
    with pytest.raises(KeyError):
        state.decide("7:add:1-2", "reject")


def test_an_include_that_overlaps_another_included_span_is_refused(tmp_path):
    # A2: [28,32) REC and [32,35) OBR; A3: one long [28,35) REC -> items 28-35 (A2+A3) and 32-35 (A2)
    state = _state(tmp_path, [MULTA], [MULTA, (28, 32, "RECOMENDACAO"), (32, 35, "OBRIGACAO")], [MULTA, (28, 35, "RECOMENDACAO")])
    state.decide("7:add:28-35", "include", source="A3")
    with pytest.raises(ValueError, match="7:add:28-35"):
        state.decide("7:add:32-35", "include")
    assert state.decision("7:add:32-35") is None and state.decision("7:add:28-35")["source"] == "A3"
    state.decide("7:add:28-35", "include", source="A2")  # the shorter candidate leaves room
    state.decide("7:add:32-35", "include")
    assert state.decision("7:add:32-35")["action"] == "include"


def test_decisions_survive_a_reload(tmp_path):
    state = _state(tmp_path, [MULTA], [MULTA, REC], [MULTA])
    state.decide("7:add:28-35", "include")
    stored = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert stored["decisions"]["7:add:28-35"]["action"] == "include" and stored["version"] == "1"
    again = _state(tmp_path, [MULTA], [MULTA, REC], [MULTA])
    assert again.decision("7:add:28-35")["source"] == "A2"


def test_document_payload_marks_gold_items_replaced_by_an_included_span(tmp_path):
    gold = (0, 16, "MULTA")
    state = _state(tmp_path, [gold], [(5, 9, "MULTA"), (10, 16, "MULTA")], [])
    payload = state.document(7)
    assert payload["doc_id"] == 7 and set(payload["layers"]) == {"A1", "A2", "A3"}
    assert payload["layers"]["A1"] == [{"start": 0, "end": 16, "char_start": 0, "char_end": char_span(0, 16)[1], "label": "MULTA"}]
    items = {i["id"]: i for i in payload["items"]}
    assert items["7:gold:0-16"]["decision"] is None and items["7:gold:0-16"]["replaced_by"] is None
    state.decide("7:gold:0-16", "keep")
    state.decide("7:add:10-16", "include")
    items = {i["id"]: i for i in state.document(7)["items"]}
    assert items["7:add:10-16"]["decision"]["action"] == "include" and items["7:add:10-16"]["explicit"]
    assert items["7:gold:0-16"]["decision"]["action"] == "replaced"
    assert items["7:gold:0-16"]["replaced_by"] == "7:add:10-16"
    assert items["7:add:5-9"]["default"] is None and items["7:add:5-9"]["decision"] is None


def test_annotator_hash_mismatch_only_warns_and_orphan_decisions_are_dropped(tmp_path, caplog):
    (tmp_path / "state.json").write_text(
        json.dumps({"annotators_sha256": {"anotador1.jsonl": "old"}, "decisions": {"9:add:1-2": {"action": "reject"}}}),
        encoding="utf-8",
    )
    with caplog.at_level(logging.WARNING):
        state = _state(tmp_path, [MULTA], [MULTA, REC], [MULTA], sha={"anotador1.jsonl": "new"})
    assert "sha256" in caplog.text
    assert state.data["decisions"] == {} and state.data["annotators_sha256"] == {"anotador1.jsonl": "new"}
