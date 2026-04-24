"""``POST /api/v1/reviews/{kind}/{id}/claim`` — atomic claim and TTL rules."""

from __future__ import annotations

from datetime import datetime, timedelta


def test_claim_happy_path(authenticated_client, make_staging_obrigacao) -> None:
    client, me, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao()

    resp = client.post(f"/api/v1/reviews/obrigacao/{staged['id']}/claim")
    assert resp.status_code == 200
    body = resp.json()
    assert body["claimed_by"] == "alice"
    assert body["claimed_at"] is not None
    assert body["expires_at"] > body["claimed_at"]


def test_claim_conflict_when_held_by_other(
    authenticated_client, make_staging_obrigacao
) -> None:
    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao(claimed_by="bob", claimed_at=datetime.utcnow())
    resp = client.post(f"/api/v1/reviews/obrigacao/{staged['id']}/claim")
    assert resp.status_code == 409
    assert "bob" in resp.json()["detail"]


def test_claim_acquired_after_ttl_expires(
    authenticated_client, make_staging_obrigacao
) -> None:
    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao(
        claimed_by="bob", claimed_at=datetime.utcnow() - timedelta(hours=1)
    )
    resp = client.post(f"/api/v1/reviews/obrigacao/{staged['id']}/claim")
    assert resp.status_code == 200
    assert resp.json()["claimed_by"] == "alice"


def test_claim_is_idempotent_for_same_user(
    authenticated_client, make_staging_obrigacao
) -> None:
    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao()

    first = client.post(f"/api/v1/reviews/obrigacao/{staged['id']}/claim")
    second = client.post(f"/api/v1/reviews/obrigacao/{staged['id']}/claim")
    assert first.status_code == 200
    assert second.status_code == 200


def test_claim_404_when_missing(authenticated_client) -> None:
    client, _, _ = authenticated_client(username="alice")
    resp = client.post("/api/v1/reviews/obrigacao/999999/claim")
    assert resp.status_code == 404


def test_release_is_idempotent(authenticated_client, make_staging_obrigacao) -> None:
    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao()
    client.post(f"/api/v1/reviews/obrigacao/{staged['id']}/claim")

    r1 = client.post(f"/api/v1/reviews/obrigacao/{staged['id']}/release")
    r2 = client.post(f"/api/v1/reviews/obrigacao/{staged['id']}/release")
    assert r1.status_code == 204
    assert r2.status_code == 204
