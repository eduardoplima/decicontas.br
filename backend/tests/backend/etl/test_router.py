"""``POST /api/v1/etl/run`` + ``GET /api/v1/etl/extracoes[/{id}]`` — admin
role + persistence + orchestrator enqueue. ARQ pool is mocked.
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import select


def _fake_job(job_id: str = "job-abc"):
    job = MagicMock()
    job.job_id = job_id
    return job


def test_trigger_requires_admin_role(authenticated_client) -> None:
    """A reviewer must get 403 from ``/etl/run``."""
    client, _, _ = authenticated_client(username="rev", role="reviewer")
    resp = client.post(
        "/api/v1/etl/run",
        json={"filters": {"start_date": "2026-02-01", "end_date": "2026-02-28"}},
    )
    assert resp.status_code == 403


def test_trigger_persists_extracao_and_enqueues_orchestrator(
    authenticated_client, arq_pool, test_session_factory
) -> None:
    from tools.models import ExtracaoORM

    client, _, _ = authenticated_client(username="boss", role="admin")
    arq_pool.enqueue_job = AsyncMock(return_value=_fake_job("job-xyz"))

    resp = client.post(
        "/api/v1/etl/run",
        json={
            "filters": {"start_date": "2026-02-01", "end_date": "2026-02-28"},
        },
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["job_id"] == "job-xyz"
    assert isinstance(body["extracao_id"], int)
    assert body["status_url"] == f"/api/v1/etl/extracoes/{body['extracao_id']}"

    # Single orchestrator task — no per-kind dispatch anymore.
    arq_pool.enqueue_job.assert_awaited_once()
    call = arq_pool.enqueue_job.await_args
    assert call.args[0] == "run_full_extraction"
    assert call.args[1] == {
        "start_date": "2026-02-01",
        "end_date": "2026-02-28",
        "process_numbers": None,
        "overwrite": False,
    }
    assert call.args[2] == body["extracao_id"]
    assert call.kwargs["_queue_name"] == "decicontas:etl"

    # Persisted Extracao row carries the queued state and the job_id.
    s = test_session_factory()
    try:
        rows = s.execute(select(ExtracaoORM)).scalars().all()
        assert len(rows) == 1
        assert rows[0].DataInicio == date(2026, 2, 1)
        assert rows[0].DataFim == date(2026, 2, 28)
        assert rows[0].Status == "queued"
        assert rows[0].EtapaAtual == "queued"
        assert rows[0].JobId == "job-xyz"
    finally:
        s.close()


def test_trigger_returns_503_when_pool_unavailable(authenticated_client) -> None:
    """If ``REDIS_URL`` wasn't configured, ``get_arq_pool`` raises 503 — and
    no Extracao row should leak into the history.
    """
    client, _, _ = authenticated_client(username="boss", role="admin")
    resp = client.post(
        "/api/v1/etl/run",
        json={"filters": {"start_date": "2026-02-01", "end_date": "2026-02-28"}},
    )
    assert resp.status_code == 503


def test_get_extracao_returns_status(
    authenticated_client, test_session_factory
) -> None:
    from tools.models import ExtracaoORM

    s = test_session_factory()
    try:
        row = ExtracaoORM(
            DataInicio=date(2026, 2, 1),
            DataFim=date(2026, 2, 28),
            DataExecucao=datetime(2026, 3, 1, 9, 0, 0),
            Status="running",
            EtapaAtual="obrigacoes",
            DecisoesProcessadas=10,
            ObrigacoesGeradas=4,
            RecomendacoesGeradas=0,
            Erros=0,
        )
        s.add(row)
        s.commit()
        s.refresh(row)
        extracao_id = row.IdExtracao
    finally:
        s.close()

    client, _, _ = authenticated_client(username="boss", role="admin")
    resp = client.get(f"/api/v1/etl/extracoes/{extracao_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "running"
    assert body["etapa_atual"] == "obrigacoes"
    assert body["decisoes_processadas"] == 10
    assert body["obrigacoes_geradas"] == 4


def test_get_extracao_404_when_unknown(authenticated_client) -> None:
    client, _, _ = authenticated_client(username="boss", role="admin")
    resp = client.get("/api/v1/etl/extracoes/999999")
    assert resp.status_code == 404


def test_list_extracoes_requires_admin(authenticated_client) -> None:
    client, _, _ = authenticated_client(username="rev", role="reviewer")
    resp = client.get("/api/v1/etl/extracoes")
    assert resp.status_code == 403


def test_list_extracoes_returns_rows_desc(
    authenticated_client, test_session_factory
) -> None:
    """Most recently executed run comes first."""
    from tools.models import ExtracaoORM

    s = test_session_factory()
    try:
        s.add(
            ExtracaoORM(
                DataInicio=date(2026, 1, 13),
                DataFim=date(2026, 2, 26),
                DataExecucao=datetime(2026, 3, 16, 0, 0, 0),
                Status="done",
                EtapaAtual="done",
            )
        )
        s.add(
            ExtracaoORM(
                DataInicio=date(2026, 3, 1),
                DataFim=date(2026, 3, 15),
                DataExecucao=datetime(2026, 3, 20, 12, 0, 0),
                Status="done",
                EtapaAtual="done",
            )
        )
        s.add(
            ExtracaoORM(
                DataInicio=date(2025, 12, 1),
                DataFim=date(2025, 12, 31),
                DataExecucao=datetime(2026, 1, 5, 9, 30, 0),
                Status="done",
                EtapaAtual="done",
            )
        )
        s.commit()
    finally:
        s.close()

    client, _, _ = authenticated_client(username="boss", role="admin")
    resp = client.get("/api/v1/etl/extracoes")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    items = body["items"]
    assert items[0]["data_inicio"] == "2026-03-01"
    assert items[1]["data_inicio"] == "2026-01-13"
    assert items[2]["data_inicio"] == "2025-12-01"
