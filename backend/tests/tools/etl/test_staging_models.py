"""Tests for the staging ORMs in ``tools.etl.staging``.

Imports are intentionally inside each test body so they resolve to the
``tools.etl.staging`` currently in ``sys.modules`` — this keeps the tests
robust to ``test_scaffolding.py::test_imports_work`` clearing the cache.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


def test_obrigacao_staging_mirrors_final_orm() -> None:
    from tools.etl.staging import ObrigacaoStagingORM
    from tools.models import ObrigacaoORM

    final = {c.name for c in ObrigacaoORM.__table__.columns} - {"IdObrigacao"}
    staging = {c.name for c in ObrigacaoStagingORM.__table__.columns}
    missing = final - staging
    assert not missing, f"ObrigacaoStaging missing columns: {missing}"

    review_cols = {
        "status",
        "reviewer",
        "reviewed_at",
        "claimed_by",
        "claimed_at",
        "original_payload",
        "review_notes",
    }
    assert review_cols.issubset(staging)
    assert "IdObrigacaoStaging" in staging


def test_recomendacao_staging_mirrors_final_orm() -> None:
    from tools.etl.staging import RecomendacaoStagingORM
    from tools.models import RecomendacaoORM

    final = {c.name for c in RecomendacaoORM.__table__.columns} - {"IdRecomendacao"}
    staging = {c.name for c in RecomendacaoStagingORM.__table__.columns}
    missing = final - staging
    assert not missing, f"RecomendacaoStaging missing columns: {missing}"

    review_cols = {
        "status",
        "reviewer",
        "reviewed_at",
        "claimed_by",
        "claimed_at",
        "original_payload",
        "review_notes",
    }
    assert review_cols.issubset(staging)
    assert "IdRecomendacaoStaging" in staging


def test_obrigacao_staging_roundtrip_defaults(in_memory_engine: Engine) -> None:
    from tools.etl.staging import ObrigacaoStagingORM, ReviewStatus

    row = ObrigacaoStagingORM(
        IdProcesso=1,
        IdComposicaoPauta=2,
        IdVotoPauta=3,
        DescricaoObrigacao="adote providências corretivas no prazo de 90 dias",
    )
    with Session(in_memory_engine) as session:
        session.add(row)
        session.commit()
        session.refresh(row)

        fetched = session.get(ObrigacaoStagingORM, row.IdObrigacaoStaging)
        assert fetched is not None
        assert fetched.status == ReviewStatus.pending
        assert fetched.reviewer is None
        assert fetched.reviewed_at is None
        assert fetched.claimed_by is None
        assert fetched.claimed_at is None
        assert fetched.original_payload is None
        assert fetched.review_notes is None
        assert fetched.IdProcesso == 1
        assert fetched.IdComposicaoPauta == 2
        assert fetched.IdVotoPauta == 3


def test_recomendacao_staging_roundtrip_defaults(in_memory_engine: Engine) -> None:
    from tools.etl.staging import RecomendacaoStagingORM, ReviewStatus

    row = RecomendacaoStagingORM(
        IdProcesso=10,
        IdComposicaoPauta=20,
        IdVotoPauta=30,
        DescricaoRecomendacao="aperfeiçoar controles internos",
    )
    with Session(in_memory_engine) as session:
        session.add(row)
        session.commit()
        session.refresh(row)

        fetched = session.get(RecomendacaoStagingORM, row.IdRecomendacaoStaging)
        assert fetched is not None
        assert fetched.status == ReviewStatus.pending
        assert fetched.reviewer is None
        assert fetched.reviewed_at is None
        assert fetched.claimed_by is None
        assert fetched.claimed_at is None
        assert fetched.original_payload is None
        assert fetched.review_notes is None
        assert fetched.IdProcesso == 10


def test_obrigacao_staging_stores_review_layer(in_memory_engine: Engine) -> None:
    from tools.etl.staging import ObrigacaoStagingORM, ReviewStatus

    payload = {"raw": "from LLM", "model": "gpt-4o"}
    reviewed = datetime(2026, 4, 24, 10, 30, 0)
    claimed = datetime(2026, 4, 24, 10, 0, 0)

    row = ObrigacaoStagingORM(
        IdProcesso=1,
        IdComposicaoPauta=2,
        IdVotoPauta=3,
        DescricaoObrigacao="obrigação teste",
        status=ReviewStatus.approved,
        reviewer="auditor.a",
        reviewed_at=reviewed,
        claimed_by="auditor.a",
        claimed_at=claimed,
        original_payload=payload,
        review_notes="aprovado sem ressalvas",
    )
    with Session(in_memory_engine) as session:
        session.add(row)
        session.commit()
        session.refresh(row)

        fetched = session.get(ObrigacaoStagingORM, row.IdObrigacaoStaging)
        assert fetched is not None
        assert fetched.status == ReviewStatus.approved
        assert fetched.reviewer == "auditor.a"
        assert fetched.reviewed_at == reviewed
        assert fetched.claimed_by == "auditor.a"
        assert fetched.claimed_at == claimed
        assert fetched.original_payload == payload
        assert fetched.review_notes == "aprovado sem ressalvas"
