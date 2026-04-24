"""Schema-parity test: the approval DTO must cover every reviewer-editable
column on the final ORM, and every field on the DTO must correspond to a
column on the final ORM. Guards against silent data loss when a column is
added to the ORM and the DTO isn't updated in lock-step.
"""

from __future__ import annotations


def _pascal_to_snake(name: str) -> str:
    """Insert ``_`` before every uppercase letter after index 0, then lowercase."""
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


# Columns the DTO is not expected to carry: the auto-assigned PK.
_OBRIGACAO_ALLOWLIST = {"IdObrigacao"}
_RECOMENDACAO_ALLOWLIST = {"IdRecomendacao"}


def test_obrigacao_review_dto_matches_orm_columns() -> None:
    from app.review.schemas import ObrigacaoReview
    from tools.models import ObrigacaoORM

    orm_cols = {c.name for c in ObrigacaoORM.__table__.columns} - _OBRIGACAO_ALLOWLIST
    dto_fields = set(ObrigacaoReview.model_fields.keys())

    # Every final-ORM column must appear on the DTO (snake_case).
    missing_on_dto = {
        col for col in orm_cols if _pascal_to_snake(col) not in dto_fields
    }
    assert not missing_on_dto, (
        f"ObrigacaoReview is missing reviewer-editable fields for ORM columns: "
        f"{sorted(missing_on_dto)}"
    )

    # Every DTO field must correspond to an ORM column (or be in the set of
    # identity-triple fields carried for round-trip convenience).
    orm_snake = {_pascal_to_snake(c) for c in orm_cols}
    extras = dto_fields - orm_snake
    assert not extras, (
        f"ObrigacaoReview has extra fields not on ObrigacaoORM: {sorted(extras)}"
    )


def test_recomendacao_review_dto_matches_orm_columns() -> None:
    from app.review.schemas import RecomendacaoReview
    from tools.models import RecomendacaoORM

    orm_cols = {
        c.name for c in RecomendacaoORM.__table__.columns
    } - _RECOMENDACAO_ALLOWLIST
    dto_fields = set(RecomendacaoReview.model_fields.keys())

    missing_on_dto = {
        col for col in orm_cols if _pascal_to_snake(col) not in dto_fields
    }
    assert not missing_on_dto, (
        f"RecomendacaoReview is missing fields for ORM columns: "
        f"{sorted(missing_on_dto)}"
    )

    orm_snake = {_pascal_to_snake(c) for c in orm_cols}
    extras = dto_fields - orm_snake
    assert not extras, (
        f"RecomendacaoReview has extra fields not on RecomendacaoORM: {sorted(extras)}"
    )
