"""Review business logic.

Pendente = a final-table row (``Obrigacao`` / ``Recomendacao``) without a
matching ``*Staging`` audit row. Approve/reject INSERTs the audit row keyed
to the final row by FK; claim state lives on the final row.

The atomic claim uses a conditional ``UPDATE`` guarded by the current claim
state, which is MSSQL-compatible (no ``SELECT … FOR UPDATE SKIP LOCKED``):
exactly one concurrent caller's WHERE clause matches, so exactly one
succeeds.
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
    RecomendacaoORM,
    UserORM,
)
from tools.utils import DB_PROCESSOS, SQL_DIR, get_connection


logger = logging.getLogger(__name__)

CLAIM_TTL = timedelta(minutes=15)

Kind = Literal["obrigacao", "recomendacao"]


# ----- helpers -------------------------------------------------------------


def _final_orm(kind: Kind):
    return ObrigacaoORM if kind == "obrigacao" else RecomendacaoORM


def _final_pk(kind: Kind):
    orm = _final_orm(kind)
    return orm.IdObrigacao if kind == "obrigacao" else orm.IdRecomendacao


def _staging_orm(kind: Kind):
    return ObrigacaoStagingORM if kind == "obrigacao" else RecomendacaoStagingORM


def _staging_fk(kind: Kind):
    """Column on the staging audit table that links to the final-table PK."""
    orm = _staging_orm(kind)
    return orm.IdObrigacao if kind == "obrigacao" else orm.IdRecomendacao


def _staging_pk(kind: Kind):
    orm = _staging_orm(kind)
    return orm.IdObrigacaoStaging if kind == "obrigacao" else orm.IdRecomendacaoStaging


def _load_final(session: Session, kind: Kind, id: int):
    row = session.get(_final_orm(kind), id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="review not found"
        )
    return row


def _load_audit(session: Session, kind: Kind, final_id: int):
    """Return the (single) audit row linked to the given final-table row, or None."""
    stmt = select(_staging_orm(kind)).where(_staging_fk(kind) == final_id)
    return session.execute(stmt).scalar_one_or_none()


def _has_active_claim_by(final_row, user: UserORM) -> bool:
    if final_row.ReservadoPor != user.NomeUsuario:
        return False
    if final_row.DataReserva is None:
        return False
    return final_row.DataReserva >= datetime.utcnow() - CLAIM_TTL


def _final_descricao(final_row, kind: Kind) -> str:
    if kind == "obrigacao":
        return final_row.DescricaoObrigacao or ""
    return final_row.DescricaoRecomendacao or ""


def _final_id(final_row, kind: Kind) -> int:
    return final_row.IdObrigacao if kind == "obrigacao" else final_row.IdRecomendacao


def _final_fields(final_row, kind: Kind) -> dict[str, Any]:
    if kind == "obrigacao":
        return {
            "descricao_obrigacao": final_row.DescricaoObrigacao,
            "de_fazer": final_row.DeFazer,
            "prazo": final_row.Prazo,
            "data_cumprimento": final_row.DataCumprimento,
            "orgao_responsavel": final_row.OrgaoResponsavel,
            "id_orgao_responsavel": final_row.IdOrgaoResponsavel,
            "tem_multa_cominatoria": final_row.TemMultaCominatoria,
            "nome_responsavel_multa_cominatoria": final_row.NomeResponsavelMultaCominatoria,
            "documento_responsavel_multa_cominatoria": final_row.DocumentoResponsavelMultaCominatoria,
            "id_pessoa_multa_cominatoria": final_row.IdPessoaMultaCominatoria,
            "valor_multa_cominatoria": final_row.ValorMultaCominatoria,
            "periodo_multa_cominatoria": final_row.PeriodoMultaCominatoria,
            "e_multa_cominatoria_solidaria": final_row.EMultaCominatoriaSolidaria,
            "solidarios_multa_cominatoria": final_row.SolidariosMultaCominatoria,
        }
    return {
        "descricao_recomendacao": final_row.DescricaoRecomendacao,
        "prazo_cumprimento_recomendacao": final_row.PrazoCumprimentoRecomendacao,
        "data_cumprimento_recomendacao": final_row.DataCumprimentoRecomendacao,
        "nome_responsavel": final_row.NomeResponsavel,
        "id_pessoa_responsavel": final_row.IdPessoaResponsavel,
        "orgao_responsavel": final_row.OrgaoResponsavel,
        "id_orgao_responsavel": final_row.IdOrgaoResponsavel,
        "cancelado": final_row.Cancelado,
    }


def _audit_fields(audit_row, kind: Kind) -> dict[str, Any]:
    """Reviewer-edited values stored on the audit row."""
    if kind == "obrigacao":
        return {
            "descricao_obrigacao": audit_row.DescricaoObrigacao,
            "de_fazer": audit_row.DeFazer,
            "prazo": audit_row.Prazo,
            "data_cumprimento": audit_row.DataCumprimento,
            "orgao_responsavel": audit_row.OrgaoResponsavel,
            "id_orgao_responsavel": audit_row.IdOrgaoResponsavel,
            "tem_multa_cominatoria": audit_row.TemMultaCominatoria,
            "nome_responsavel_multa_cominatoria": audit_row.NomeResponsavelMultaCominatoria,
            "documento_responsavel_multa_cominatoria": audit_row.DocumentoResponsavelMultaCominatoria,
            "id_pessoa_multa_cominatoria": audit_row.IdPessoaMultaCominatoria,
            "valor_multa_cominatoria": audit_row.ValorMultaCominatoria,
            "periodo_multa_cominatoria": audit_row.PeriodoMultaCominatoria,
            "e_multa_cominatoria_solidaria": audit_row.EMultaCominatoriaSolidaria,
            "solidarios_multa_cominatoria": audit_row.SolidariosMultaCominatoria,
        }
    return {
        "descricao_recomendacao": audit_row.DescricaoRecomendacao,
        "prazo_cumprimento_recomendacao": audit_row.PrazoCumprimentoRecomendacao,
        "data_cumprimento_recomendacao": audit_row.DataCumprimentoRecomendacao,
        "nome_responsavel": audit_row.NomeResponsavel,
        "id_pessoa_responsavel": audit_row.IdPessoaResponsavel,
        "orgao_responsavel": audit_row.OrgaoResponsavel,
        "id_orgao_responsavel": audit_row.IdOrgaoResponsavel,
        "cancelado": audit_row.Cancelado,
    }


def _to_list_item(final_row, audit_row, kind: Kind) -> schemas.ReviewListItem:
    if audit_row is None:
        status_value = ReviewStatus.pending.value
        reviewer = None
        reviewed_at = None
    else:
        status_value = (
            audit_row.Status.value
            if isinstance(audit_row.Status, ReviewStatus)
            else str(audit_row.Status)
        )
        reviewer = audit_row.Revisor
        reviewed_at = audit_row.DataRevisao
    return schemas.ReviewListItem(
        id=_final_id(final_row, kind),
        kind=kind,
        status=status_value,
        descricao=_final_descricao(final_row, kind),
        id_processo=final_row.IdProcesso,
        id_composicao_pauta=final_row.IdComposicaoPauta,
        id_voto_pauta=final_row.IdVotoPauta,
        claimed_by=final_row.ReservadoPor,
        claimed_at=final_row.DataReserva,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
    )


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
    session: Session, final_row, audit_row, kind: Kind
) -> schemas.ReviewDetail:
    """Detail without ``texto_acordao`` — fast, no MSSQL hit on the heavy text
    column. The frontend fetches the text separately via
    ``GET /reviews/{kind}/{id}/texto-acordao``.
    """
    if audit_row is None:
        staged = _final_fields(final_row, kind)
        original_payload = None
        status_value = ReviewStatus.pending.value
        reviewer = None
        reviewed_at = None
        review_notes = None
    else:
        staged = _audit_fields(audit_row, kind)
        original_payload = _final_fields(final_row, kind)
        status_value = (
            audit_row.Status.value
            if isinstance(audit_row.Status, ReviewStatus)
            else str(audit_row.Status)
        )
        reviewer = audit_row.Revisor
        reviewed_at = audit_row.DataRevisao
        review_notes = audit_row.ObservacoesRevisao

    return schemas.ReviewDetail(
        id=_final_id(final_row, kind),
        kind=kind,
        status=status_value,
        id_processo=final_row.IdProcesso,
        id_composicao_pauta=final_row.IdComposicaoPauta,
        id_voto_pauta=final_row.IdVotoPauta,
        staged=staged,
        original_payload=original_payload,
        claimed_by=final_row.ReservadoPor,
        claimed_at=final_row.DataReserva,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        review_notes=review_notes,
    )


def get_review_texto(
    session: Session, *, kind: Kind, id: int, current_user: UserORM
) -> schemas.ReviewTexto:
    """Fetch ``texto_acordao`` and the matched span for a single review item."""
    final_row = _load_final(session, kind, id)
    audit_row = _load_audit(session, kind, id)

    if audit_row is None:
        descricao = _final_descricao(final_row, kind)
    else:
        edited = _audit_fields(audit_row, kind)
        descricao = (
            edited.get(
                "descricao_obrigacao" if kind == "obrigacao" else "descricao_recomendacao"
            )
            or _final_descricao(final_row, kind)
        )

    texto_acordao = _load_texto_acordao(
        final_row.IdProcesso,
        final_row.IdComposicaoPauta,
        final_row.IdVotoPauta,
    )
    span, match_status = find_span_with_status(descricao or "", texto_acordao or "")
    return schemas.ReviewTexto(
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
    final = _final_orm(kind)
    staging = _staging_orm(kind)
    fk = _staging_fk(kind)
    pk = _final_pk(kind)
    cutoff = datetime.utcnow() - CLAIM_TTL
    me = current_user.NomeUsuario

    if status_filter == ReviewStatus.pending:
        # LEFT JOIN final ↔ staging; pending = staging row missing.
        # Plus claim filter: exclude rows held by another reviewer (within TTL).
        stmt = (
            select(final, staging)
            .outerjoin(staging, fk == pk)
            .where(_staging_pk(kind).is_(None))
            .where(
                or_(
                    final.ReservadoPor.is_(None),
                    final.ReservadoPor == me,
                    final.DataReserva < cutoff,
                )
            )
        )
    else:
        # approved / rejected → INNER JOIN with status filter.
        stmt = (
            select(final, staging)
            .join(staging, fk == pk)
            .where(staging.Status == status_filter)
        )

    total = session.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()

    rows = (
        session.execute(stmt.order_by(pk.asc()).offset((page - 1) * page_size).limit(page_size))
        .all()
    )

    return schemas.ReviewListPage(
        items=[_to_list_item(final_row, audit_row, kind) for final_row, audit_row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


def get_review(
    session: Session, *, kind: Kind, id: int, current_user: UserORM
) -> schemas.ReviewDetail:
    final_row = _load_final(session, kind, id)
    audit_row = _load_audit(session, kind, id)
    return _to_detail(session, final_row, audit_row, kind)


# ----- claim / release ----------------------------------------------------


def claim(
    session: Session, *, kind: Kind, id: int, current_user: UserORM
) -> schemas.ClaimResponse:
    final = _final_orm(kind)
    pk = _final_pk(kind)
    now = datetime.utcnow()
    cutoff = now - CLAIM_TTL
    me = current_user.NomeUsuario

    # Refuse if already reviewed (audit row exists).
    audit_row = _load_audit(session, kind, id)
    if audit_row is not None:
        status_value = (
            audit_row.Status.value
            if isinstance(audit_row.Status, ReviewStatus)
            else str(audit_row.Status)
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"review is {status_value}, not pending",
        )

    stmt = (
        update(final)
        .where(
            pk == id,
            or_(
                final.ReservadoPor.is_(None),
                final.ReservadoPor == me,
                final.DataReserva < cutoff,
            ),
        )
        .values(ReservadoPor=me, DataReserva=now)
        .execution_options(synchronize_session=False)
    )
    result = session.execute(stmt)
    session.commit()

    if result.rowcount == 1:
        row = session.get(final, id)
        return schemas.ClaimResponse(
            claimed_by=row.ReservadoPor,
            claimed_at=row.DataReserva,
            expires_at=row.DataReserva + CLAIM_TTL,
        )

    # rowcount == 0 → 404 vs 409.
    row = session.get(final, id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="review not found"
        )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"claimed by {row.ReservadoPor}",
    )


def release(session: Session, *, kind: Kind, id: int, current_user: UserORM) -> None:
    """Idempotent: release the claim if it's held by the caller."""
    final = _final_orm(kind)
    pk = _final_pk(kind)
    me = current_user.NomeUsuario

    stmt = (
        update(final)
        .where(pk == id, final.ReservadoPor == me)
        .values(ReservadoPor=None, DataReserva=None)
        .execution_options(synchronize_session=False)
    )
    session.execute(stmt)
    session.commit()


