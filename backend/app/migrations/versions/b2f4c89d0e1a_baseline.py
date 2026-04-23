"""baseline

Revision ID: b2f4c89d0e1a
Revises:
Create Date: 2026-04-23 11:45:00.000000

Empty by design. The existing production schema in DB_DECISOES is the baseline;
this revision exists only so `alembic stamp head` can mark the live database as
being at the current version without executing any DDL. See
backend/app/migrations/README.md and backend/CLAUDE.md "Alembic baseline".
"""

from typing import Sequence, Union


revision: str = "b2f4c89d0e1a"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
