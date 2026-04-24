"""``POST /api/v1/reviews/{kind}/{id}/reject`` — notes validation + status flip."""

from __future__ import annotations

from datetime import datetime


def test_reject_requires_notes_at_least_10_chars(
    authenticated_client, make_staging_obrigacao
) -> None:
    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao(claimed_by="alice", claimed_at=datetime.utcnow())
    resp = client.post(
        f"/api/v1/reviews/obrigacao/{staged['id']}/reject",
        json={"review_notes": "short"},
    )
    assert resp.status_code == 422


def test_reject_without_claim_returns_403(
    authenticated_client, make_staging_obrigacao
) -> None:
    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao()  # no claim
    resp = client.post(
        f"/api/v1/reviews/obrigacao/{staged['id']}/reject",
        json={"review_notes": "descricao não condiz com o texto"},
    )
    assert resp.status_code == 403


def test_reject_happy_path_flips_status(
    authenticated_client, make_staging_obrigacao, test_session_factory
) -> None:
    from tools.etl.staging import ObrigacaoStagingORM, ReviewStatus

    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao(claimed_by="alice", claimed_at=datetime.utcnow())
    notes = "descricao inconsistente com o voto do relator"
    resp = client.post(
        f"/api/v1/reviews/obrigacao/{staged['id']}/reject",
        json={"review_notes": notes},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "rejected"
    assert body["reviewer"] == "alice"
    assert body["review_notes"] == notes

    session = test_session_factory()
    try:
        row = session.get(ObrigacaoStagingORM, staged["id"])
        assert row.Status == ReviewStatus.rejected
        assert row.ObservacoesRevisao == notes
    finally:
        session.close()