# ----- approve / reject ---------------------------------------------------


def _require_active_claim(final_row, user: UserORM) -> None:
    if not _has_active_claim_by(final_row, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="no active claim by caller",
        )


def _refuse_if_already_reviewed(audit_row) -> None:
    if audit_row is None:
        return
    status_value = (
        audit_row.Status.value
        if isinstance(audit_row.Status, ReviewStatus)
        else str(audit_row.Status)
    )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"review is {status_value}",
    )


def _clear_claim(session: Session, kind: Kind, id: int) -> None:
    stmt = (
        update(_final_orm(kind))
        .where(_final_pk(kind) == id)
        .values(ReservadoPor=None, DataReserva=None)
        .execution_options(synchronize_session=False)
    )
    session.execute(stmt)


def approve_obrigacao(
    session: Session,
    *,
    id: int,
    payload: schemas.ObrigacaoReview,
    current_user: UserORM,
) -> schemas.ReviewDetail:
    final_row = _load_final(session, "obrigacao", id)
    _require_active_claim(final_row, current_user)
    _refuse_if_already_reviewed(_load_audit(session, "obrigacao", id))

    try:
        now = datetime.utcnow()
        audit = ObrigacaoStagingORM(
            IdObrigacao=final_row.IdObrigacao,
            IdProcesso=final_row.IdProcesso,
            IdComposicaoPauta=final_row.IdComposicaoPauta,
            IdVotoPauta=final_row.IdVotoPauta,
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
            Status=ReviewStatus.approved,
            Revisor=current_user.NomeUsuario,
            DataRevisao=now,
        )
        session.add(audit)
        _clear_claim(session, "obrigacao", id)
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

    session.refresh(final_row)
    return _to_detail(session, final_row, audit, "obrigacao")


