"""Fixtures for tests under ``backend/tests/tools/``.

All sample text is fictional. PII is replaced by ``FULANO DE TAL`` / ``000.000.000-00``.
"""

from __future__ import annotations

import pytest

from tools.schema import (
    NERDecisao,
    NERMulta,
    NERObrigacao,
    NERRecomendacao,
    NERRessarcimento,
)


@pytest.fixture
def sample_texto_acordao() -> str:
    """A roughly 500-character fictional TCE/RN decision."""
    return (
        "Acórdão nº 0123/2024 - TCE/RN. Processo nº 0001234-56.2023. "
        "Vistos, relatados e discutidos os presentes autos, decidem os "
        "Conselheiros do Tribunal de Contas do Estado do Rio Grande do Norte, "
        "à unanimidade, em sessão plenária, julgar irregulares as contas do "
        "Sr. FULANO DE TAL, CPF 000.000.000-00, ex-prefeito municipal, e "
        "aplicar-lhe multa no valor de R$ 10.000,00, nos termos do art. 107, "
        "II, da Lei Complementar Estadual nº 464/2012, determinando ainda ao "
        "atual gestor que adote providências corretivas no prazo de 90 "
        "(noventa) dias, sob pena de multa cominatória diária."
    )


@pytest.fixture
def sample_ner_decisao() -> NERDecisao:
    """A ``NERDecisao`` with one entity of each type populated."""
    return NERDecisao(
        multas=[
            NERMulta(
                descricao_multa=(
                    "Multa no valor de R$ 10.000,00 aplicada ao responsável "
                    "nos termos do art. 107, II, da LCE nº 464/2012."
                )
            )
        ],
        obrigacoes=[
            NERObrigacao(
                descricao_obrigacao=(
                    "Determinar ao atual gestor que adote providências "
                    "corretivas no prazo de 90 (noventa) dias, sob pena de "
                    "multa cominatória diária."
                )
            )
        ],
        ressarcimentos=[
            NERRessarcimento(
                descricao_ressarcimento=(
                    "Ressarcimento ao erário no valor de R$ 5.000,00 referente "
                    "a despesas irregulares apuradas na auditoria."
                )
            )
        ],
        recomendacoes=[
            NERRecomendacao(
                descricao_recomendacao=(
                    "Recomenda-se à unidade o aperfeiçoamento dos controles "
                    "internos de execução orçamentária."
                )
            )
        ],
    )
