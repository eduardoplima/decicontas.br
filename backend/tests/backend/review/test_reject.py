"""``POST /api/v1/reviews/{kind}/{id}/reject`` — notes validation + audit insert."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select


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


def test_reject_happy_path_inserts_audit_and_clears_claim(
    authenticated_client, make_staging_obrigacao, test_session_factory
) -> None:
    from tools.etl.staging import ObrigacaoStagingORM, ReviewStatus
    from tools.models import ObrigacaoORM

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
    assert body["id"] == staged["id"]

    session = test_session_factory()
    try:
        audit = (
            session.execute(
                select(ObrigacaoStagingORM).where(
                    ObrigacaoStagingORM.IdObrigacao == staged["id"]
                )
            )
            .scalars()
            .first()
        )
        assert audit is not None
        assert audit.Status == ReviewStatus.rejected
        assert audit.ObservacoesRevisao == notes
        assert audit.Revisor == "alice"

        final = session.get(ObrigacaoORM, staged["id"])
        assert final.ReservadoPor is None
        assert final.DataReserva is None
    finally:
        session.close()


def test_reject_when_already_reviewed_returns_409(
    authenticated_client, make_staging_obrigacao
) -> None:
    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao(
        status="rejected",
        claimed_by="alice",
        claimed_at=datetime.utcnow(),
        reviewer="alice",
        review_notes="rejeitado anteriormente",
    )
    resp = client.post(
        f"/api/v1/reviews/obrigacao/{staged['id']}/reject",
        json={"review_notes": "tentativa de rejeitar de novo"},
    )
    assert resp.status_code == 409
