"""ARQ task tests. Tasks are invoked directly (no arq runtime), so these
don't need Redis. The pipeline is stubbed at the ``app.worker`` boundary for
shape/failure tests; the end-to-end idempotency test drives the real pipeline
with a mocked LLM and the in-memory staging DB.
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---- thin-wrapper shape --------------------------------------------------


def test_obrigacao_task_forwards_filters_and_returns_report(
    in_memory_engine, mocker
) -> None:
    """``run_obrigacao_extraction`` must build an ``ExtractionFilters``
    matching the dict and return the pipeline's ``ExtractionReport`` as a dict.
    """
    from app import worker
    from tools.etl.pipeline import ExtractionFilters, ExtractionReport

    captured: dict = {}

    def _fake_enqueue(filters, **kwargs):
        captured["filters"] = filters
        return ExtractionReport(scanned=3, enqueued=2, skipped=1, failed=0, errors=[])

    mocker.patch.object(worker, "_build_obrigacao_extractor", return_value=object())
    mocker.patch.object(worker, "_build_responsible_extractor", return_value=object())
    mocker.patch.object(worker, "_build_session", return_value=mocker.MagicMock())
    mocker.patch(
        "tools.etl.pipeline.enqueue_obrigacao_extraction",
        side_effect=_fake_enqueue,
    )

    result = _run(
        worker.run_obrigacao_extraction(
            {"job_id": "job-1"},
            {
                "start_date": "2026-02-01",
                "end_date": "2026-02-28",
                "process_numbers": ["001/2026"],
                "overwrite": False,
            },
        )
    )

    from datetime import date

    assert captured["filters"] == ExtractionFilters(
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
        process_numbers=["001/2026"],
        overwrite=False,
    )
    assert result == {
        "scanned": 3,
        "enqueued": 2,
        "skipped": 1,
        "failed": 0,
        "errors": [],
    }


def test_task_failure_propagates(in_memory_engine, mocker) -> None:
    """If the pipeline raises, the task re-raises so ARQ marks the job failed."""
    from app import worker

    mocker.patch.object(worker, "_build_obrigacao_extractor", return_value=object())
    mocker.patch.object(worker, "_build_responsible_extractor", return_value=object())
    mocker.patch.object(worker, "_build_session", return_value=mocker.MagicMock())
    mocker.patch(
        "tools.etl.pipeline.enqueue_obrigacao_extraction",
        side_effect=RuntimeError("pipeline boom"),
    )

    with pytest.raises(RuntimeError, match="pipeline boom"):
        _run(worker.run_obrigacao_extraction({"job_id": "job-2"}, {}))


# ---- end-to-end idempotency (real pipeline, mocked LLM) ------------------


def test_task_idempotent_against_pipeline_dedup(
    in_memory_engine, test_session_factory, mocker
) -> None:
    """Running the task twice with the same input must not create duplicate
    staging rows. Verifies that the pipeline's staging-layer dedup is reached
    via the worker task (not mocked)."""
    from app import worker
    from tools.etl.staging import ObrigacaoStagingORM
    from tools.schema import Obrigacao

    row_from_driver = {
        "id_processo": 541094,
        "id_composicao_pauta": 7001,
        "id_voto_pauta": 9001,
        "id_ner_obrigacao": 123,
        "descricao_obrigacao": "adotar providências corretivas no prazo de 90 dias",
        "orgao_responsavel": "PREFEITURA MUNICIPAL DE EXEMPLO",
        "id_orgao_responsavel": 406,
        "processo": "001/2026",
        "data_sessao": "2026-02-15",
        "texto_acordao": "Acórdão fictício.",
        "responsaveis": [],
    }

    # Pipeline-internal boundary: driver rows + LLM stage-2 call.
    mocker.patch(
        "tools.etl.pipeline._fetch_driver_rows",
        return_value=iter([row_from_driver]),
    )
    mocker.patch(
        "tools.etl.pipeline.extract_obrigacao",
        return_value=Obrigacao(
            descricao_obrigacao=row_from_driver["descricao_obrigacao"],
            orgao_responsavel="PREFEITURA MUNICIPAL DE EXEMPLO",
        ),
    )

    mocker.patch.object(worker, "_build_obrigacao_extractor", return_value=object())
    mocker.patch.object(worker, "_build_responsible_extractor", return_value=object())

    # Each task invocation builds a fresh session from the SAME engine.
    mocker.patch.object(
        worker, "_build_session", side_effect=lambda: test_session_factory()
    )

    def _fresh_rows(*args, **kwargs):
        return iter([row_from_driver])

    # Rebind per-call so the generator is fresh on the second invocation.
    mocker.patch("tools.etl.pipeline._fetch_driver_rows", side_effect=_fresh_rows)

    first = _run(worker.run_obrigacao_extraction({"job_id": "j1"}, {}))
    second = _run(worker.run_obrigacao_extraction({"job_id": "j2"}, {}))

    assert first["enqueued"] == 1
    assert second["enqueued"] == 0
    assert second["skipped"] == 1

    s = test_session_factory()
    try:
        rows = s.execute(select(ObrigacaoStagingORM)).scalars().all()
        assert len(rows) == 1
    finally:
        s.close()
