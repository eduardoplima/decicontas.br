"""End-to-end tests for the auth router via ``TestClient``."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient


def _login(client: TestClient, username: str, password: str):
    return client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )


def test_login_success_and_me(api_client: TestClient, make_user) -> None:
    user = make_user(username="alice", password="hunter2")

    resp = _login(api_client, "alice", "hunter2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]

    me = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == "alice"
    assert me.json()["role"] == user["role"]


def test_login_wrong_password_returns_401(api_client: TestClient, make_user) -> None:
    make_user(username="bob", password="correct")
    resp = _login(api_client, "bob", "wrong")
    assert resp.status_code == 401


def test_login_inactive_user_returns_401(api_client: TestClient, make_user) -> None:
    make_user(username="ghost", password="pw", is_active=False)
    resp = _login(api_client, "ghost", "pw")
    assert resp.status_code == 401


def test_refresh_rotation_invalidates_old_token(
    api_client: TestClient, make_user
) -> None:
    make_user(username="alice", password="hunter2")
    first = _login(api_client, "alice", "hunter2").json()

    rotated = api_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )
    assert rotated.status_code == 200
    second = rotated.json()
    assert second["refresh_token"] != first["refresh_token"]
    assert second["access_token"] != first["access_token"]

    reused = api_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )
    assert reused.status_code == 401

    # New refresh token still works.
    again = api_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": second["refresh_token"]}
    )
    assert again.status_code == 200


def test_logout_revokes_refresh(api_client: TestClient, make_user) -> None:
    make_user(username="alice", password="hunter2")
    pair = _login(api_client, "alice", "hunter2").json()

    out = api_client.post(
        "/api/v1/auth/logout", json={"refresh_token": pair["refresh_token"]}
    )
    assert out.status_code == 204

    blocked = api_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]}
    )
    assert blocked.status_code == 401


def test_access_token_expiration_returns_401(
    api_client: TestClient, make_user, monkeypatch
) -> None:
    """An expired access token must be rejected by ``/me`` with 401."""
    from app.auth import security

    make_user(username="alice", password="pw")

    # Mint the token as if issued two hours ago. With the default 60-minute
    # TTL, ``exp`` lands one hour in the past — jose rejects it at decode.
    original_now = security._now
    monkeypatch.setattr(security, "_now", lambda: original_now() - timedelta(hours=2))
    login = _login(api_client, "alice", "pw").json()
    monkeypatch.undo()

    me = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert me.status_code == 401


def test_invalid_access_token_returns_401(api_client: TestClient) -> None:
    me = api_client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert me.status_code == 401
