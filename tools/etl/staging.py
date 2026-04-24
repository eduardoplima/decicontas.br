"""Staging ORMs for the review layer.

Stage-2 extraction writes to ``ObrigacaoStaging`` / ``RecomendacaoStaging``.
The approval transaction in ``backend/app/review/service.py`` is the only
writer to the final ``Obrigacao`` / ``Recomendacao`` tables.

Each staging row mirrors every field of its final ORM (except the final
autoincrement PK, which is assigned on approval) and adds a review layer:
``status``, ``reviewer``, ``reviewed_at``, ``claimed_by``, ``claimed_at``,
``original_payload``, ``review_notes``.

Lives in ``DB_DECISOES``. Keyed by an independent staging PK; carries the
identity triple ``(IdProcesso, IdComposicaoPauta, IdVotoPauta)``.
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

    status = Column(
        _REVIEW_STATUS_ENUM,
        nullable=False,
        default=ReviewStatus.pending,
        index=True,
    )
    reviewer = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    claimed_by = Column(String(255), nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    original_payload = Column(JSON, nullable=True)
    review_notes = Column(Text, nullable=True)


class RecomendacaoStagingORM(Base):
    __tablename__ = "RecomendacaoStaging"

    IdRecomendacaoStaging = Column(Integer, primary_key=True, autoincrement=True)

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

    status = Column(
        _REVIEW_STATUS_ENUM,
        nullable=False,
        default=ReviewStatus.pending,
        index=True,
    )
    reviewer = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    claimed_by = Column(String(255), nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    original_payload = Column(JSON, nullable=True)
    review_notes = Column(Text, nullable=True)
