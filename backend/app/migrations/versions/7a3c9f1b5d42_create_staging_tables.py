"""create staging tables

Revision ID: 7a3c9f1b5d42
Revises: b2f4c89d0e1a
Create Date: 2026-04-24 00:00:00.000000

Creates ``ObrigacaoStaging`` and ``RecomendacaoStaging`` in ``DB_DECISOES``.
Each staging table mirrors its final ORM (minus the final autoincrement PK)
and adds the review layer: status / reviewer / reviewed_at / claimed_by /
claimed_at / original_payload / review_notes.

Hand-written — do not regenerate via ``alembic revision --autogenerate``.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "7a3c9f1b5d42"
down_revision: Union[str, Sequence[str], None] = "b2f4c89d0e1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_REVIEW_STATUS = sa.Enum("pending", "approved", "rejected", name="review_status")


def _review_columns() -> list[sa.Column]:
    return [
        sa.Column("status", _REVIEW_STATUS, nullable=False, server_default="pending"),
        sa.Column("reviewer", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("claimed_by", sa.String(length=255), nullable=True),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.Column("original_payload", sa.JSON(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "ObrigacaoStaging",
        sa.Column(
            "IdObrigacaoStaging", sa.Integer(), primary_key=True, autoincrement=True
        ),
        sa.Column("IdProcesso", sa.Integer(), nullable=False),
        sa.Column("IdComposicaoPauta", sa.Integer(), nullable=False),
        sa.Column("IdVotoPauta", sa.Integer(), nullable=False),
        sa.Column("DescricaoObrigacao", sa.Text(), nullable=False),
        sa.Column("DeFazer", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("Prazo", sa.String(), nullable=True),
        sa.Column("DataCumprimento", sa.Date(), nullable=True),
        sa.Column("OrgaoResponsavel", sa.String(), nullable=True),
        sa.Column("IdOrgaoResponsavel", sa.Integer(), nullable=True),
        sa.Column(
            "TemMultaCominatoria",
            sa.Boolean(),
            nullable=True,
            server_default=sa.false(),
        ),
        sa.Column("NomeResponsavelMultaCominatoria", sa.String(), nullable=True),
        sa.Column("DocumentoResponsavelMultaCominatoria", sa.String(), nullable=True),
        sa.Column("IdPessoaMultaCominatoria", sa.Integer(), nullable=True),
        sa.Column("ValorMultaCominatoria", sa.Float(), nullable=True),
        sa.Column("PeriodoMultaCominatoria", sa.String(), nullable=True),
        sa.Column(
            "EMultaCominatoriaSolidaria",
            sa.Boolean(),
            nullable=True,
            server_default=sa.false(),
        ),
        sa.Column("SolidariosMultaCominatoria", sa.JSON(), nullable=True),
        *_review_columns(),
    )
    op.create_index(
        "ix_obrigacao_staging_triple",
        "ObrigacaoStaging",
        ["IdProcesso", "IdComposicaoPauta", "IdVotoPauta"],
    )
    op.create_index("ix_obrigacao_staging_status", "ObrigacaoStaging", ["status"])

    op.create_table(
        "RecomendacaoStaging",
        sa.Column(
            "IdRecomendacaoStaging",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("IdProcesso", sa.Integer(), nullable=False),
        sa.Column("IdComposicaoPauta", sa.Integer(), nullable=False),
        sa.Column("IdVotoPauta", sa.Integer(), nullable=False),
        sa.Column("DescricaoRecomendacao", sa.String(), nullable=True),
        sa.Column("PrazoCumprimentoRecomendacao", sa.String(), nullable=True),
        sa.Column("DataCumprimentoRecomendacao", sa.Date(), nullable=True),
        sa.Column("NomeResponsavel", sa.String(), nullable=True),
        sa.Column("IdPessoaResponsavel", sa.Integer(), nullable=True),
        sa.Column("OrgaoResponsavel", sa.String(), nullable=True),
        sa.Column("IdOrgaoResponsavel", sa.Integer(), nullable=True),
        sa.Column("Cancelado", sa.Boolean(), nullable=True),
        *_review_columns(),
    )
    op.create_index(
        "ix_recomendacao_staging_triple",
        "RecomendacaoStaging",
        ["IdProcesso", "IdComposicaoPauta", "IdVotoPauta"],
    )
    op.create_index("ix_recomendacao_staging_status", "RecomendacaoStaging", ["status"])


def downgrade() -> None:
    op.drop_index("ix_recomendacao_staging_status", table_name="RecomendacaoStaging")
    op.drop_index("ix_recomendacao_staging_triple", table_name="RecomendacaoStaging")
    op.drop_table("RecomendacaoStaging")
    op.drop_index("ix_obrigacao_staging_status", table_name="ObrigacaoStaging")
    op.drop_index("ix_obrigacao_staging_triple", table_name="ObrigacaoStaging")
    op.drop_table("ObrigacaoStaging")
