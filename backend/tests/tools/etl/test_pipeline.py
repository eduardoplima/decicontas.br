"""Tests for ``tools.etl.pipeline``.

Happy path (one final-table row + one ``Processed*`` bridge row written) and
dedup (second call with the same NER id is skipped via the bridge). The
stage-2 extractor functions (``tools.utils.extract_obrigacao`` /
``extract_recomendacao``) are patched at the pipeline's import boundary to
avoid hitting MSSQL or the LLM.
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


def _seed_ner_obrigacao(session: Session, *, id_ner: int) -> None:
    """Insert a NERDecisao + NERObrigacao so the FK in ProcessedObrigacao is valid."""
    from tools.models import NERDecisaoORM, NERObrigacaoORM

    decisao = NERDecisaoORM(
        IdProcesso=541094,
        IdComposicaoPauta=7001,
        IdVotoPauta=9001,
        RawJson="{}",
    )
    session.add(decisao)
    session.flush()
    ner = NERObrigacaoORM(
        IdNerObrigacao=id_ner,
        IdNerDecisao=decisao.IdNerDecisao,
        Ordem=0,
        DescricaoObrigacao="ner source",
    )
    session.add(ner)
    session.commit()


def _seed_ner_recomendacao(session: Session, *, id_ner: int) -> None:
    from tools.models import NERDecisaoORM, NERRecomendacaoORM

    decisao = NERDecisaoORM(
        IdProcesso=541094,
        IdComposicaoPauta=7001,
        IdVotoPauta=9001,
        RawJson="{}",
    )
    session.add(decisao)
    session.flush()
    ner = NERRecomendacaoORM(
        IdNerRecomendacao=id_ner,
        IdNerDecisao=decisao.IdNerDecisao,
        Ordem=0,
        DescricaoRecomendacao="ner source",
    )
    session.add(ner)
    session.commit()


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


def test_enqueue_obrigacao_writes_final_and_bridge(
    in_memory_engine: Engine, mocker
) -> None:
    from tools.etl.pipeline import (
        ExtractionFilters,
        enqueue_obrigacao_extraction,
    )
    from tools.models import ObrigacaoORM, ProcessedObrigacaoORM
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
        _seed_ner_obrigacao(session, id_ner=123)
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

        finals = session.execute(select(ObrigacaoORM)).scalars().all()
        assert len(finals) == 1
        final = finals[0]
        assert final.IdProcesso == 541094
        assert final.DescricaoObrigacao == fake_result.descricao_obrigacao
        assert final.Prazo == "90 dias"
        assert final.ValorMultaCominatoria == 1000.0
        assert final.ReservadoPor is None  # no claim until a reviewer takes it

        bridges = session.execute(select(ProcessedObrigacaoORM)).scalars().all()
        assert len(bridges) == 1
        assert bridges[0].IdNerObrigacao == 123
        assert bridges[0].IdObrigacao == final.IdObrigacao


def test_enqueue_obrigacao_dedupes_via_processed_bridge(
    in_memory_engine: Engine, mocker
) -> None:
    from tools.etl.pipeline import (
        ExtractionFilters,
        enqueue_obrigacao_extraction,
    )
    from tools.models import ObrigacaoORM
    from tools.schema import Obrigacao

    mocker.patch(
        "tools.etl.pipeline.extract_obrigacao",
        return_value=Obrigacao(
            descricao_obrigacao=_sample_obrigacao_row()["descricao_obrigacao"]
        ),
    )

    row = _sample_obrigacao_row()
    with Session(in_memory_engine) as session:
        _seed_ner_obrigacao(session, id_ner=123)
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

        finals = session.execute(select(ObrigacaoORM)).scalars().all()
        assert len(finals) == 1


def test_enqueue_recomendacao_writes_final_and_bridge(
    in_memory_engine: Engine, mocker
) -> None:
    from tools.etl.pipeline import (
        ExtractionFilters,
        enqueue_recomendacao_extraction,
    )
    from tools.models import ProcessedRecomendacaoORM, RecomendacaoORM
    from tools.schema import Recomendacao

    fake_result = Recomendacao(
        descricao_recomendacao="aperfeiçoar controles internos",
        orgao_responsavel_recomendacao="SECRETARIA MUNICIPAL DE EXEMPLO",
        nome_responsavel_recomendacao="FULANO DE TAL",
        prazo_cumprimento_recomendacao="60 dias",
    )
    mocker.patch("tools.etl.pipeline.extract_recomendacao", return_value=fake_result)

    with Session(in_memory_engine) as session:
        _seed_ner_recomendacao(session, id_ner=456)
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

        finals = session.execute(select(RecomendacaoORM)).scalars().all()
        assert len(finals) == 1
        final = finals[0]
        assert final.DescricaoRecomendacao == fake_result.descricao_recomendacao
        assert final.OrgaoResponsavel == fake_result.orgao_responsavel_recomendacao
        assert final.PrazoCumprimentoRecomendacao == "60 dias"
        assert final.Cancelado is False

        bridges = session.execute(select(ProcessedRecomendacaoORM)).scalars().all()
        assert len(bridges) == 1
        assert bridges[0].IdNerRecomendacao == 456
        assert bridges[0].IdRecomendacao == final.IdRecomendacao


def test_enqueue_recomendacao_dedupes_via_processed_bridge(
    in_memory_engine: Engine, mocker
) -> None:
    from tools.etl.pipeline import (
        ExtractionFilters,
        enqueue_recomendacao_extraction,
    )
    from tools.models import RecomendacaoORM
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
        _seed_ner_recomendacao(session, id_ner=456)
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

        finals = session.execute(select(RecomendacaoORM)).scalars().all()
        assert len(finals) == 1
