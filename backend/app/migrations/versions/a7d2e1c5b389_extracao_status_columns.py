"""extend Extracao with status/stage/counters

Revision ID: a7d2e1c5b389
Revises: f3b8c1e7a294
Create Date: 2026-04-27 16:00:00.000000

Adds live-status columns so the ETL orchestrator can update progress on the
``Extracao`` row while it runs through the three stages
(``decisoes`` → ``obrigacoes`` → ``recomendacoes``).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a7d2e1c5b389"
down_revision: Union[str, Sequence[str], None] = "f3b8c1e7a294"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "Extracao",
        sa.Column(
            "Status",
            sa.String(length=20),
            nullable=False,
            server_default="done",
        ),
    )
    op.add_column(
        "Extracao",
        sa.Column(
            "EtapaAtual",
            sa.String(length=30),
            nullable=False,
            server_default="done",
        ),
    )
    op.add_column(
        "Extracao",
        sa.Column(
            "DecisoesProcessadas",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "Extracao",
        sa.Column(
            "ObrigacoesGeradas",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "Extracao",
        sa.Column(
            "RecomendacoesGeradas",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "Extracao",
        sa.Column("Erros", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("Extracao", sa.Column("MensagemErro", sa.Text(), nullable=True))
    op.add_column("Extracao", sa.Column("JobId", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("Extracao", "JobId")
    op.drop_column("Extracao", "MensagemErro")
    op.drop_column("Extracao", "Erros")
    op.drop_column("Extracao", "RecomendacoesGeradas")
    op.drop_column("Extracao", "ObrigacoesGeradas")
    op.drop_column("Extracao", "DecisoesProcessadas")
    op.drop_column("Extracao", "EtapaAtual")
    op.drop_column("Extracao", "Status")
