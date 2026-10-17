"""FastAPI backend for the person-mention review tool.

Reads ``docs/privacy/persons_candidates.json`` (written by ``find_persons``),
keeps the decisions in ``docs/privacy/review_state.json`` and serves the built
React frontend from ``tools/review/frontend/dist``.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from research.release import paths
from tools.review.state import ReviewState

PRIVACY_DIR = paths.REPO_ROOT / "docs" / "privacy"
CANDIDATES_PATH = PRIVACY_DIR / "persons_candidates.json"
STATE_PATH = PRIVACY_DIR / "review_state.json"
FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"


class Decision(BaseModel):
    value: str


class Mention(BaseModel):
    doc_id: int
    text: str


class Ids(BaseModel):
    mention_ids: list[str]


class Gender(BaseModel):
    gender: str | None


def load_state(candidates_path: Path = CANDIDATES_PATH, state_path: Path = STATE_PATH) -> ReviewState:
    payload = json.loads(candidates_path.read_text(encoding="utf-8"))
    return ReviewState(state_path, payload["candidates"], payload["documents"])


def create_app(state: ReviewState | None = None) -> FastAPI:
    state = state or load_state()
    app = FastAPI(title="decicontas.br — revisão de pessoas")

    @app.get("/api/documents")
    def documents():
        return {"documents": state.documents(), "finished": state.data["finished"]}

    @app.put("/api/decisions/{mention_id}")
    def decide(mention_id: str, body: Decision):
        if mention_id not in state.candidates:
            raise HTTPException(404, mention_id)
        updated = state.decide(mention_id, body.value)
        return {"id": mention_id, "decision": state.decision(mention_id), "updated": updated}

    @app.post("/api/mentions")
    def add_mention(body: Mention):
        try:
            return state.add_mention(body.doc_id, body.text)
        except (KeyError, ValueError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/persons")
    def persons():
        return {"persons": state.persons()}

    @app.post("/api/persons/merge")
    def merge(body: Ids):
        state.merge(body.mention_ids)
        return {"persons": state.persons()}

    @app.post("/api/persons/split")
    def split(body: Ids):
        state.split(body.mention_ids)
        return {"persons": state.persons()}

    @app.post("/api/persons/{group_id}/gender")
    def gender(group_id: str, body: Gender):
        state.set_gender(group_id, body.gender)
        return {"persons": state.persons()}

    @app.post("/api/finish")
    def finish():
        state.finish(True)
        return {"finished": True, "persons": len(state.persons())}

    if FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
    return app
