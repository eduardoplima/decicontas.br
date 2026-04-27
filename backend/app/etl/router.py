"""ETL trigger and status endpoints. Admin-only.

``POST /etl/run`` enqueues the orchestrator task that runs NER → obrigação →
recomendação for the given date window. The endpoint creates an ``Extracao``
row up-front (status=``queued``) and returns ``extracao_id`` so the frontend
can poll ``GET /etl/extracoes/{id}`` for live progress.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from arq.jobs import Job, JobStatus
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_arq_pool, get_db_session, require_role
from app.etl import schemas
from tools.models import ExtracaoORM


if TYPE_CHECKING:
    from arq.connections import ArqRedis


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/etl", tags=["etl"])

_QUEUE_NAME = "decicontas:etl"
_TASK_NAME = "run_full_extraction"


_STATUS_MAP = {
    JobStatus.deferred: "deferred",
    JobStatus.queued: "queued",
    JobStatus.in_progress: "in_progress",
    JobStatus.complete: "complete",
    JobStatus.not_found: "not_found",
}


def _to_extracao_out(row: ExtracaoORM) -> schemas.ExtracaoOut:
    return schemas.ExtracaoOut(
        id=row.IdExtracao,
        data_inicio=row.DataInicio,
        data_fim=row.DataFim,
        data_execucao=row.DataExecucao,
        status=row.Status,
        etapa_atual=row.EtapaAtual,
        decisoes_processadas=row.DecisoesProcessadas,
        obrigacoes_geradas=row.ObrigacoesGeradas,
        recomendacoes_geradas=row.RecomendacoesGeradas,
        erros=row.Erros,
        mensagem_erro=row.MensagemErro,
        job_id=row.JobId,
    )


@router.post(
    "/run",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=schemas.ExtractionJobAccepted,
    dependencies=[Depends(require_role("admin"))],
)
async def trigger_extraction(
    body: schemas.ExtractionTriggerRequest,
    pool: "ArqRedis" = Depends(get_arq_pool),
    session: Session = Depends(get_db_session),
) -> schemas.ExtractionJobAccepted:
    enqueued_at = datetime.utcnow()

    extracao = ExtracaoORM(
        DataInicio=body.filters.start_date,
        DataFim=body.filters.end_date,
        DataExecucao=enqueued_at,
        Status="queued",
        EtapaAtual="queued",
    )
    session.add(extracao)
    session.commit()
    session.refresh(extracao)

    job = await pool.enqueue_job(
        _TASK_NAME,
        body.filters.model_dump(mode="json"),
        extracao.IdExtracao,
        _queue_name=_QUEUE_NAME,
    )
    if job is None:
        # Couldn't enqueue: roll back the row so the history isn't polluted
        # with phantom queued runs.
        session.delete(extracao)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="failed to enqueue job",
        )

    extracao.JobId = job.job_id
    session.commit()

    return schemas.ExtractionJobAccepted(
        extracao_id=extracao.IdExtracao,
        job_id=job.job_id,
        status_url=f"/api/v1/etl/extracoes/{extracao.IdExtracao}",
        enqueued_at=enqueued_at,
    )


@router.get(
    "/extracoes",
    response_model=schemas.ExtracaoListPage,
    dependencies=[Depends(require_role("admin"))],
)
def list_extracoes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_db_session),
) -> schemas.ExtracaoListPage:
    base = select(ExtracaoORM).order_by(ExtracaoORM.DataExecucao.desc())
    total = session.execute(
        select(func.count()).select_from(ExtracaoORM)
    ).scalar_one()
    rows = (
        session.execute(base.offset((page - 1) * page_size).limit(page_size))
        .scalars()
        .all()
    )
    return schemas.ExtracaoListPage(
        items=[_to_extracao_out(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/extracoes/{extracao_id}",
    response_model=schemas.ExtracaoOut,
    dependencies=[Depends(require_role("admin"))],
)
def get_extracao(
    extracao_id: int,
    session: Session = Depends(get_db_session),
) -> schemas.ExtracaoOut:
    row = session.get(ExtracaoORM, extracao_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="extracao not found"
        )
    return _to_extracao_out(row)


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
