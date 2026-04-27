"""DTOs for the review API.

``ObrigacaoReview`` / ``RecomendacaoReview`` are the payload schemas for
approvals — one reviewer-editable field per reviewer-editable column on the
final ORM. A schema-parity test pins this mapping so that when a column is
added to the final ORM, the DTO fails the test until it's updated (silent
data-loss guard).

All human-facing field names stay snake_case (Pydantic convention + matches
the stage-2 schemas in ``tools/schema.py``). The service layer translates to
the final ORM's PascalCase Portuguese columns.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


Kind = Literal["obrigacao", "recomendacao"]
ReviewStatusStr = Literal["pending", "approved", "rejected"]
SpanMatchStatusStr = Literal["exact", "fuzzy", "not_found"]


# ----- Approval payloads ---------------------------------------------------


class ObrigacaoReview(BaseModel):
    """Reviewer-editable fields, one-to-one with ``ObrigacaoORM`` (minus the
    auto-assigned ``IdObrigacao`` PK). The identity triple is accepted for
    round-trip convenience but is ignored by the service — the final row's
    triple is authoritative. Edited values land on the ``ObrigacaoStaging``
    audit row, never on the final ``Obrigacao`` row.
    """

    id_processo: Optional[int] = None
    id_composicao_pauta: Optional[int] = None
    id_voto_pauta: Optional[int] = None

    descricao_obrigacao: str
    de_fazer: Optional[bool] = True
    prazo: Optional[str] = None
    data_cumprimento: Optional[date] = None
    orgao_responsavel: Optional[str] = None
    id_orgao_responsavel: Optional[int] = None
    tem_multa_cominatoria: Optional[bool] = False
    nome_responsavel_multa_cominatoria: Optional[str] = None
    documento_responsavel_multa_cominatoria: Optional[str] = None
    id_pessoa_multa_cominatoria: Optional[int] = None
    valor_multa_cominatoria: Optional[float] = None
    periodo_multa_cominatoria: Optional[str] = None
    e_multa_cominatoria_solidaria: Optional[bool] = False
    solidarios_multa_cominatoria: Optional[list[str]] = None


class RecomendacaoReview(BaseModel):
    """Reviewer-editable fields, one-to-one with ``RecomendacaoORM`` (minus
    the auto-assigned ``IdRecomendacao`` PK)."""

    id_processo: Optional[int] = None
    id_composicao_pauta: Optional[int] = None
    id_voto_pauta: Optional[int] = None

    descricao_recomendacao: Optional[str] = None
    prazo_cumprimento_recomendacao: Optional[str] = None
    data_cumprimento_recomendacao: Optional[date] = None
    nome_responsavel: Optional[str] = None
    id_pessoa_responsavel: Optional[int] = None
    orgao_responsavel: Optional[str] = None
    id_orgao_responsavel: Optional[int] = None
    cancelado: Optional[bool] = None


# ----- List / detail responses --------------------------------------------


class ReviewListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: Kind
    status: ReviewStatusStr
    descricao: str
    id_processo: int
    id_composicao_pauta: int
    id_voto_pauta: int
    claimed_by: Optional[str] = None
    claimed_at: Optional[datetime] = None
    reviewer: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class ReviewListPage(BaseModel):
    items: list[ReviewListItem]
    page: int
    page_size: int
    total: int


class ReviewDetail(BaseModel):
    id: int  # IdObrigacao / IdRecomendacao (final-table id)
    kind: Kind
    status: ReviewStatusStr

    id_processo: int
    id_composicao_pauta: int
    id_voto_pauta: int

    # Currently displayed values: pending → final-row fields; approved/rejected
    # → audit-row (reviewer-edited) fields.
    staged: dict[str, Any]
    # When status != pending, holds the immutable LLM extraction from the final
    # row so reviewers can compare what they edited against the original.
    original_payload: Optional[dict[str, Any]] = None

    claimed_by: Optional[str] = None
    claimed_at: Optional[datetime] = None
    reviewer: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None


class ReviewTexto(BaseModel):
    """Full ``texto_acordao`` plus span-match metadata, fetched separately so
    the detail form can render before the (slow) MSSQL text query returns.
    """

    texto_acordao: Optional[str] = None
    matched_span: Optional[str] = None
    span_match_status: SpanMatchStatusStr


# ----- Claim / reject -----------------------------------------------------


class ClaimResponse(BaseModel):
    claimed_by: str
    claimed_at: datetime
    expires_at: datetime


class RejectRequest(BaseModel):
    review_notes: str = Field(min_length=10)
