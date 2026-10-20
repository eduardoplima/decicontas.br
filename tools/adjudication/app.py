"""FastAPI backend for the adjudication tool.

Reads the three annotator files, keeps the decisions in
``dataset/errors/adjudication-state.json`` and serves the React frontend built
for ``tools.review`` (which switches views on ``GET /api/mode``).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from research.release import paths
from tools.adjudication.decisions import PRE_ADJUDICATION, ConflictError
from tools.adjudication.state import AdjudicationState, load_state
from tools.review.app import FRONTEND_DIST

DECISIONS_PATH = paths.ADJUDICATION_DECISIONS_JSON


class Decision(BaseModel):
    action: str
    source: str | None = None
    label: str | None = None
    char_start: int | None = None
    char_end: int | None = None


def create_app(
    state: AdjudicationState | None = None,
    decisions_path: Path = DECISIONS_PATH,
    gold_release: Path | str | None = PRE_ADJUDICATION,
) -> FastAPI:
    """``gold_release``: the gold annotator 1 must still match when finishing (``None`` skips it)."""
    state = state or load_state()
    app = FastAPI(title="decicontas.br — adjudicação")

    @app.get("/api/mode")
    def mode():
        return {"mode": "adjudication"}

    @app.get("/api/adjudication/documents")
    def documents():
        return {"documents": state.documents(), "finished": state.data["finished"]}

    @app.get("/api/adjudication/changes")
    def changes():
        return state.changes()

    @app.put("/api/adjudication/decisions/{item_id}")
    def decide(item_id: str, body: Decision):
        item = state.by_id.get(item_id)
        if item is None:
            raise HTTPException(404, item_id)
        try:
            state.decide(
                item_id, body.action, source=body.source, label=body.label,
                char_start=body.char_start, char_end=body.char_end,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"document": state.document(item.doc_id)}

    @app.post("/api/adjudication/finish")
    def finish():
        try:
            summary = state.finish(decisions_path, gold_release)
        except ConflictError as exc:
            raise HTTPException(409, {"conflicts": [list(pair) for pair in exc.conflicts]}) from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"finished": True, "path": str(decisions_path), "summary": summary}

    if FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
    return app
