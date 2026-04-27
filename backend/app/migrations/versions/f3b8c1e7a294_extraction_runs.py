"""create Extracao table + seed historical run

Revision ID: f3b8c1e7a294
Revises: e9a4b7c2f8d1
Create Date: 2026-04-27 14:00:00.000000

Tracks one row per stage-2 extraction run. ``DataInicio`` / ``DataFim`` cover
the session-date window passed to ``get_decisions_by_dates``;
``DataExecucao`` is when the job was triggered.

Seeds the table with the historical run that scanned 2026-01-13 → 2026-02-26
on 2026-03-16 — that one happened before the table existed.
"""

from datetime import date, datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f3b8c1e7a294"
down_revision: Union[str, Sequence[str], None] = "e9a4b7c2f8d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    extracao = op.create_table(
        "Extracao",
        sa.Column("IdExtracao", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("DataInicio", sa.Date(), nullable=False),
        sa.Column("DataFim", sa.Date(), nullable=False),
        sa.Column(
            "DataExecucao",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.bulk_insert(
        extracao,
        [
            {
                "DataInicio": date(2026, 1, 13),
                "DataFim": date(2026, 2, 26),
                "DataExecucao": datetime(2026, 3, 16, 0, 0, 0),
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("Extracao")
