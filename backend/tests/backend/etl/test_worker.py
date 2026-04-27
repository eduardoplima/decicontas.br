"""ARQ worker tests for ``run_full_extraction``.

Tasks are invoked directly (no arq runtime), so these don't need Redis. The
pipelines are stubbed at the ``app.worker`` boundary; we verify the
orchestrator updates the ``Extracao`` row through each stage and surfaces
failures.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd
import pytest
from sqlalchemy import select


@dataclass
class _FakeReport:
    scanned: int = 0
    enqueued: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] | None = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _seed_extracao(session_factory) -> int:
    from tools.models import ExtracaoORM

    s = session_factory()
    try:
        row = ExtracaoORM(
            DataInicio=date(2026, 2, 1),
            DataFim=date(2026, 2, 28),
            DataExecucao=datetime(2026, 3, 1, 9, 0, 0),
            Status="queued",
            EtapaAtual="queued",
        )
        s.add(row)
        s.commit()
        s.refresh(row)
        return row.IdExtracao
    finally:
        s.close()


def _patch_factories_and_pipelines(
    mocker, *, ner_decisoes: int, ob_report: _FakeReport, rec_report: _FakeReport
):
    """Stub every external dep of run_full_extraction so the test stays
    self-contained (no Azure, no MSSQL, no real LLM)."""
    from app import worker

    mocker.patch.object(worker, "_build_ner_extractor", return_value=object())
    mocker.patch.object(worker, "_build_obrigacao_extractor", return_value=object())
    mocker.patch.object(
        worker, "_build_recomendacao_extractor", return_value=object()
    )
    mocker.patch.object(
        worker, "_build_responsible_extractor", return_value=object()
    )

    df = pd.DataFrame([{"id": i} for i in range(ner_decisoes)])
    mocker.patch("tools.utils.get_decisions_by_dates", return_value=df)
    mocker.patch(
        "tools.utils.run_ner_pipeline_for_dataframe", return_value=None
    )
    mocker.patch(
        "tools.etl.pipeline.enqueue_obrigacao_extraction", return_value=ob_report
    )
    mocker.patch(
        "tools.etl.pipeline.enqueue_recomendacao_extraction",
        return_value=rec_report,
    )


def test_orchestrator_walks_three_stages_and_marks_done(
    in_memory_engine, test_session_factory, mocker
) -> None:
    """Happy path: each stage updates the row; final state is done."""
    from app import worker
    from tools.models import ExtracaoORM

    extracao_id = _seed_extracao(test_session_factory)

    _patch_factories_and_pipelines(
        mocker,
        ner_decisoes=5,
        ob_report=_FakeReport(scanned=5, enqueued=4, skipped=1, failed=0),
        rec_report=_FakeReport(scanned=5, enqueued=2, skipped=3, failed=0),
    )
    # Each task call rebuilds a session; reuse the test engine.
    mocker.patch.object(
        worker, "_build_session", side_effect=lambda: test_session_factory()
    )

    result = _run(
        worker.run_full_extraction(
            {"job_id": "job-1"},
            {
                "start_date": "2026-02-01",
                "end_date": "2026-02-28",
                "process_numbers": None,
                "overwrite": False,
            },
            extracao_id,
        )
    )

    assert result["extracao_id"] == extracao_id
    assert result["decisoes_processadas"] == 5
    assert result["obrigacoes"]["enqueued"] == 4
    assert result["recomendacoes"]["enqueued"] == 2

    s = test_session_factory()
    try:
        row = s.get(ExtracaoORM, extracao_id)
        assert row.Status == "done"
        assert row.EtapaAtual == "done"
        assert row.DecisoesProcessadas == 5
        assert row.ObrigacoesGeradas == 4
        assert row.RecomendacoesGeradas == 2
        assert row.Erros == 0
        assert row.JobId == "job-1"
    finally:
        s.close()


def test_orchestrator_marks_error_when_pipeline_raises(
    in_memory_engine, test_session_factory, mocker
) -> None:
    """If any stage raises, the row must end up as ``status='error'`` with
    the message populated, and the exception must propagate so ARQ retries.
    """
    from app import worker
    from tools.models import ExtracaoORM

    extracao_id = _seed_extracao(test_session_factory)

    mocker.patch.object(worker, "_build_ner_extractor", return_value=object())
    mocker.patch.object(worker, "_build_obrigacao_extractor", return_value=object())
    mocker.patch.object(
        worker, "_build_recomendacao_extractor", return_value=object()
    )
    mocker.patch.object(
        worker, "_build_responsible_extractor", return_value=object()
    )
    mocker.patch.object(
        worker, "_build_session", side_effect=lambda: test_session_factory()
    )
    mocker.patch(
        "tools.utils.get_decisions_by_dates",
        side_effect=RuntimeError("MSSQL unreachable"),
    )

    with pytest.raises(RuntimeError, match="MSSQL unreachable"):
        _run(
            worker.run_full_extraction(
                {"job_id": "job-bad"},
                {
                    "start_date": "2026-02-01",
                    "end_date": "2026-02-28",
                    "process_numbers": None,
                    "overwrite": False,
                },
                extracao_id,
            )
        )

    s = test_session_factory()
    try:
        row = s.get(ExtracaoORM, extracao_id)
        assert row.Status == "error"
        assert row.MensagemErro is not None
        assert "MSSQL unreachable" in row.MensagemErro
    finally:
        s.close()
