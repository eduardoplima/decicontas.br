"""Review business logic.

The approval transaction (``approve_obrigacao`` / ``approve_recomendacao``) is
the only writer to ``ObrigacaoORM`` / ``RecomendacaoORM``. All other writes
flow through the staging tables.

The atomic claim uses a conditional ``UPDATE`` guarded by the current claim
state, which is MSSQL-compatible (no ``SELECT … FOR UPDATE SKIP LOCKED``):
exactly one concurrent caller's WHERE clause matches, so exactly one succeeds.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, text, update
from sqlalchemy.orm import Session

from app.review import schemas
from tools.etl.staging import (
    ObrigacaoStagingORM,
    RecomendacaoStagingORM,
    ReviewStatus,
)
from tools.etl.text_alignment import find_span_with_status
from tools.models import (
    ObrigacaoORM,
    ProcessedObrigacaoORM,
    ProcessedRecomendacaoORM,
    RecomendacaoORM,
    UserORM,
)
from tools.utils import DB_PROCESSOS, SQL_DIR, get_connection


logger = logging.getLogger(__name__)

CLAIM_TTL = timedelta(minutes=15)

Kind = Literal["obrigacao", "recomendacao"]


# ----- helpers -------------------------------------------------------------


def _staging_orm(kind: Kind):
    return ObrigacaoStagingORM if kind == "obrigacao" else RecomendacaoStagingORM


def _staging_pk(kind: Kind):
    orm = _staging_orm(kind)
    return orm.IdObrigacaoStaging if kind == "obrigacao" else orm.IdRecomendacaoStaging


def _staging_descricao(kind: Kind):
    orm = _staging_orm(kind)
    return orm.DescricaoObrigacao if kind == "obrigacao" else orm.DescricaoRecomendacao


def _load_staging(session: Session, kind: Kind, id: int):
    row = session.get(_staging_orm(kind), id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="review not found"
        )
    return row


def _has_active_claim_by(row, user: UserORM) -> bool:
    if row.ReservadoPor != user.NomeUsuario:
        return False
    if row.DataReserva is None:
        return False
    return row.DataReserva >= datetime.utcnow() - CLAIM_TTL


def _to_list_item(row, kind: Kind) -> schemas.ReviewListItem:
    pk = row.IdObrigacaoStaging if kind == "obrigacao" else row.IdRecomendacaoStaging
    descricao = (
        row.DescricaoObrigacao
        if kind == "obrigacao"
        else (row.DescricaoRecomendacao or "")
    )
    status_value = (
        row.Status.value if isinstance(row.Status, ReviewStatus) else str(row.Status)
    )
    return schemas.ReviewListItem(
        id=pk,
        kind=kind,
        status=status_value,
        descricao=descricao,
        id_processo=row.IdProcesso,
        id_composicao_pauta=row.IdComposicaoPauta,
        id_voto_pauta=row.IdVotoPauta,
        claimed_by=row.ReservadoPor,
        claimed_at=row.DataReserva,
        reviewer=row.Revisor,
        reviewed_at=row.DataRevisao,
    )


def _staged_fields(row, kind: Kind) -> dict[str, Any]:
    if kind == "obrigacao":
        return {
            "descricao_obrigacao": row.DescricaoObrigacao,
            "de_fazer": row.DeFazer,
            "prazo": row.Prazo,
            "data_cumprimento": row.DataCumprimento,
            "orgao_responsavel": row.OrgaoResponsavel,
            "id_orgao_responsavel": row.IdOrgaoResponsavel,
            "tem_multa_cominatoria": row.TemMultaCominatoria,
            "nome_responsavel_multa_cominatoria": row.NomeResponsavelMultaCominatoria,
            "documento_responsavel_multa_cominatoria": row.DocumentoResponsavelMultaCominatoria,
            "id_pessoa_multa_cominatoria": row.IdPessoaMultaCominatoria,
            "valor_multa_cominatoria": row.ValorMultaCominatoria,
            "periodo_multa_cominatoria": row.PeriodoMultaCominatoria,
            "e_multa_cominatoria_solidaria": row.EMultaCominatoriaSolidaria,
            "solidarios_multa_cominatoria": row.SolidariosMultaCominatoria,
        }
    return {
        "descricao_recomendacao": row.DescricaoRecomendacao,
        "prazo_cumprimento_recomendacao": row.PrazoCumprimentoRecomendacao,
        "data_cumprimento_recomendacao": row.DataCumprimentoRecomendacao,
        "nome_responsavel": row.NomeResponsavel,
        "id_pessoa_responsavel": row.IdPessoaResponsavel,
        "orgao_responsavel": row.OrgaoResponsavel,
        "id_orgao_responsavel": row.IdOrgaoResponsavel,
        "cancelado": row.Cancelado,
    }


def _load_texto_acordao(
    id_processo: int, id_composicao: int, id_voto: int
) -> str | None:
    """Read ``texto_acordao`` via ``sql/decisions_full_text.sql``. Returns None
    if the query can't run (e.g. in tests without a real MSSQL backend) so the
    detail endpoint degrades gracefully to ``span_match_status='not_found'``.
    """
    try:
        with open(os.path.join(SQL_DIR, "decisions_full_text.sql")) as f:
            sql = f.read()
        sql = sql.format(
            id_processo=id_processo,
            id_composicao_pauta=id_composicao,
            id_voto_pauta=id_voto,
        )
        with get_connection(DB_PROCESSOS).connect() as conn:
            row = conn.execute(text(sql)).first()
        if row is None:
            return None
        return getattr(row, "texto_acordao", None)
    except Exception:
        logger.exception(
            "failed to load texto_acordao for (%s, %s, %s)",
            id_processo,
            id_composicao,
            id_voto,
        )
        return None


def _to_detail(
    session: Session, row, kind: Kind, *, texto_acordao: str | None = None
) -> schemas.ReviewDetail:
    descricao = (
        row.DescricaoObrigacao
        if kind == "obrigacao"
        else (row.DescricaoRecomendacao or "")
    )
    if texto_acordao is None:
        texto_acordao = _load_texto_acordao(
            row.IdProcesso, row.IdComposicaoPauta, row.IdVotoPauta
        )
    span, match_status = find_span_with_status(descricao, texto_acordao or "")

    pk = row.IdObrigacaoStaging if kind == "obrigacao" else row.IdRecomendacaoStaging
    status_value = (
        row.Status.value if isinstance(row.Status, ReviewStatus) else str(row.Status)
    )

    return schemas.ReviewDetail(
        id=pk,
        kind=kind,
        status=status_value,
        id_processo=row.IdProcesso,
        id_composicao_pauta=row.IdComposicaoPauta,
        id_voto_pauta=row.IdVotoPauta,
        staged=_staged_fields(row, kind),
        original_payload=row.PayloadOriginal,
        claimed_by=row.ReservadoPor,
        claimed_at=row.DataReserva,
        reviewer=row.Revisor,
        reviewed_at=row.DataRevisao,
        review_notes=row.ObservacoesRevisao,
        texto_acordao=texto_acordao,
        matched_span=span,
        span_match_status=match_status,
    )


# ----- list / get ----------------------------------------------------------


def list_reviews(
    session: Session,
    *,
    kind: Kind,
    status_filter: ReviewStatus,
    page: int,
    page_size: int,
    current_user: UserORM,
) -> schemas.ReviewListPage:
    orm = _staging_orm(kind)
    cutoff = datetime.utcnow() - CLAIM_TTL
    me = current_user.NomeUsuario

    # Exclude rows with an active claim by someone else.
    base = select(orm).where(
        orm.Status == status_filter,
        or_(
            orm.ReservadoPor.is_(None),
            orm.ReservadoPor == me,
            orm.DataReserva < cutoff,
        ),
    )

    total = session.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()

    pk = _staging_pk(kind)
    stmt = base.order_by(pk.asc()).offset((page - 1) * page_size).limit(page_size)
    rows = session.execute(stmt).scalars().all()

    return schemas.ReviewListPage(
        items=[_to_list_item(r, kind) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


def get_review(
    session: Session, *, kind: Kind, id: int, current_user: UserORM
) -> schemas.ReviewDetail:
    row = _load_staging(session, kind, id)
    return _to_detail(session, row, kind)


# ----- claim / release ----------------------------------------------------


def claim(
    session: Session, *, kind: Kind, id: int, current_user: UserORM
) -> schemas.ClaimResponse:
    orm = _staging_orm(kind)
    pk = _staging_pk(kind)
    now = datetime.utcnow()
    cutoff = now - CLAIM_TTL
    me = current_user.NomeUsuario

    stmt = (
        update(orm)
        .where(
            pk == id,
            orm.Status == ReviewStatus.pending,
            or_(
                orm.ReservadoPor.is_(None),
                orm.ReservadoPor == me,
                orm.DataReserva < cutoff,
            ),
        )
        .values(ReservadoPor=me, DataReserva=now)
        .execution_options(synchronize_session=False)
    )
    result = session.execute(stmt)
    session.commit()

    if result.rowcount == 1:
        row = session.get(orm, id)
        return schemas.ClaimResponse(
            claimed_by=row.ReservadoPor,
            claimed_at=row.DataReserva,
            expires_at=row.DataReserva + CLAIM_TTL,
        )

    # rowcount == 0 — distinguish 404 vs 409.
    row = session.get(orm, id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="review not found"
        )
    status_value = (
        row.Status.value if isinstance(row.Status, ReviewStatus) else str(row.Status)
    )
    if row.Status != ReviewStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"review is {status_value}, not pending",
        )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"claimed by {row.ReservadoPor}",
    )


def release(session: Session, *, kind: Kind, id: int, current_user: UserORM) -> None:
    """Idempotent: release the claim if it's held by the caller."""
    orm = _staging_orm(kind)
    pk = _staging_pk(kind)
    me = current_user.NomeUsuario

    stmt = (
        update(orm)
        .where(pk == id, orm.ReservadoPor == me)
        .values(ReservadoPor=None, DataReserva=None)
        .execution_options(synchronize_session=False)
    )
    session.execute(stmt)
    session.commit()


