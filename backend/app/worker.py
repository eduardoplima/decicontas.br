"""ARQ worker for stage-2 extraction.

Two tasks wrap ``tools.etl.pipeline``:
  - ``run_obrigacao_extraction``
  - ``run_recomendacao_extraction``

Tasks are thin adapters: they deserialize the filters dict, build clients via
factory functions (no module-level instantiation — keeps tests importable
without touching Azure or MSSQL), call the pipeline, and return an
``ExtractionReport``-compatible dict that ARQ can JSON-serialize.

Idempotency is enforced one layer deeper, in
``tools.etl.pipeline.enqueue_*_extraction`` — staging rows with status
``pending``/``approved`` are skipped via the SQL driver's ``NOT EXISTS`` and
the in-code ``_already_staged_*`` check. Retries are therefore safe by
construction; ``max_tries=3`` below relies on that.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import date
from typing import Any

from arq.connections import RedisSettings

from app.config import get_settings


logger = logging.getLogger(__name__)


# ---- factories (never called at import time) -----------------------------


def _build_obrigacao_extractor():
    from langchain_openai import AzureChatOpenAI

    from tools.schema import Obrigacao

    llm = AzureChatOpenAI(deployment_name="gpt-4-turbo", model_name="gpt-4")
    return llm.with_structured_output(
        Obrigacao, include_raw=False, method="json_schema"
    )


def _build_recomendacao_extractor():
    from langchain_openai import AzureChatOpenAI

    from tools.schema import Recomendacao

    llm = AzureChatOpenAI(deployment_name="gpt-4-turbo", model_name="gpt-4")
    return llm.with_structured_output(
        Recomendacao, include_raw=False, method="json_schema"
    )


def _build_responsible_extractor():
    from langchain_openai import AzureChatOpenAI

    from tools.schema import ResponsibleChoice

    llm = AzureChatOpenAI(deployment_name="gpt-4-turbo", model_name="gpt-4")
    return llm.with_structured_output(
        ResponsibleChoice, include_raw=False, method="json_schema"
    )


def _build_session():
    from sqlalchemy.orm import sessionmaker

    from tools.utils import DB_DECISOES, get_connection

    return sessionmaker(bind=get_connection(DB_DECISOES))()


def _deserialize_filters(d: dict[str, Any]):
    """Coerce a JSON-compatible dict into ``ExtractionFilters``.

    Dates arrive as ISO strings when the router serialized with
    ``model_dump(mode="json")``; this helper normalizes both shapes.
    """
    from tools.etl.pipeline import ExtractionFilters

    def _coerce_date(v):
        if v is None or isinstance(v, date):
            return v
        return date.fromisoformat(v)

    return ExtractionFilters(
        start_date=_coerce_date(d.get("start_date")),
        end_date=_coerce_date(d.get("end_date")),
        process_numbers=d.get("process_numbers"),
        overwrite=bool(d.get("overwrite", False)),
    )


# ---- tasks ---------------------------------------------------------------


async def run_obrigacao_extraction(ctx: dict, filters_dict: dict) -> dict:
    from tools.etl.pipeline import enqueue_obrigacao_extraction

    filters = _deserialize_filters(filters_dict)
    logger.info("task %s: obrigacao extraction with %s", ctx.get("job_id"), filters)

    extractor = _build_obrigacao_extractor()
    responsible_extractor = _build_responsible_extractor()
    session = _build_session()
    try:
        report = enqueue_obrigacao_extraction(
            filters,
            extractor=extractor,
            responsible_extractor=responsible_extractor,
            session=session,
        )
    finally:
        session.close()
    return asdict(report)


async def run_recomendacao_extraction(ctx: dict, filters_dict: dict) -> dict:
    from tools.etl.pipeline import enqueue_recomendacao_extraction

    filters = _deserialize_filters(filters_dict)
    logger.info("task %s: recomendacao extraction with %s", ctx.get("job_id"), filters)

    extractor = _build_recomendacao_extractor()
    responsible_extractor = _build_responsible_extractor()
    session = _build_session()
    try:
        report = enqueue_recomendacao_extraction(
            filters,
            extractor=extractor,
            responsible_extractor=responsible_extractor,
            session=session,
        )
    finally:
        session.close()
    return asdict(report)


# ---- WorkerSettings ------------------------------------------------------


def _redis_settings() -> RedisSettings:
    url = get_settings().redis_url
    if url:
        return RedisSettings.from_dsn(url)
    return RedisSettings()  # defaults: localhost:6379


class WorkerSettings:
    redis_settings = _redis_settings()
    functions = [run_obrigacao_extraction, run_recomendacao_extraction]
    queue_name = "decicontas:etl"
    max_jobs = 4
    job_timeout = 30 * 60
    max_tries = 3
    keep_result = 24 * 3600
    keep_result_forever = False
