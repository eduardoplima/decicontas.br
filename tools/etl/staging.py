"""Staging ORMs — review audit trail.

Each staging row is the **audit record** of one approve/reject action. It
points at the final-table row that was reviewed via ``IdObrigacao`` /
``IdRecomendacao``, mirrors the field columns (so the audit row carries the
reviewer's edited values), and adds review metadata: ``Status``, ``Revisor``,
``DataRevisao``, ``ObservacoesRevisao``, ``PayloadOriginal``.

A final row with no audit row is *pending review*; one with an audit row is
*approved* or *rejected* (see ``Status`` on the audit row).

Stage-2 ETL writes to the final tables (`Obrigacao` / `Recomendacao`), not
here — see ``tools.etl.pipeline``.

Lives in ``DB_DECISOES``. Keyed by an independent staging PK; carries the
identity triple ``(IdProcesso, IdComposicaoPauta, IdVotoPauta)`` redundantly
for ad-hoc joins.

The legacy ``ReservadoPor`` / ``DataReserva`` columns on staging are unused
under the current model — claim state lives on the final rows
(`ObrigacaoORM.ReservadoPor`, etc.). They remain on the table for backward
compatibility with the existing schema; do not write them.
"""

from __future__ import annotations

import enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)

from tools.models import Base


class ReviewStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


_REVIEW_STATUS_ENUM = Enum(
    ReviewStatus,
    name="review_status",
    values_callable=lambda e: [member.value for member in e],
)


class ObrigacaoStagingORM(Base):
    __tablename__ = "ObrigacaoStaging"

    IdObrigacaoStaging = Column(Integer, primary_key=True, autoincrement=True)

    # Nullable so the SQLite-bound test in-memory schema (and the production
    # baseline that pre-existed this column) accept rows without the FK.
    # The application path always sets it; the unique index in the
    # corresponding Alembic migration is partial (``WHERE IdObrigacao IS NOT NULL``)
    # so multiple NULLs don't collide.
    IdObrigacao = Column(
        Integer,
        ForeignKey("Obrigacao.IdObrigacao"),
        nullable=True,
        index=True,
    )

    IdNerObrigacao = Column(
        Integer,
        ForeignKey("NERObrigacao.IdNerObrigacao"),
        nullable=True,
        index=True,
    )

    IdProcesso = Column(Integer, nullable=False, index=True)
    IdComposicaoPauta = Column(Integer, nullable=False)
    IdVotoPauta = Column(Integer, nullable=False)

    DescricaoObrigacao = Column(Text, nullable=False)
    DeFazer = Column(Boolean, default=True)
    Prazo = Column(String, nullable=True)
    DataCumprimento = Column(Date, nullable=True)
    OrgaoResponsavel = Column(String, nullable=True)
    IdOrgaoResponsavel = Column(Integer, nullable=True)
    TemMultaCominatoria = Column(Boolean, default=False)
    NomeResponsavelMultaCominatoria = Column(String, nullable=True)
    DocumentoResponsavelMultaCominatoria = Column(String, nullable=True)
    IdPessoaMultaCominatoria = Column(Integer, nullable=True)
    ValorMultaCominatoria = Column(Float, nullable=True)
    PeriodoMultaCominatoria = Column(String, nullable=True)
    EMultaCominatoriaSolidaria = Column(Boolean, default=False)
    SolidariosMultaCominatoria = Column(JSON, nullable=True)

    Status = Column(
        _REVIEW_STATUS_ENUM,
        nullable=False,
        default=ReviewStatus.pending,
        index=True,
    )
    Revisor = Column(String(255), nullable=True)
    DataRevisao = Column(DateTime, nullable=True)
    ReservadoPor = Column(String(255), nullable=True)
    DataReserva = Column(DateTime, nullable=True)
    PayloadOriginal = Column(JSON, nullable=True)
    ObservacoesRevisao = Column(Text, nullable=True)


class RecomendacaoStagingORM(Base):
    __tablename__ = "RecomendacaoStaging"

    IdRecomendacaoStaging = Column(Integer, primary_key=True, autoincrement=True)

    # See note on ``ObrigacaoStagingORM.IdObrigacao``.
    IdRecomendacao = Column(
        Integer,
        ForeignKey("Recomendacao.IdRecomendacao"),
        nullable=True,
        index=True,
    )

    IdNerRecomendacao = Column(
        Integer,
        ForeignKey("NERRecomendacao.IdNerRecomendacao"),
        nullable=True,
        index=True,
    )

    IdProcesso = Column(Integer, nullable=False, index=True)
    IdComposicaoPauta = Column(Integer, nullable=False)
    IdVotoPauta = Column(Integer, nullable=False)

    DescricaoRecomendacao = Column(String, nullable=True)
    PrazoCumprimentoRecomendacao = Column(String, nullable=True)
    DataCumprimentoRecomendacao = Column(Date, nullable=True)
    NomeResponsavel = Column(String, nullable=True)
    IdPessoaResponsavel = Column(Integer, nullable=True)
    OrgaoResponsavel = Column(String, nullable=True)
    IdOrgaoResponsavel = Column(Integer, nullable=True)
    Cancelado = Column(Boolean, nullable=True)

    Status = Column(
        _REVIEW_STATUS_ENUM,
        nullable=False,
        default=ReviewStatus.pending,
        index=True,
    )
    Revisor = Column(String(255), nullable=True)
    DataRevisao = Column(DateTime, nullable=True)
    ReservadoPor = Column(String(255), nullable=True)
    DataReserva = Column(DateTime, nullable=True)
    PayloadOriginal = Column(JSON, nullable=True)
    ObservacoesRevisao = Column(Text, nullable=True)
