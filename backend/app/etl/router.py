"""ETL trigger and status endpoints. Admin-only.

The POST endpoint enqueues an ARQ job and returns 202 immediately — all heavy
work happens in ``app.worker``. The GET endpoint is a read-through to ARQ's
job status so the frontend can poll.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from arq.jobs import Job, JobStatus
from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_arq_pool, require_role
from app.etl import schemas


if TYPE_CHECKING:
    from arq.connections import ArqRedis


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/etl", tags=["etl"])

_QUEUE_NAME = "decicontas:etl"

_TASK_BY_KIND = {
    "obrigacao": "run_obrigacao_extraction",
    "recomendacao": "run_recomendacao_extraction",
}


_STATUS_MAP = {
    JobStatus.deferred: "deferred",
    JobStatus.queued: "queued",
    JobStatus.in_progress: "in_progress",
    JobStatus.complete: "complete",
    JobStatus.not_found: "not_found",
}


@router.post(
    "/run",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=schemas.ExtractionJobAccepted,
    dependencies=[Depends(require_role("admin"))],
)
async def trigger_extraction(
    body: schemas.ExtractionTriggerRequest,
    pool: "ArqRedis" = Depends(get_arq_pool),
) -> schemas.ExtractionJobAccepted:
    task_name = _TASK_BY_KIND[body.kind]
    job = await pool.enqueue_job(
        task_name,
        body.filters.model_dump(mode="json"),
        _queue_name=_QUEUE_NAME,
    )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="failed to enqueue job",
        )
    return schemas.ExtractionJobAccepted(
        job_id=job.job_id,
        status_url=f"/api/v1/etl/jobs/{job.job_id}",
        enqueued_at=datetime.utcnow(),
    )


@router.get(
    "/jobs/{job_id}",
    response_model=schemas.ExtractionJobStatus,
    dependencies=[Depends(require_role("admin"))],
)
async def get_job_status(
    job_id: str,
    pool: "ArqRedis" = Depends(get_arq_pool),
) -> schemas.ExtractionJobStatus:
    job = Job(job_id=job_id, redis=pool, _queue_name=_QUEUE_NAME)
    job_status = await job.status()
    status_str = _STATUS_MAP.get(job_status, "not_found")

    if job_status == JobStatus.not_found:
        return schemas.ExtractionJobStatus(job_id=job_id, status="not_found")

    info = await job.result_info()
    if info is None:
        return schemas.ExtractionJobStatus(job_id=job_id, status=status_str)

    return schemas.ExtractionJobStatus(
        job_id=job_id,
        status=status_str,
        success=info.success,
        result=info.result if isinstance(info.result, dict) else None,
        enqueued_at=info.enqueue_time,
        started_at=info.start_time,
        finished_at=info.finish_time,
    )