def approve_recomendacao(
    session: Session,
    *,
    id: int,
    payload: schemas.RecomendacaoReview,
    current_user: UserORM,
) -> schemas.ReviewDetail:
    final_row = _load_final(session, "recomendacao", id)
    _require_active_claim(final_row, current_user)
    _refuse_if_already_reviewed(_load_audit(session, "recomendacao", id))

    try:
        now = datetime.utcnow()
        audit = RecomendacaoStagingORM(
            IdRecomendacao=final_row.IdRecomendacao,
            IdProcesso=final_row.IdProcesso,
            IdComposicaoPauta=final_row.IdComposicaoPauta,
            IdVotoPauta=final_row.IdVotoPauta,
            DescricaoRecomendacao=payload.descricao_recomendacao,
            PrazoCumprimentoRecomendacao=payload.prazo_cumprimento_recomendacao,
            DataCumprimentoRecomendacao=payload.data_cumprimento_recomendacao,
            NomeResponsavel=payload.nome_responsavel,
            IdPessoaResponsavel=payload.id_pessoa_responsavel,
            OrgaoResponsavel=payload.orgao_responsavel,
            IdOrgaoResponsavel=payload.id_orgao_responsavel,
            Cancelado=payload.cancelado,
            Status=ReviewStatus.approved,
            Revisor=current_user.NomeUsuario,
            DataRevisao=now,
        )
        session.add(audit)
        _clear_claim(session, "recomendacao", id)
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

    session.refresh(final_row)
    return _to_detail(session, final_row, audit, "recomendacao")


