"""add ner fk columns to staging tables

Revision ID: d5f2a8e4b1c7
Revises: c1d4e9a8b6f3
Create Date: 2026-04-24 00:20:00.000000

Adds nullable ``IdNerObrigacao`` / ``IdNerRecomendacao`` columns to the staging
tables so the approval transaction can insert ``Processed*ORM`` rows without
re-matching against the NER tables by descricao text.

Nullable because pre-migration rows don't carry the FK. New rows produced by
``tools.etl.pipeline`` populate the column from the SQL driver row.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d5f2a8e4b1c7"
down_revision: Union[str, Sequence[str], None] = "c1d4e9a8b6f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ObrigacaoStaging",
        sa.Column(
            "IdNerObrigacao",
            sa.Integer(),
            sa.ForeignKey("NERObrigacao.IdNerObrigacao"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_obrigacao_staging_id_ner", "ObrigacaoStaging", ["IdNerObrigacao"]
    )
    op.add_column(
        "RecomendacaoStaging",
        sa.Column(
            "IdNerRecomendacao",
            sa.Integer(),
            sa.ForeignKey("NERRecomendacao.IdNerRecomendacao"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_recomendacao_staging_id_ner",
        "RecomendacaoStaging",
        ["IdNerRecomendacao"],
    )


def downgrade() -> None:
    op.drop_index("ix_recomendacao_staging_id_ner", table_name="RecomendacaoStaging")
    op.drop_column("RecomendacaoStaging", "IdNerRecomendacao")
    op.drop_index("ix_obrigacao_staging_id_ner", table_name="ObrigacaoStaging")
    op.drop_column("ObrigacaoStaging", "IdNerObrigacao")
