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
        "Status",
        "Revisor",
        "DataRevisao",
        "ReservadoPor",
        "DataReserva",
        "PayloadOriginal",
        "ObservacoesRevisao",
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
        "Status",
        "Revisor",
        "DataRevisao",
        "ReservadoPor",
        "DataReserva",
        "PayloadOriginal",
        "ObservacoesRevisao",
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
        assert fetched.Status == ReviewStatus.pending
        assert fetched.Revisor is None
        assert fetched.DataRevisao is None
        assert fetched.ReservadoPor is None
        assert fetched.DataReserva is None
        assert fetched.PayloadOriginal is None
        assert fetched.ObservacoesRevisao is None
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
        assert fetched.Status == ReviewStatus.pending
        assert fetched.Revisor is None
        assert fetched.DataRevisao is None
        assert fetched.ReservadoPor is None
        assert fetched.DataReserva is None
        assert fetched.PayloadOriginal is None
        assert fetched.ObservacoesRevisao is None
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
        Status=ReviewStatus.approved,
        Revisor="auditor.a",
        DataRevisao=reviewed,
        ReservadoPor="auditor.a",
        DataReserva=claimed,
        PayloadOriginal=payload,
        ObservacoesRevisao="aprovado sem ressalvas",
    )
    with Session(in_memory_engine) as session:
        session.add(row)
        session.commit()
        session.refresh(row)

        fetched = session.get(ObrigacaoStagingORM, row.IdObrigacaoStaging)
        assert fetched is not None
        assert fetched.Status == ReviewStatus.approved
        assert fetched.Revisor == "auditor.a"
        assert fetched.DataRevisao == reviewed
        assert fetched.ReservadoPor == "auditor.a"
        assert fetched.DataReserva == claimed
        assert fetched.PayloadOriginal == payload
        assert fetched.ObservacoesRevisao == "aprovado sem ressalvas"
