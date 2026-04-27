"""``POST /api/v1/reviews/{kind}/{id}/approve`` — audit-row insert + claim clear."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


_PAYLOAD = {
    "descricao_obrigacao": "adotar providências corretivas em 90 dias",
    "de_fazer": True,
    "prazo": "90 dias",
    "orgao_responsavel": "PREFEITURA MUNICIPAL DE EXEMPLO",
    "tem_multa_cominatoria": True,
    "valor_multa_cominatoria": 1000.0,
    "periodo_multa_cominatoria": "diário",
}


def test_approve_happy_path_inserts_audit_and_clears_claim(
    authenticated_client, make_staging_obrigacao, test_session_factory
) -> None:
    from tools.etl.staging import ObrigacaoStagingORM, ReviewStatus
    from tools.models import ObrigacaoORM

    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao(
        claimed_by="alice",
        claimed_at=datetime.utcnow(),
    )

    resp = client.post(
        f"/api/v1/reviews/obrigacao/{staged['id']}/approve", json=_PAYLOAD
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "approved"
    assert body["reviewer"] == "alice"
    assert body["id"] == staged["id"]

    session = test_session_factory()
    try:
        # Audit row exists, status approved, FK to the final row.
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
        assert audit.Status == ReviewStatus.approved
        assert audit.Revisor == "alice"
        assert audit.DataRevisao is not None
        assert audit.DescricaoObrigacao == _PAYLOAD["descricao_obrigacao"]
        assert audit.Prazo == "90 dias"

        # Final row preserved (LLM original) and claim cleared.
        final = session.get(ObrigacaoORM, staged["id"])
        assert final is not None
        assert final.DescricaoObrigacao == staged["descricao"]  # unchanged
        assert final.ReservadoPor is None
        assert final.DataReserva is None
    finally:
        session.close()


def test_approve_without_claim_returns_403(
    authenticated_client, make_staging_obrigacao, test_session_factory
) -> None:
    from tools.etl.staging import ObrigacaoStagingORM
    from tools.models import ObrigacaoORM

    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao()  # no claim

    resp = client.post(
        f"/api/v1/reviews/obrigacao/{staged['id']}/approve", json=_PAYLOAD
    )
    assert resp.status_code == 403

    # No audit row created; final row still pristine.
    session = test_session_factory()
    try:
        audits = session.execute(select(ObrigacaoStagingORM)).scalars().all()
        assert audits == []
        final = session.get(ObrigacaoORM, staged["id"])
        assert final.ReservadoPor is None
    finally:
        session.close()


def test_approve_claim_by_other_user_returns_403(
    authenticated_client, make_staging_obrigacao, test_session_factory
) -> None:
    from tools.etl.staging import ObrigacaoStagingORM

    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao(claimed_by="bob", claimed_at=datetime.utcnow())
    resp = client.post(
        f"/api/v1/reviews/obrigacao/{staged['id']}/approve", json=_PAYLOAD
    )
    assert resp.status_code == 403

    session = test_session_factory()
    try:
        assert session.execute(select(ObrigacaoStagingORM)).scalars().all() == []
    finally:
        session.close()


def test_approve_when_already_reviewed_returns_409(
    authenticated_client, make_staging_obrigacao
) -> None:
    """A second approve on the same final row must conflict — exactly one
    audit row per final row is the model invariant.
    """
    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao(
        status="approved",
        claimed_by="alice",
        claimed_at=datetime.utcnow(),
        reviewer="alice",
    )

    resp = client.post(
        f"/api/v1/reviews/obrigacao/{staged['id']}/approve", json=_PAYLOAD
    )
    assert resp.status_code == 409


def test_approve_rolls_back_when_clear_claim_fails(
    authenticated_client, make_staging_obrigacao, test_session_factory, mocker
) -> None:
    """Mid-transaction failure (here: clear-claim UPDATE) must roll back
    cleanly so the audit row is not persisted and the claim survives,
    letting the reviewer retry.
    """
    from tools.etl.staging import ObrigacaoStagingORM
    from tools.models import ObrigacaoORM

    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao(claimed_by="alice", claimed_at=datetime.utcnow())

    def _boom(*_args, **_kwargs):
        raise IntegrityError("simulated", None, Exception("boom"))

    mocker.patch("app.review.service._clear_claim", side_effect=_boom)

    resp = client.post(
        f"/api/v1/reviews/obrigacao/{staged['id']}/approve", json=_PAYLOAD
    )
    assert resp.status_code == 500

    session = test_session_factory()
    try:
        # No audit row inserted (rollback dropped the queued INSERT).
        audits = session.execute(select(ObrigacaoStagingORM)).scalars().all()
        assert audits == []
        # Claim survived the failed transaction so the reviewer can retry.
        final = session.get(ObrigacaoORM, staged["id"])
        assert final.ReservadoPor == "alice"
        assert final.DataReserva is not None
    finally:
        session.close()
