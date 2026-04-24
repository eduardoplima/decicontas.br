"""Stage-2 extraction orchestration that writes to the review staging tables.

Ports the logic previously invoked from ``notebooks/etl.ipynb`` via
``tools.utils.run_obrigacao_pipeline`` / ``run_recomendacao_pipeline``. Unlike
those helpers, this module writes to ``ObrigacaoStaging`` / ``RecomendacaoStaging``
(status ``pending``) — the final tables are written only by the approval
transaction in ``backend/app/review/service.py``.

Factory-only: no LLM client or DB engine is constructed at import time.
Extractors and the staging ``Session`` are injected by the caller (ARQ worker
in production, mocks in tests).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from tools.etl.staging import (
    ObrigacaoStagingORM,
    RecomendacaoStagingORM,
    ReviewStatus,
)
from tools.models import ProcessedObrigacaoORM, ProcessedRecomendacaoORM
from tools.schema import Obrigacao, Recomendacao
from tools.utils import (
    DB_DECISOES,
    SQL_DIR,
    aggregate_responsaveis,
    extract_obrigacao,
    extract_recomendacao,
    get_connection,
    get_id_pessoa_multa_cominatoria,
    safe_int,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtractionFilters:
    """Scope of a single extraction run. All fields optional; empty = everything pending.

    ``overwrite`` forces re-extraction even if a staging row already exists with
    status ``pending`` or ``approved`` (rejected rows are always re-extractable).
    """

    start_date: date | None = None
    end_date: date | None = None
    process_numbers: Sequence[str] | None = None
    overwrite: bool = False


@dataclass
class ExtractionReport:
    scanned: int = 0
    enqueued: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def _load_driver_sql(sql_filename: str) -> str:
    with open(os.path.join(SQL_DIR, sql_filename)) as f:
        return f.read()


def _apply_filters(df: pd.DataFrame, filters: ExtractionFilters) -> pd.DataFrame:
    if df.empty:
        return df
    if filters.start_date is not None and "data_sessao" in df.columns:
        df = df[pd.to_datetime(df["data_sessao"]) >= pd.Timestamp(filters.start_date)]
    if filters.end_date is not None and "data_sessao" in df.columns:
        df = df[pd.to_datetime(df["data_sessao"]) <= pd.Timestamp(filters.end_date)]
    if filters.process_numbers and "processo" in df.columns:
        df = df[df["processo"].isin(list(filters.process_numbers))]
    return df


def _fetch_driver_rows(sql_filename: str, filters: ExtractionFilters) -> Iterable[dict]:
    conn = get_connection(DB_DECISOES)
    df = pd.read_sql(_load_driver_sql(sql_filename), conn)
    df = _apply_filters(df, filters)
    if df.empty:
        return []
    df = aggregate_responsaveis(df)
    return (row.to_dict() for _, row in df.iterrows())


def _as_row_dict(row: Mapping[str, Any] | Any) -> dict:
    if isinstance(row, dict):
        return row
    if hasattr(row, "to_dict"):
        return row.to_dict()
    return dict(row)


def _identity_triple(
    row: Mapping[str, Any],
) -> tuple[int | None, int | None, int | None]:
    return (
        safe_int(row.get("id_processo")),
        safe_int(row.get("id_composicao_pauta")),
        safe_int(row.get("id_voto_pauta")),
    )


# ---- Obrigação -----------------------------------------------------------


def _already_staged_obrigacao(
    session: Session,
    triple: tuple[int | None, int | None, int | None],
    descricao: str,
) -> bool:
    id_proc, id_comp, id_voto = triple
    stmt = select(ObrigacaoStagingORM.IdObrigacaoStaging).where(
        and_(
            ObrigacaoStagingORM.IdProcesso == id_proc,
            ObrigacaoStagingORM.IdComposicaoPauta == id_comp,
            ObrigacaoStagingORM.IdVotoPauta == id_voto,
            ObrigacaoStagingORM.DescricaoObrigacao == descricao,
            ObrigacaoStagingORM.status.in_(
                [ReviewStatus.pending, ReviewStatus.approved]
            ),
        )
    )
    return session.execute(stmt).first() is not None


def _already_processed_obrigacao(session: Session, id_ner: int | None) -> bool:
    if id_ner is None:
        return False
    stmt = select(ProcessedObrigacaoORM.IdObrigacaoProcessada).where(
        ProcessedObrigacaoORM.IdNerObrigacao == id_ner
    )
    return session.execute(stmt).first() is not None


def _build_obrigacao_staging(
    row: Mapping[str, Any], result: Obrigacao
) -> ObrigacaoStagingORM:
    id_proc, id_comp, id_voto = _identity_triple(row)
    return ObrigacaoStagingORM(
        IdProcesso=id_proc,
        IdComposicaoPauta=id_comp,
        IdVotoPauta=id_voto,
        DescricaoObrigacao=result.descricao_obrigacao,
        DeFazer=result.de_fazer,
        Prazo=result.prazo,
        DataCumprimento=result.data_cumprimento,
        OrgaoResponsavel=result.orgao_responsavel,
        IdOrgaoResponsavel=safe_int(row.get("id_orgao_responsavel")),
        TemMultaCominatoria=result.tem_multa_cominatoria,
        NomeResponsavelMultaCominatoria=result.nome_responsavel_multa_cominatoria,
        DocumentoResponsavelMultaCominatoria=result.documento_responsavel_multa_cominatoria,
        IdPessoaMultaCominatoria=get_id_pessoa_multa_cominatoria(row, result),
        ValorMultaCominatoria=result.valor_multa_cominatoria,
        PeriodoMultaCominatoria=result.periodo_multa_cominatoria,
        EMultaCominatoriaSolidaria=result.e_multa_cominatoria_solidaria,
        SolidariosMultaCominatoria=result.solidarios_multa_cominatoria,
        status=ReviewStatus.pending,
        original_payload=result.model_dump(mode="json"),
    )


def enqueue_obrigacao_extraction(
    filters: ExtractionFilters,
    *,
    extractor: BaseChatModel,
    responsible_extractor: BaseChatModel,
    session: Session,
    rows: Iterable[Mapping[str, Any]] | None = None,
) -> ExtractionReport:
    """Run stage-2 obrigação extraction and write results to ``ObrigacaoStaging``.

    ``rows`` is a test-only escape hatch; when omitted, the SQL driver runs
    against MSSQL via ``get_connection(DB_DECISOES)``.
    """
    report = ExtractionReport()
    iterable = (
        _fetch_driver_rows("obligations_nonprocessed.sql", filters)
        if rows is None
        else rows
    )

    for raw_row in iterable:
        report.scanned += 1
        row = _as_row_dict(raw_row)
        descricao = row.get("descricao_obrigacao")
        if not descricao:
            report.failed += 1
            report.errors.append("row missing descricao_obrigacao")
            continue

        triple = _identity_triple(row)
        id_ner = safe_int(row.get("id_ner_obrigacao"))

        if not filters.overwrite and (
            _already_processed_obrigacao(session, id_ner)
            or _already_staged_obrigacao(session, triple, descricao)
        ):
            report.skipped += 1
            continue

        draft = Obrigacao(
            descricao_obrigacao=descricao,
            orgao_responsavel=row.get("orgao_responsavel"),
        )
        try:
            result = extract_obrigacao(extractor, responsible_extractor, row, draft)
        except Exception as exc:
            report.failed += 1
            report.errors.append(f"{triple}: {exc}")
            logger.exception("Obrigacao extraction failed for %s", triple)
            continue

        session.add(_build_obrigacao_staging(row, result))
        session.commit()
        report.enqueued += 1

    return report


# ---- Recomendação --------------------------------------------------------


def _already_staged_recomendacao(
    session: Session,
    triple: tuple[int | None, int | None, int | None],
    descricao: str,
) -> bool:
    id_proc, id_comp, id_voto = triple
    stmt = select(RecomendacaoStagingORM.IdRecomendacaoStaging).where(
        and_(
            RecomendacaoStagingORM.IdProcesso == id_proc,
            RecomendacaoStagingORM.IdComposicaoPauta == id_comp,
            RecomendacaoStagingORM.IdVotoPauta == id_voto,
            RecomendacaoStagingORM.DescricaoRecomendacao == descricao,
            RecomendacaoStagingORM.status.in_(
                [ReviewStatus.pending, ReviewStatus.approved]
            ),
        )
    )
    return session.execute(stmt).first() is not None


def _already_processed_recomendacao(session: Session, id_ner: int | None) -> bool:
    if id_ner is None:
        return False
    stmt = select(ProcessedRecomendacaoORM.IdRecomendacaoProcessada).where(
        ProcessedRecomendacaoORM.IdNerRecomendacao == id_ner
    )
    return session.execute(stmt).first() is not None


def _build_recomendacao_staging(
    row: Mapping[str, Any], result: Recomendacao
) -> RecomendacaoStagingORM:
    id_proc, id_comp, id_voto = _identity_triple(row)
    return RecomendacaoStagingORM(
        IdProcesso=id_proc,
        IdComposicaoPauta=id_comp,
        IdVotoPauta=id_voto,
        DescricaoRecomendacao=result.descricao_recomendacao,
        PrazoCumprimentoRecomendacao=result.prazo_cumprimento_recomendacao,
        DataCumprimentoRecomendacao=result.data_cumprimento_recomendacao,
        NomeResponsavel=result.nome_responsavel_recomendacao,
        IdPessoaResponsavel=safe_int(row.get("id_pessoa")),
        OrgaoResponsavel=result.orgao_responsavel_recomendacao,
        IdOrgaoResponsavel=safe_int(row.get("id_orgao_responsavel")),
        Cancelado=False,
        status=ReviewStatus.pending,
        original_payload=result.model_dump(mode="json"),
    )


def enqueue_recomendacao_extraction(
    filters: ExtractionFilters,
    *,
    extractor: BaseChatModel,
    responsible_extractor: BaseChatModel,
    session: Session,
    rows: Iterable[Mapping[str, Any]] | None = None,
) -> ExtractionReport:
    """Run stage-2 recomendação extraction and write results to ``RecomendacaoStaging``."""
    report = ExtractionReport()
    iterable = (
        _fetch_driver_rows("recommendations_nonprocessed.sql", filters)
        if rows is None
        else rows
    )

    for raw_row in iterable:
        report.scanned += 1
        row = _as_row_dict(raw_row)
        descricao = row.get("descricao_recomendacao")
        if not descricao:
            report.failed += 1
            report.errors.append("row missing descricao_recomendacao")
            continue

        triple = _identity_triple(row)
        id_ner = safe_int(row.get("id_ner_recomendacao"))

        if not filters.overwrite and (
            _already_processed_recomendacao(session, id_ner)
            or _already_staged_recomendacao(session, triple, descricao)
        ):
            report.skipped += 1
            continue

        draft = Recomendacao(
            descricao_recomendacao=descricao,
            orgao_responsavel_recomendacao=row.get("orgao_responsavel")
            or "Desconhecido",
            nome_responsavel_recomendacao="Desconhecido",
        )
        try:
            result = extract_recomendacao(extractor, responsible_extractor, row, draft)
        except Exception as exc:
            report.failed += 1
            report.errors.append(f"{triple}: {exc}")
            logger.exception("Recomendacao extraction failed for %s", triple)
            continue

        session.add(_build_recomendacao_staging(row, result))
        session.commit()
        report.enqueued += 1

    return report