def reject(
    session: Session,
    *,
    kind: Kind,
    id: int,
    notes: str,
    current_user: UserORM,
) -> schemas.ReviewDetail:
    final_row = _load_final(session, kind, id)
    _require_active_claim(final_row, current_user)
    _refuse_if_already_reviewed(_load_audit(session, kind, id))

    try:
        now = datetime.utcnow()
        if kind == "obrigacao":
            audit = ObrigacaoStagingORM(
                IdObrigacao=final_row.IdObrigacao,
                IdProcesso=final_row.IdProcesso,
                IdComposicaoPauta=final_row.IdComposicaoPauta,
                IdVotoPauta=final_row.IdVotoPauta,
                DescricaoObrigacao=final_row.DescricaoObrigacao,
                Status=ReviewStatus.rejected,
                Revisor=current_user.NomeUsuario,
                DataRevisao=now,
                ObservacoesRevisao=notes,
            )
        else:
            audit = RecomendacaoStagingORM(
                IdRecomendacao=final_row.IdRecomendacao,
                IdProcesso=final_row.IdProcesso,
                IdComposicaoPauta=final_row.IdComposicaoPauta,
                IdVotoPauta=final_row.IdVotoPauta,
                DescricaoRecomendacao=final_row.DescricaoRecomendacao,
                Status=ReviewStatus.rejected,
                Revisor=current_user.NomeUsuario,
                DataRevisao=now,
                ObservacoesRevisao=notes,
            )
        session.add(audit)
        _clear_claim(session, kind, id)
        session.commit()
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        logger.exception("reject transaction failed for %s %s", kind, id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="reject transaction failed",
        ) from exc

    session.refresh(final_row)
    return _to_detail(session, final_row, audit, kind)
