"""DTOs for the ETL trigger endpoint."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel


JobStatusStr = Literal["queued", "deferred", "in_progress", "complete", "not_found"]
RunStatusStr = Literal["queued", "running", "done", "error"]
EtapaStr = Literal[
    "queued", "decisoes", "obrigacoes", "recomendacoes", "done"
]


class ExtractionFiltersBody(BaseModel):
    start_date: date
    end_date: date
    process_numbers: list[str] | None = None
    overwrite: bool = False


class ExtractionTriggerRequest(BaseModel):
    """Body for ``POST /etl/run``. Single-shot orchestration: NER → obrigação
    → recomendação. No ``kind`` field — the orchestrator runs all three stages.
    """

    filters: ExtractionFiltersBody


class ExtractionJobAccepted(BaseModel):
    extracao_id: int
    job_id: str
    status_url: str
    enqueued_at: datetime


class ExtractionJobStatus(BaseModel):
    job_id: str
    status: JobStatusStr
    success: bool | None = None
    result: dict[str, Any] | None = None
    enqueued_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ExtracaoOut(BaseModel):
    """One row from ``ExtracaoORM`` — covers history and live status."""

    model_config = {"from_attributes": True}

    id: int
    data_inicio: date
    data_fim: date
    data_execucao: datetime
    status: RunStatusStr
    etapa_atual: EtapaStr
    decisoes_processadas: int
    obrigacoes_geradas: int
    recomendacoes_geradas: int
    erros: int
    mensagem_erro: str | None = None
    job_id: str | None = None


class ExtracaoListPage(BaseModel):
    items: list[ExtracaoOut]
    page: int
    page_size: int
    total: int
