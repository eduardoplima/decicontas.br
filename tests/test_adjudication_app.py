"""HTTP surface of the adjudication tool (tools.adjudication.app)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from tests.adjudication_fixture import MULTA, OFFSETS, TEXT
from tools.adjudication.app import create_app, load_state

REC = (28, 35, "RECOMENDACAO")


def _jsonl(path, spans, doc_id=7):
    rec = {"id": doc_id, "text": TEXT, "spans": [{"start": OFFSETS[s][0], "end": OFFSETS[e - 1][1], "label": lab} for s, e, lab in spans]}
    path.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")


def _client(tmp_path, a1=(MULTA,), a2=(MULTA, REC), a3=(MULTA, REC)):
    _jsonl(tmp_path / "anotador1.jsonl", a1)
    _jsonl(tmp_path / "anotador2.jsonl", a2)
    _jsonl(tmp_path / "anotador3.jsonl", a3)
    state = load_state(tmp_path, tmp_path / "adjudication-state.json")
    return TestClient(create_app(state, decisions_path=tmp_path / "adjudication-decisions.json", gold_release=None))


def test_mode_and_documents_with_items(tmp_path):
    client = _client(tmp_path)
    assert client.get("/api/mode").json() == {"mode": "adjudication"}
    data = client.get("/api/adjudication/documents").json()
    assert data["finished"] is False and [d["doc_id"] for d in data["documents"]] == [7]
    (item,) = data["documents"][0]["items"]
    assert item["id"] == "7:add:28-35" and item["decision"]["action"] == "include" and not item["explicit"]
    assert data["documents"][0]["layers"]["A2"][1]["label"] == "RECOMENDACAO"


def test_decisions_return_the_updated_document_and_validate(tmp_path):
    client = _client(tmp_path)
    r = client.put("/api/adjudication/decisions/7:add:28-35", json={"action": "reject"})
    assert r.status_code == 200
    (item,) = r.json()["document"]["items"]
    assert item["decision"]["action"] == "reject" and item["explicit"]
    assert client.put("/api/adjudication/decisions/7:add:28-35", json={"action": "remove"}).status_code == 400
    assert client.put("/api/adjudication/decisions/7:add:1-2", json={"action": "reject"}).status_code == 404
    r = client.put("/api/adjudication/decisions/7:add:28-35", json={"action": "pending"})
    assert r.json()["document"]["items"][0]["decision"]["action"] == "include"


def test_finish_writes_the_decisions_file_and_reports_the_summary(tmp_path):
    client = _client(tmp_path)
    r = client.post("/api/adjudication/finish")
    assert r.status_code == 200
    body = r.json()
    assert body["finished"] is True and body["path"].endswith("adjudication-decisions.json")
    assert body["summary"]["include"] == 1 and body["summary"]["entities_after"]["RECOMENDACAO"] == 1
    written = json.loads((tmp_path / "adjudication-decisions.json").read_text(encoding="utf-8"))
    assert len(written["token_changes"]) == 7
    assert client.get("/api/adjudication/documents").json()["finished"] is True


def test_finish_reports_conflicting_inclusions(tmp_path):
    client = _client(tmp_path, a2=(MULTA, (28, 32, "RECOMENDACAO")), a3=(MULTA, (31, 35, "OBRIGACAO")))
    for item_id in ("7:add:28-32", "7:add:31-35"):
        assert client.put(f"/api/adjudication/decisions/{item_id}", json={"action": "include"}).status_code == 200
    r = client.post("/api/adjudication/finish")
    assert r.status_code == 409 and r.json()["detail"]["conflicts"] == [["7:add:28-32", "7:add:31-35"]]
