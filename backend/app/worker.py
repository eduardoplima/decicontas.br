"""ARQ worker for stage-1 (NER) + stage-2 extraction.

A single orchestrator task ``run_full_extraction`` runs the three pipeline
stages back-to-back and updates the ``ExtracaoORM`` row after each stage so
the frontend can poll for live status:

  1. ``decisoes`` — NER extraction on raw decision texts via
     ``tools.utils.run_ner_pipeline_for_dataframe``.
  2. ``obrigacoes`` — stage-2 obrigação extraction.
  3. ``recomendacoes`` — stage-2 recomendação extraction.

Tasks are thin adapters: they build clients via factory functions (no
module-level instantiation — keeps tests importable without touching Azure
or MSSQL), call the pipelines, and update the ``Extracao`` row.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from arq.connections import RedisSettings
from sqlalchemy import update

from app.config import get_settings


logger = logging.getLogger(__name__)


# ---- factories (never called at import time) -----------------------------


def _build_ner_extractor():
    from langchain_openai import AzureChatOpenAI

    from tools.schema import NERDecisao

    llm = AzureChatOpenAI(deployment_name="gpt-4-turbo", model_name="gpt-4")
    return llm.with_structured_output(
        NERDecisao, include_raw=False, method="json_schema"
    )


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
    """Coerce a JSON-compatible dict into ``ExtractionFilters``."""
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


# ---- progress updates ---------------------------------------------------


_FIELD_MAP = {
    "status": "Status",
    "etapa": "EtapaAtual",
    "decisoes_processadas": "DecisoesProcessadas",
    "obrigacoes_geradas": "ObrigacoesGeradas",
    "recomendacoes_geradas": "RecomendacoesGeradas",
    "erros": "Erros",
    "mensagem_erro": "MensagemErro",
    "job_id": "JobId",
}


def _update_extracao(session, extracao_id: int, **fields) -> None:
    from tools.models import ExtracaoORM

    updates = {_FIELD_MAP[k]: v for k, v in fields.items() if k in _FIELD_MAP}
    if not updates:
        return
    session.execute(
        update(ExtracaoORM)
        .where(ExtracaoORM.IdExtracao == extracao_id)
        .values(**updates)
    )
    session.commit()


# ---- orchestrator task --------------------------------------------------


async def run_full_extraction(
    ctx: dict, filters_dict: dict, extracao_id: int
) -> dict:
    """Run NER → Obrigação → Recomendação for one date window, updating the
    ``Extracao`` row after each stage so the frontend's poller sees progress.
    """
    from tools.etl.pipeline import (
        enqueue_obrigacao_extraction,
        enqueue_recomendacao_extraction,
    )
    from tools.utils import (
        get_decisions_by_dates,
        run_ner_pipeline_for_dataframe,
    )

    filters = _deserialize_filters(filters_dict)
    job_id = ctx.get("job_id")
    logger.info("orchestrator job %s starting (extracao=%s)", job_id, extracao_id)

    session = _build_session()
    try:
        _update_extracao(
            session,
            extracao_id,
            status="running",
            etapa="decisoes",
            job_id=job_id,
        )

        # Stage 1 — NER.
        df = get_decisions_by_dates(filters.start_date, filters.end_date)
        scanned = len(df)
        ner_extractor = _build_ner_extractor()
        run_ner_pipeline_for_dataframe(
            df, ner_extractor, model_name="gpt-4", prompt_version="v1"
        )
        _update_extracao(
            session,
            extracao_id,
            decisoes_processadas=scanned,
            etapa="obrigacoes",
        )

        # Stage 2a — Obrigação.
        ob_session = _build_session()
        try:
            ob_report = enqueue_obrigacao_extraction(
                filters,
                extractor=_build_obrigacao_extractor(),
                responsible_extractor=_build_responsible_extractor(),
                session=ob_session,
            )
        finally:
            ob_session.close()
        _update_extracao(
            session,
            extracao_id,
            obrigacoes_geradas=ob_report.enqueued,
            erros=ob_report.failed,
            etapa="recomendacoes",
        )

        # Stage 2b — Recomendação.
        rec_session = _build_session()
        try:
            rec_report = enqueue_recomendacao_extraction(
                filters,
                extractor=_build_recomendacao_extractor(),
                responsible_extractor=_build_responsible_extractor(),
                session=rec_session,
            )
        finally:
            rec_session.close()
        _update_extracao(
            session,
            extracao_id,
            recomendacoes_geradas=rec_report.enqueued,
            erros=ob_report.failed + rec_report.failed,
            etapa="done",
            status="done",
        )

        return {
            "extracao_id": extracao_id,
            "decisoes_processadas": scanned,
            "obrigacoes": asdict(ob_report),
            "recomendacoes": asdict(rec_report),
        }
    except Exception as exc:
        logger.exception("orchestrator job %s failed", job_id)
        _update_extracao(
            session,
            extracao_id,
            status="error",
            mensagem_erro=str(exc)[:500],
        )
        raise
    finally:
        session.close()


# ---- WorkerSettings ------------------------------------------------------


def _redis_settings() -> RedisSettings:
    url = get_settings().redis_url
    if url:
        return RedisSettings.from_dsn(url)
    return RedisSettings()  # defaults: localhost:6379


class WorkerSettings:
    redis_settings = _redis_settings()
    functions = [run_full_extraction]
    queue_name = "decicontas:etl"
    max_jobs = 4
    job_timeout = 60 * 60  # NER step can be long for wide windows
    max_tries = 3
    keep_result = 24 * 3600
    keep_result_forever = False
