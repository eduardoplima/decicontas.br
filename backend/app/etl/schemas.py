"""DTOs for the ETL trigger endpoint."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel


Kind = Literal["obrigacao", "recomendacao"]
JobStatusStr = Literal["queued", "deferred", "in_progress", "complete", "not_found"]


class ExtractionFiltersBody(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    process_numbers: list[str] | None = None
    overwrite: bool = False


class ExtractionTriggerRequest(BaseModel):
    kind: Kind
    filters: ExtractionFiltersBody = ExtractionFiltersBody()


class ExtractionJobAccepted(BaseModel):
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
