"""Persistence of the review decisions (tools.review.state)."""

from __future__ import annotations

import json

from tools.review.state import ReviewState

CANDIDATES = [
    {"id": "7:0", "doc_id": 7, "text": "Teobaldo Quaresma Lins", "start": 13, "end": 35, "sources": ["spacy", "llm"]},
    {"id": "7:1", "doc_id": 7, "text": "inciso II", "start": 40, "end": 49, "sources": ["spacy"]},
]
DOCS = {7: "multa ao Sr. Teobaldo Quaresma Lins, nos termos do inciso II, da LCE."}


def test_high_confidence_candidates_start_as_yes_and_the_rest_as_pending(tmp_path):
    state = ReviewState(tmp_path / "state.json", CANDIDATES, DOCS)
    assert state.decision("7:0") == "yes"
    assert state.decision("7:1") is None


def test_decisions_survive_a_reload(tmp_path):
    path = tmp_path / "state.json"
    state = ReviewState(path, CANDIDATES, DOCS)
    state.decide("7:1", "no")
    state.decide("7:0", "no")
    again = ReviewState(path, CANDIDATES, DOCS)
    assert again.decision("7:0") == "no" and again.decision("7:1") == "no"
    assert json.loads(path.read_text())["decisions"]["7:0"] == "no"


def test_a_decision_applies_to_the_same_name_repeated_in_the_document(tmp_path):
    repeated = CANDIDATES + [
        {"id": "7:2", "doc_id": 7, "text": "TEOBALDO QUARESMA LINS", "start": 60, "end": 82, "sources": ["caps"]},
        {"id": "8:0", "doc_id": 8, "text": "Teobaldo Quaresma Lins", "start": 0, "end": 22, "sources": ["caps"]},
    ]
    state = ReviewState(tmp_path / "state.json", repeated, {**DOCS, 8: "Teobaldo Quaresma Lins"})
    assert sorted(state.decide("7:0", "no")) == ["7:0", "7:2"]
    assert state.decision("7:2") == "no" and state.decision("8:0") is None


def test_manual_mention_is_located_in_the_text_and_marked_yes(tmp_path):
    state = ReviewState(tmp_path / "state.json", CANDIDATES, DOCS)
    mention = state.add_mention(7, "LCE")
    assert (mention["start"], mention["end"]) == (DOCS[7].index("LCE"), DOCS[7].index("LCE") + 3)
    assert state.decision(mention["id"]) == "yes"
    assert mention["sources"] == ["manual"]


def test_marked_mentions_feed_the_person_groups(tmp_path):
    state = ReviewState(tmp_path / "state.json", CANDIDATES, DOCS)
    state.decide("7:1", "no")
    groups = state.persons()
    assert [g["canonical"] for g in groups] == ["Teobaldo Quaresma Lins"]
    state.set_gender(groups[0]["id"], "M")
    assert state.persons()[0]["gender"] == "M"
