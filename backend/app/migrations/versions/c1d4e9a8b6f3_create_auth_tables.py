"""create auth tables

Revision ID: c1d4e9a8b6f3
Revises: 7a3c9f1b5d42
Create Date: 2026-04-24 00:10:00.000000

Creates ``Usuarios`` and ``TokensRenovacao`` in ``DB_DECISOES``. Hand-written —
do not regenerate via ``alembic revision --autogenerate``.

``papel_usuario`` is a SQL enum (``reviewer`` / ``admin``); on MSSQL it lowers
to a CHECK constraint, native enum on PostgreSQL.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c1d4e9a8b6f3"
down_revision: Union[str, Sequence[str], None] = "7a3c9f1b5d42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_USER_ROLE = sa.Enum("reviewer", "admin", name="papel_usuario")


def upgrade() -> None:
    op.create_table(
        "Usuarios",
        sa.Column("IdUsuario", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("NomeUsuario", sa.String(length=150), nullable=False),
        sa.Column("Email", sa.String(length=255), nullable=False),
        sa.Column("SenhaHash", sa.String(length=255), nullable=False),
        sa.Column(
            "Papel",
            _USER_ROLE,
            nullable=False,
            server_default="reviewer",
        ),
        sa.Column(
            "Ativo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "DataCriacao",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "DataAtualizacao",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_usuarios_nome_usuario", "Usuarios", ["NomeUsuario"], unique=True
    )
    op.create_index("ix_usuarios_email", "Usuarios", ["Email"], unique=True)

    op.create_table(
        "TokensRenovacao",
        sa.Column(
            "IdTokenRenovacao", sa.Integer(), primary_key=True, autoincrement=True
        ),
        sa.Column(
            "IdUsuario",
            sa.Integer(),
            sa.ForeignKey("Usuarios.IdUsuario"),
            nullable=False,
        ),
        sa.Column("HashToken", sa.String(length=255), nullable=False),
        sa.Column("DataExpiracao", sa.DateTime(), nullable=False),
        sa.Column("DataRevogacao", sa.DateTime(), nullable=True),
        sa.Column(
            "DataCriacao",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_tokens_renovacao_id_usuario", "TokensRenovacao", ["IdUsuario"])
    op.create_index(
        "ix_tokens_renovacao_hash_token",
        "TokensRenovacao",
        ["HashToken"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_tokens_renovacao_hash_token", table_name="TokensRenovacao")
    op.drop_index("ix_tokens_renovacao_id_usuario", table_name="TokensRenovacao")
    op.drop_table("TokensRenovacao")
    op.drop_index("ix_usuarios_email", table_name="Usuarios")
    op.drop_index("ix_usuarios_nome_usuario", table_name="Usuarios")
    op.drop_table("Usuarios")
