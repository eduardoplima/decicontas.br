"""``GET /api/v1/reviews`` — list behavior, in particular claim-visibility."""

from __future__ import annotations

from datetime import datetime, timedelta


def test_list_excludes_active_claim_by_other_user(
    authenticated_client, make_staging_obrigacao
) -> None:
    client, me, _ = authenticated_client(username="alice")

    # Row claimed by someone else, claim still active.
    make_staging_obrigacao(
        descricao="claimed by someone else",
        claimed_by="bob",
        claimed_at=datetime.utcnow(),
    )
    # My own row.
    mine = make_staging_obrigacao(descricao="mine — unclaimed")
    # Expired claim by another → should be visible.
    make_staging_obrigacao(
        descricao="stale claim",
        claimed_by="carol",
        claimed_at=datetime.utcnow() - timedelta(hours=1),
    )

    resp = client.get("/api/v1/reviews?kind=obrigacao")
    assert resp.status_code == 200
    body = resp.json()
    descricoes = {item["descricao"] for item in body["items"]}
    assert "mine — unclaimed" in descricoes
    assert "stale claim" in descricoes
    assert "claimed by someone else" not in descricoes
    assert body["total"] == 2


def test_list_includes_own_claim(authenticated_client, make_staging_obrigacao) -> None:
    client, me, _ = authenticated_client(username="alice")

    make_staging_obrigacao(
        descricao="my active claim",
        claimed_by="alice",
        claimed_at=datetime.utcnow(),
    )
    resp = client.get("/api/v1/reviews?kind=obrigacao")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["claimed_by"] == "alice"


def test_list_pagination(authenticated_client, make_staging_obrigacao) -> None:
    client, _, _ = authenticated_client(username="alice")
    for i in range(5):
        make_staging_obrigacao(descricao=f"item {i}")

    first = client.get("/api/v1/reviews?kind=obrigacao&page=1&page_size=2").json()
    assert len(first["items"]) == 2
    assert first["total"] == 5

    second = client.get("/api/v1/reviews?kind=obrigacao&page=2&page_size=2").json()
    assert len(second["items"]) == 2
    # No overlap across pages.
    ids_first = {i["id"] for i in first["items"]}
    ids_second = {i["id"] for i in second["items"]}
    assert ids_first.isdisjoint(ids_second)


def test_list_requires_auth(api_client) -> None:
    resp = api_client.get("/api/v1/reviews?kind=obrigacao")
    assert resp.status_code in (401, 403)
