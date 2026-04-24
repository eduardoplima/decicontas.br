"""Tests for ``tools.etl.pipeline``.

Happy path (one staging row written) and dedup (second call with the same
identity triple doesn't duplicate). The stage-2 extractor functions
(``tools.utils.extract_obrigacao`` / ``extract_recomendacao``) are patched
at the pipeline's import boundary to avoid hitting MSSQL or the LLM.
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


def _sample_obrigacao_row() -> dict:
    return {
        "id_processo": 541094,
        "id_composicao_pauta": 7001,
        "id_voto_pauta": 9001,
        "id_ner_obrigacao": 123,
        "descricao_obrigacao": (
            "adotar providências corretivas no prazo de 90 dias, sob pena "
            "de multa cominatória"
        ),
        "orgao_responsavel": "PREFEITURA MUNICIPAL DE EXEMPLO",
        "id_orgao_responsavel": 406,
        "processo": "001234/2026",
        "data_sessao": datetime(2026, 2, 15, 14, 0),
        "texto_acordao": "Acórdão fictício para teste.",
        "responsaveis": [
            {
                "nome_responsavel": "FULANO DE TAL",
                "documento_responsavel": "000.000.000-00",
                "tipo_responsavel": "F",
                "id_pessoa": 54720,
            }
        ],
    }


def _sample_recomendacao_row() -> dict:
    return {
        "id_processo": 541094,
        "id_composicao_pauta": 7001,
        "id_voto_pauta": 9001,
        "id_ner_recomendacao": 456,
        "descricao_recomendacao": "aperfeiçoar controles internos de execução orçamentária",
        "orgao_responsavel": "SECRETARIA MUNICIPAL DE EXEMPLO",
        "id_orgao_responsavel": 308,
        "id_pessoa": 54720,
        "processo": "001234/2026",
        "data_sessao": datetime(2026, 2, 15, 14, 0),
        "texto_acordao": "Acórdão fictício para teste.",
        "responsaveis": [
            {
                "nome_responsavel": "FULANO DE TAL",
                "documento_responsavel": "000.000.000-00",
                "tipo_responsavel": "F",
                "id_pessoa": 54720,
            }
        ],
    }


def test_enqueue_obrigacao_writes_one_staging_row(
    in_memory_engine: Engine, mocker
) -> None:
    from tools.etl.pipeline import (
        ExtractionFilters,
        enqueue_obrigacao_extraction,
    )
    from tools.etl.staging import ObrigacaoStagingORM, ReviewStatus
    from tools.schema import Obrigacao

    fake_result = Obrigacao(
        descricao_obrigacao="adotar providências corretivas em 90 dias",
        de_fazer=True,
        prazo="90 dias",
        data_cumprimento=date(2026, 5, 15),
        orgao_responsavel="PREFEITURA MUNICIPAL DE EXEMPLO",
        tem_multa_cominatoria=True,
        valor_multa_cominatoria=1000.0,
        periodo_multa_cominatoria="diário",
    )
    mocker.patch("tools.etl.pipeline.extract_obrigacao", return_value=fake_result)

    with Session(in_memory_engine) as session:
        report = enqueue_obrigacao_extraction(
            ExtractionFilters(),
            extractor=MagicMock(),
            responsible_extractor=MagicMock(),
            session=session,
            rows=[_sample_obrigacao_row()],
        )

        assert report.scanned == 1
        assert report.enqueued == 1
        assert report.skipped == 0
        assert report.failed == 0

        rows = session.execute(select(ObrigacaoStagingORM)).scalars().all()
        assert len(rows) == 1
        staged = rows[0]
        assert staged.IdProcesso == 541094
        assert staged.IdComposicaoPauta == 7001
        assert staged.IdVotoPauta == 9001
        assert staged.status == ReviewStatus.pending
        assert staged.DescricaoObrigacao == fake_result.descricao_obrigacao
        assert staged.Prazo == "90 dias"
        assert staged.ValorMultaCominatoria == 1000.0
        assert staged.original_payload is not None
        assert (
            staged.original_payload["descricao_obrigacao"]
            == fake_result.descricao_obrigacao
        )
        assert staged.original_payload["data_cumprimento"] == "2026-05-15"


def test_enqueue_obrigacao_dedupes_same_triple(
    in_memory_engine: Engine, mocker
) -> None:
    from tools.etl.pipeline import (
        ExtractionFilters,
        enqueue_obrigacao_extraction,
    )
    from tools.etl.staging import ObrigacaoStagingORM
    from tools.schema import Obrigacao

    mocker.patch(
        "tools.etl.pipeline.extract_obrigacao",
        return_value=Obrigacao(
            descricao_obrigacao=_sample_obrigacao_row()["descricao_obrigacao"]
        ),
    )

    row = _sample_obrigacao_row()
    with Session(in_memory_engine) as session:
        first = enqueue_obrigacao_extraction(
            ExtractionFilters(),
            extractor=MagicMock(),
            responsible_extractor=MagicMock(),
            session=session,
            rows=[row],
        )
        second = enqueue_obrigacao_extraction(
            ExtractionFilters(),
            extractor=MagicMock(),
            responsible_extractor=MagicMock(),
            session=session,
            rows=[row],
        )

        assert first.enqueued == 1 and first.skipped == 0
        assert second.enqueued == 0 and second.skipped == 1

        count = session.execute(select(ObrigacaoStagingORM)).scalars().all()
        assert len(count) == 1


def test_enqueue_recomendacao_writes_one_staging_row(
    in_memory_engine: Engine, mocker
) -> None:
    from tools.etl.pipeline import (
        ExtractionFilters,
        enqueue_recomendacao_extraction,
    )
    from tools.etl.staging import RecomendacaoStagingORM, ReviewStatus
    from tools.schema import Recomendacao

    fake_result = Recomendacao(
        descricao_recomendacao="aperfeiçoar controles internos",
        orgao_responsavel_recomendacao="SECRETARIA MUNICIPAL DE EXEMPLO",
        nome_responsavel_recomendacao="FULANO DE TAL",
        prazo_cumprimento_recomendacao="60 dias",
    )
    mocker.patch("tools.etl.pipeline.extract_recomendacao", return_value=fake_result)

    with Session(in_memory_engine) as session:
        report = enqueue_recomendacao_extraction(
            ExtractionFilters(),
            extractor=MagicMock(),
            responsible_extractor=MagicMock(),
            session=session,
            rows=[_sample_recomendacao_row()],
        )

        assert report.scanned == 1
        assert report.enqueued == 1
        assert report.skipped == 0

        rows = session.execute(select(RecomendacaoStagingORM)).scalars().all()
        assert len(rows) == 1
        staged = rows[0]
        assert staged.status == ReviewStatus.pending
        assert staged.DescricaoRecomendacao == fake_result.descricao_recomendacao
        assert staged.OrgaoResponsavel == fake_result.orgao_responsavel_recomendacao
        assert staged.PrazoCumprimentoRecomendacao == "60 dias"
        assert staged.Cancelado is False
        assert staged.original_payload is not None
        assert (
            staged.original_payload["descricao_recomendacao"]
            == fake_result.descricao_recomendacao
        )


def test_enqueue_recomendacao_dedupes_same_triple(
    in_memory_engine: Engine, mocker
) -> None:
    from tools.etl.pipeline import (
        ExtractionFilters,
        enqueue_recomendacao_extraction,
    )
    from tools.etl.staging import RecomendacaoStagingORM
    from tools.schema import Recomendacao

    row = _sample_recomendacao_row()
    mocker.patch(
        "tools.etl.pipeline.extract_recomendacao",
        return_value=Recomendacao(
            descricao_recomendacao=row["descricao_recomendacao"],
            orgao_responsavel_recomendacao="X",
            nome_responsavel_recomendacao="Y",
        ),
    )

    with Session(in_memory_engine) as session:
        enqueue_recomendacao_extraction(
            ExtractionFilters(),
            extractor=MagicMock(),
            responsible_extractor=MagicMock(),
            session=session,
            rows=[row],
        )
        report2 = enqueue_recomendacao_extraction(
            ExtractionFilters(),
            extractor=MagicMock(),
            responsible_extractor=MagicMock(),
            session=session,
            rows=[row],
        )
        assert report2.enqueued == 0
        assert report2.skipped == 1

        rows = session.execute(select(RecomendacaoStagingORM)).scalars().all()
        assert len(rows) == 1
