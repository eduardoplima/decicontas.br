"""``POST /api/v1/reviews/{kind}/{id}/approve`` — transaction semantics."""

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


def _seed_ner(session_factory, *, id_processo, id_composicao, id_voto) -> int:
    """Insert a minimal NERDecisao + NERObrigacao so ProcessedObrigacao has a valid FK."""
    from tools.models import NERDecisaoORM, NERObrigacaoORM

    s = session_factory()
    try:
        decisao = NERDecisaoORM(
            IdProcesso=id_processo,
            IdComposicaoPauta=id_composicao,
            IdVotoPauta=id_voto,
            RawJson="{}",
        )
        s.add(decisao)
        s.flush()
        ner = NERObrigacaoORM(
            IdNerDecisao=decisao.IdNerDecisao,
            Ordem=0,
            DescricaoObrigacao="ner source",
        )
        s.add(ner)
        s.commit()
        return ner.IdNerObrigacao
    finally:
        s.close()


def test_approve_happy_path_writes_final_and_processed(
    authenticated_client, make_staging_obrigacao, test_session_factory
) -> None:
    from tools.etl.staging import ObrigacaoStagingORM, ReviewStatus
    from tools.models import ObrigacaoORM, ProcessedObrigacaoORM

    client, _, _ = authenticated_client(username="alice")
    id_ner = _seed_ner(
        test_session_factory,
        id_processo=541094,
        id_composicao=7001,
        id_voto=9001,
    )
    staged = make_staging_obrigacao(
        id_ner_obrigacao=id_ner,
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

    session = test_session_factory()
    try:
        staging_row = session.get(ObrigacaoStagingORM, staged["id"])
        assert staging_row.Status == ReviewStatus.approved
        assert staging_row.Revisor == "alice"
        assert staging_row.DataRevisao is not None

        finals = session.execute(select(ObrigacaoORM)).scalars().all()
        assert len(finals) == 1
        assert finals[0].DescricaoObrigacao == _PAYLOAD["descricao_obrigacao"]
        assert finals[0].Prazo == "90 dias"
        assert finals[0].IdProcesso == 541094

        processed = session.execute(select(ProcessedObrigacaoORM)).scalars().all()
        assert len(processed) == 1
        assert processed[0].IdObrigacao == finals[0].IdObrigacao
        assert processed[0].IdNerObrigacao == id_ner
    finally:
        session.close()


def test_approve_without_claim_returns_403(
    authenticated_client, make_staging_obrigacao, test_session_factory
) -> None:
    from tools.etl.staging import ObrigacaoStagingORM, ReviewStatus
    from tools.models import ObrigacaoORM

    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao()  # no claim

    resp = client.post(
        f"/api/v1/reviews/obrigacao/{staged['id']}/approve", json=_PAYLOAD
    )
    assert resp.status_code == 403

    # Staging must not have flipped.
    session = test_session_factory()
    try:
        row = session.get(ObrigacaoStagingORM, staged["id"])
        assert row.Status == ReviewStatus.pending
        assert session.execute(select(ObrigacaoORM)).scalars().all() == []
    finally:
        session.close()


def test_approve_claim_by_other_user_returns_403(
    authenticated_client, make_staging_obrigacao
) -> None:
    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao(claimed_by="bob", claimed_at=datetime.utcnow())
    resp = client.post(
        f"/api/v1/reviews/obrigacao/{staged['id']}/approve", json=_PAYLOAD
    )
    assert resp.status_code == 403


def test_approve_rolls_back_when_final_insert_fails(
    authenticated_client, make_staging_obrigacao, test_session_factory, mocker
) -> None:
    """Mid-transaction failure during the final-table insert must roll back
    staging (still pending) and leave no Processed row."""
    from tools.etl.staging import ObrigacaoStagingORM, ReviewStatus
    from tools.models import ObrigacaoORM, ProcessedObrigacaoORM

    client, _, _ = authenticated_client(username="alice")
    id_ner = _seed_ner(
        test_session_factory,
        id_processo=541094,
        id_composicao=7001,
        id_voto=9001,
    )
    staged = make_staging_obrigacao(
        id_ner_obrigacao=id_ner,
        claimed_by="alice",
        claimed_at=datetime.utcnow(),
    )

    def _boom(*args, **kwargs):
        raise IntegrityError("simulated", None, Exception("boom"))

    mocker.patch("app.review.service.ObrigacaoORM", side_effect=_boom)

    resp = client.post(
        f"/api/v1/reviews/obrigacao/{staged['id']}/approve", json=_PAYLOAD
    )
    assert resp.status_code == 500

    session = test_session_factory()
    try:
        row = session.get(ObrigacaoStagingORM, staged["id"])
        assert row.Status == ReviewStatus.pending
        assert row.Revisor is None
        assert row.DataRevisao is None
        assert session.execute(select(ObrigacaoORM)).scalars().all() == []
        assert session.execute(select(ProcessedObrigacaoORM)).scalars().all() == []
    finally:
        session.close()
