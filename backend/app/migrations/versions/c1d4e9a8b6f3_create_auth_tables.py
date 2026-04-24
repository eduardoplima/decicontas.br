"""create auth tables

Revision ID: c1d4e9a8b6f3
Revises: 7a3c9f1b5d42
Create Date: 2026-04-24 00:10:00.000000

Creates ``Users`` and ``RefreshTokens`` in ``DB_DECISOES``. Hand-written —
do not regenerate via ``alembic revision --autogenerate``.

``user_role`` is a SQL enum (``reviewer`` / ``admin``); on SQLite it lowers
to a CHECK constraint, on MSSQL to a CHECK constraint, and on PostgreSQL to
a native enum type.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c1d4e9a8b6f3"
down_revision: Union[str, Sequence[str], None] = "7a3c9f1b5d42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_USER_ROLE = sa.Enum("reviewer", "admin", name="user_role")


def upgrade() -> None:
    op.create_table(
        "Users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            _USER_ROLE,
            nullable=False,
            server_default="reviewer",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_users_username", "Users", ["username"], unique=True)
    op.create_index("ix_users_email", "Users", ["email"], unique=True)

    op.create_table(
        "RefreshTokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("Users.id"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_refresh_tokens_user_id", "RefreshTokens", ["user_id"])
    op.create_index(
        "ix_refresh_tokens_token_hash",
        "RefreshTokens",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_token_hash", table_name="RefreshTokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="RefreshTokens")
    op.drop_table("RefreshTokens")
    op.drop_index("ix_users_email", table_name="Users")
    op.drop_index("ix_users_username", table_name="Users")
    op.drop_table("Users")
