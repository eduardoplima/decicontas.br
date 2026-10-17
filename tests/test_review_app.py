"""HTTP surface of the review tool (tools.review.app)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from tools.review.app import create_app, load_state

TEXT = "multa ao Sr. Teobaldo Quaresma Lins e ressarcimento pela Sra. Maria Costa, nos termos do inciso II."
PAYLOAD = {
    "documents": {"7": TEXT},
    "candidates": [
        {"id": "7:0", "doc_id": 7, "text": "Teobaldo Quaresma Lins", "start": 13, "end": 35, "sources": ["spacy", "llm"], "context": ""},
        {"id": "7:1", "doc_id": 7, "text": "inciso II", "start": TEXT.index("inciso II"), "end": TEXT.index("inciso II") + 9, "sources": ["spacy"], "context": ""},
    ],
}


def _client(tmp_path):
    candidates = tmp_path / "persons_candidates.json"
    candidates.write_text(json.dumps(PAYLOAD), encoding="utf-8")
    return TestClient(create_app(load_state(candidates, tmp_path / "review_state.json")))


def test_documents_carry_candidates_with_their_current_decision(tmp_path):
    client = _client(tmp_path)
    docs = client.get("/api/documents").json()["documents"]
    assert [m["decision"] for m in docs[0]["mentions"]] == ["yes", None]


def test_deciding_and_adding_a_mention_feed_the_person_groups(tmp_path):
    client = _client(tmp_path)
    assert client.put("/api/decisions/7:1", json={"value": "no"}).json()["decision"] == "no"
    added = client.post("/api/mentions", json={"doc_id": 7, "text": "Maria Costa"}).json()
    assert added["start"] == TEXT.index("Maria Costa")
    persons = client.get("/api/persons").json()["persons"]
    assert [(p["canonical"], p["gender"]) for p in persons] == [("Maria Costa", "F"), ("Teobaldo Quaresma Lins", "M")]
    assert client.post("/api/decisions/unknown", json={"value": "no"}).status_code == 405
    assert client.put("/api/decisions/unknown", json={"value": "no"}).status_code == 404


def test_merge_split_and_finish(tmp_path):
    client = _client(tmp_path)
    client.post("/api/mentions", json={"doc_id": 7, "text": "Maria Costa"})
    merged = client.post("/api/persons/merge", json={"mention_ids": ["7:0", "7:m0"]}).json()["persons"]
    assert len(merged) == 1
    split = client.post("/api/persons/split", json={"mention_ids": ["7:m0"]}).json()["persons"]
    assert len(split) == 2
    assert client.post("/api/finish").json() == {"finished": True, "persons": 2}