# ----- approve / reject ---------------------------------------------------


def _require_active_claim(row, user: UserORM) -> None:
    if not _has_active_claim_by(row, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="no active claim by caller",
        )


def approve_obrigacao(
    session: Session,
    *,
    id: int,
    payload: schemas.ObrigacaoReview,
    current_user: UserORM,
) -> schemas.ReviewDetail:
    row = _load_staging(session, "obrigacao", id)
    if row.Status != ReviewStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"review is {row.Status.value}",
        )
    _require_active_claim(row, current_user)

    try:
        final = ObrigacaoORM(
            IdProcesso=row.IdProcesso,
            IdComposicaoPauta=row.IdComposicaoPauta,
            IdVotoPauta=row.IdVotoPauta,
            DescricaoObrigacao=payload.descricao_obrigacao,
            DeFazer=payload.de_fazer,
            Prazo=payload.prazo,
            DataCumprimento=payload.data_cumprimento,
            OrgaoResponsavel=payload.orgao_responsavel,
            IdOrgaoResponsavel=payload.id_orgao_responsavel,
            TemMultaCominatoria=payload.tem_multa_cominatoria,
            NomeResponsavelMultaCominatoria=payload.nome_responsavel_multa_cominatoria,
            DocumentoResponsavelMultaCominatoria=payload.documento_responsavel_multa_cominatoria,
            IdPessoaMultaCominatoria=payload.id_pessoa_multa_cominatoria,
            ValorMultaCominatoria=payload.valor_multa_cominatoria,
            PeriodoMultaCominatoria=payload.periodo_multa_cominatoria,
            EMultaCominatoriaSolidaria=payload.e_multa_cominatoria_solidaria,
            SolidariosMultaCominatoria=payload.solidarios_multa_cominatoria,
        )
        session.add(final)
        session.flush()  # assign IdObrigacao

        now = datetime.utcnow()
        row.Status = ReviewStatus.approved
        row.Revisor = current_user.NomeUsuario
        row.DataRevisao = now

        if row.IdNerObrigacao is not None:
            session.add(
                ProcessedObrigacaoORM(
                    IdNerObrigacao=row.IdNerObrigacao,
                    IdObrigacao=final.IdObrigacao,
                    DataProcessamento=now,
                )
            )
        else:
            logger.warning(
                "staging row %s lacks IdNerObrigacao — skipping Processed insert", id
            )

        session.commit()
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        logger.exception("approval transaction failed for obrigacao %s", id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="approval transaction failed",
        ) from exc

    return _to_detail(session, row, "obrigacao")


