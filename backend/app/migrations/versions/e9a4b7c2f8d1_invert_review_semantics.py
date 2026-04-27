"""invert review semantics

Revision ID: e9a4b7c2f8d1
Revises: d5f2a8e4b1c7
Create Date: 2026-04-27 12:00:00.000000

Move claim state to the final tables (`Obrigacao` / `Recomendacao`) and link
each staging audit row to the final-table row it reviews.

Under the new model:
  * Stage-2 ETL writes directly to ``Obrigacao`` / ``Recomendacao``.
  * Pendente review = a final-table row without a corresponding ``*Staging``
    audit row (LEFT JOIN + ``IS NULL``).
  * Approve/reject inserts one ``*Staging`` audit row pointing at the final
    row via ``IdObrigacao`` / ``IdRecomendacao``.
  * Claim state (``ReservadoPor`` / ``DataReserva``) lives on the final row.

Existing ``ReservadoPor`` / ``DataReserva`` columns on staging become unused
but are kept for backward compatibility — no data loss.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e9a4b7c2f8d1"
down_revision: Union[str, Sequence[str], None] = "d5f2a8e4b1c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Claim state on the final tables.
    op.add_column(
        "Obrigacao",
        sa.Column("ReservadoPor", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "Obrigacao",
        sa.Column("DataReserva", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "Recomendacao",
        sa.Column("ReservadoPor", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "Recomendacao",
        sa.Column("DataReserva", sa.DateTime(), nullable=True),
    )

    # FK from staging audit rows to the reviewed final row. Nullable in DDL so
    # the migration does not fail on pre-existing staging rows; the application
    # writes it on every new audit insert and the unique index guarantees at
    # most one audit per final row going forward.
    op.add_column(
        "ObrigacaoStaging",
        sa.Column(
            "IdObrigacao",
            sa.Integer(),
            sa.ForeignKey("Obrigacao.IdObrigacao"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_obrigacao_staging_id_obrigacao",
        "ObrigacaoStaging",
        ["IdObrigacao"],
        unique=True,
        mssql_where=sa.text("[IdObrigacao] IS NOT NULL"),
    )

    op.add_column(
        "RecomendacaoStaging",
        sa.Column(
            "IdRecomendacao",
            sa.Integer(),
            sa.ForeignKey("Recomendacao.IdRecomendacao"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_recomendacao_staging_id_recomendacao",
        "RecomendacaoStaging",
        ["IdRecomendacao"],
        unique=True,
        mssql_where=sa.text("[IdRecomendacao] IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_recomendacao_staging_id_recomendacao", table_name="RecomendacaoStaging"
    )
    op.drop_column("RecomendacaoStaging", "IdRecomendacao")
    op.drop_index(
        "ix_obrigacao_staging_id_obrigacao", table_name="ObrigacaoStaging"
    )
    op.drop_column("ObrigacaoStaging", "IdObrigacao")
    op.drop_column("Recomendacao", "DataReserva")
    op.drop_column("Recomendacao", "ReservadoPor")
    op.drop_column("Obrigacao", "DataReserva")
    op.drop_column("Obrigacao", "ReservadoPor")
