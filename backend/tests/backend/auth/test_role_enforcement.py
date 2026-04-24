"""``require_role`` rejects wrong-role users with 403.

Uses a throwaway FastAPI app mounted only for this test — production routers
must stay untouched.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


def _build_admin_only_app(test_session_factory):
    from app.deps import get_db_session, require_role

    app = FastAPI()

    @app.get("/admin-only")
    def admin_only(user=Depends(require_role("admin"))):
        return {"id": user.IdUsuario, "role": user.Papel.value}

    @app.get("/reviewer-only")
    def reviewer_only(user=Depends(require_role("reviewer"))):
        return {"id": user.IdUsuario, "role": user.Papel.value}

    def _override_db():
        s = test_session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db_session] = _override_db
    return app


def _login_token(real_client: TestClient, username: str, password: str) -> str:
    resp = real_client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_reviewer_cannot_reach_admin_only(
    api_client: TestClient, make_user, test_session_factory
) -> None:
    make_user(username="rev", password="pw", role="reviewer")
    token = _login_token(api_client, "rev", "pw")

    throwaway = _build_admin_only_app(test_session_factory)
    with TestClient(throwaway) as c:
        resp = c.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

        ok = c.get("/reviewer-only", headers={"Authorization": f"Bearer {token}"})
        assert ok.status_code == 200


def test_admin_reaches_admin_only(
    api_client: TestClient, make_user, test_session_factory
) -> None:
    make_user(username="boss", password="pw", role="admin")
    token = _login_token(api_client, "boss", "pw")

    throwaway = _build_admin_only_app(test_session_factory)
    with TestClient(throwaway) as c:
        resp = c.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"