def approve_recomendacao(
    session: Session,
    *,
    id: int,
    payload: schemas.RecomendacaoReview,
    current_user: UserORM,
) -> schemas.ReviewDetail:
    row = _load_staging(session, "recomendacao", id)
    if row.Status != ReviewStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"review is {row.Status.value}",
        )
    _require_active_claim(row, current_user)

    try:
        final = RecomendacaoORM(
            IdProcesso=row.IdProcesso,
            IdComposicaoPauta=row.IdComposicaoPauta,
            IdVotoPauta=row.IdVotoPauta,
            DescricaoRecomendacao=payload.descricao_recomendacao,
            PrazoCumprimentoRecomendacao=payload.prazo_cumprimento_recomendacao,
            DataCumprimentoRecomendacao=payload.data_cumprimento_recomendacao,
            NomeResponsavel=payload.nome_responsavel,
            IdPessoaResponsavel=payload.id_pessoa_responsavel,
            OrgaoResponsavel=payload.orgao_responsavel,
            IdOrgaoResponsavel=payload.id_orgao_responsavel,
            Cancelado=payload.cancelado,
        )
        session.add(final)
        session.flush()

        now = datetime.utcnow()
        row.Status = ReviewStatus.approved
        row.Revisor = current_user.NomeUsuario
        row.DataRevisao = now

        if row.IdNerRecomendacao is not None:
            session.add(
                ProcessedRecomendacaoORM(
                    IdNerRecomendacao=row.IdNerRecomendacao,
                    IdRecomendacao=final.IdRecomendacao,
                    DataProcessamento=now,
                )
            )
        else:
            logger.warning(
                "staging row %s lacks IdNerRecomendacao — skipping Processed insert",
                id,
            )

        session.commit()
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        logger.exception("approval transaction failed for recomendacao %s", id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="approval transaction failed",
        ) from exc

    return _to_detail(session, row, "recomendacao")


def reject(
    session: Session,
    *,
    kind: Kind,
    id: int,
    notes: str,
    current_user: UserORM,
) -> schemas.ReviewDetail:
    row = _load_staging(session, kind, id)
    if row.Status != ReviewStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"review is {row.Status.value}",
        )
    _require_active_claim(row, current_user)

    now = datetime.utcnow()
    row.Status = ReviewStatus.rejected
    row.Revisor = current_user.NomeUsuario
    row.DataRevisao = now
    row.ObservacoesRevisao = notes
    session.commit()
    return _to_detail(session, row, kind)
