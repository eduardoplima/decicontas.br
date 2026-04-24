"""``POST /api/v1/etl/run`` + ``GET /api/v1/etl/jobs/{id}`` —
admin role + enqueue behavior. ARQ pool is mocked."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock


def _fake_job(job_id: str = "job-abc"):
    job = MagicMock()
    job.job_id = job_id
    return job


def test_trigger_requires_admin_role(
    authenticated_client, make_staging_obrigacao
) -> None:
    """A reviewer must get 403 from ``/etl/run``."""
    client, _, _ = authenticated_client(username="rev", role="reviewer")
    resp = client.post(
        "/api/v1/etl/run",
        json={"kind": "obrigacao", "filters": {}},
    )
    assert resp.status_code == 403


def test_trigger_as_admin_returns_202_with_job_id(
    authenticated_client, arq_pool
) -> None:
    client, _, _ = authenticated_client(username="boss", role="admin")
    arq_pool.enqueue_job = AsyncMock(return_value=_fake_job("job-xyz"))

    resp = client.post(
        "/api/v1/etl/run",
        json={
            "kind": "obrigacao",
            "filters": {"start_date": "2026-02-01", "end_date": "2026-02-28"},
        },
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["job_id"] == "job-xyz"
    assert body["status_url"] == "/api/v1/etl/jobs/job-xyz"

    arq_pool.enqueue_job.assert_awaited_once()
    call = arq_pool.enqueue_job.await_args
    assert call.args[0] == "run_obrigacao_extraction"
    assert call.args[1] == {
        "start_date": "2026-02-01",
        "end_date": "2026-02-28",
        "process_numbers": None,
        "overwrite": False,
    }
    assert call.kwargs["_queue_name"] == "decicontas:etl"


def test_trigger_recomendacao_uses_correct_task_name(
    authenticated_client, arq_pool
) -> None:
    client, _, _ = authenticated_client(username="boss", role="admin")
    arq_pool.enqueue_job = AsyncMock(return_value=_fake_job())

    resp = client.post("/api/v1/etl/run", json={"kind": "recomendacao", "filters": {}})
    assert resp.status_code == 202
    assert arq_pool.enqueue_job.await_args.args[0] == "run_recomendacao_extraction"


def test_get_job_status_complete(authenticated_client, arq_pool, mocker) -> None:
    client, _, _ = authenticated_client(username="boss", role="admin")

    from arq.jobs import JobStatus

    status_mock = AsyncMock(return_value=JobStatus.complete)
    info = MagicMock()
    info.success = True
    info.result = {"scanned": 1, "enqueued": 1, "skipped": 0, "failed": 0, "errors": []}
    info.enqueue_time = datetime(2026, 4, 24, 10, 0, 0)
    info.start_time = datetime(2026, 4, 24, 10, 0, 5)
    info.finish_time = datetime(2026, 4, 24, 10, 1, 0)
    info_mock = AsyncMock(return_value=info)

    job_ctor = mocker.patch("app.etl.router.Job")
    job_ctor.return_value.status = status_mock
    job_ctor.return_value.result_info = info_mock

    resp = client.get("/api/v1/etl/jobs/abc")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "complete"
    assert body["success"] is True
    assert body["result"]["enqueued"] == 1


def test_get_job_status_not_found(authenticated_client, arq_pool, mocker) -> None:
    client, _, _ = authenticated_client(username="boss", role="admin")

    from arq.jobs import JobStatus

    job_ctor = mocker.patch("app.etl.router.Job")
    job_ctor.return_value.status = AsyncMock(return_value=JobStatus.not_found)

    resp = client.get("/api/v1/etl/jobs/nope")
    assert resp.status_code == 200
    assert resp.json()["status"] == "not_found"


def test_trigger_returns_503_when_pool_unavailable(
    authenticated_client,
) -> None:
    """If ``REDIS_URL`` wasn't configured, ``get_arq_pool`` raises 503."""
    client, _, _ = authenticated_client(username="boss", role="admin")
    # ``arq_pool`` fixture is intentionally NOT requested, so no override.
    resp = client.post("/api/v1/etl/run", json={"kind": "obrigacao", "filters": {}})
    assert resp.status_code == 503
