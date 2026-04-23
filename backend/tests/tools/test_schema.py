"""Characterization tests for Pydantic models in ``tools.schema``."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tools.schema import (
    CitationChoice,
    Decisao,
    Multa,
    NERDecisao,
    NERMulta,
    NERObrigacao,
    NERRecomendacao,
    NERRessarcimento,
    Obrigacao,
    Recomendacao,
    ResponsibleChoice,
    Ressarcimento,
)


# ======================================================================
# NER layer — raw span-level models
# ======================================================================


class TestNERMulta:
    def test_valid(self) -> None:
        model = NERMulta(descricao_multa="MULTA no valor de R$ 500,00")
        assert model.descricao_multa.startswith("MULTA")

    def test_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            NERMulta()


class TestNERObrigacao:
    def test_valid(self) -> None:
        model = NERObrigacao(descricao_obrigacao="Determinar ao IPERN ...")
        assert model.descricao_obrigacao

    def test_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            NERObrigacao()


class TestNERRessarcimento:
    def test_valid(self) -> None:
        model = NERRessarcimento(descricao_ressarcimento="Ressarcimento ao erário ...")
        assert model.descricao_ressarcimento

    def test_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            NERRessarcimento()


class TestNERRecomendacao:
    def test_valid(self) -> None:
        model = NERRecomendacao(descricao_recomendacao="Recomenda-se à unidade ...")
        assert model.descricao_recomendacao

    def test_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            NERRecomendacao()


class TestNERDecisao:
    def test_empty_construction_uses_default_empty_lists(self) -> None:
        model = NERDecisao()
        assert model.multas == []
        assert model.obrigacoes == []
        assert model.ressarcimentos == []
        assert model.recomendacoes == []

    def test_sample_fixture_has_one_of_each(self, sample_ner_decisao: NERDecisao) -> None:
        assert len(sample_ner_decisao.multas) == 1
        assert len(sample_ner_decisao.obrigacoes) == 1
        assert len(sample_ner_decisao.ressarcimentos) == 1
        assert len(sample_ner_decisao.recomendacoes) == 1

    def test_extra_fields_ignored_by_default(self) -> None:
        """Pydantic v2 default is ``extra='ignore'`` — unknown keys drop silently."""
        model = NERDecisao.model_validate({"multas": [], "unknown_field": 42})
        assert "unknown_field" not in model.model_dump()


# ======================================================================
# Enriched layer — second-pass structured records
# ======================================================================


class TestMulta:
    def test_valid_minimal(self) -> None:
        model = Multa(descricao_multa="MULTA ao Sr. FULANO DE TAL")
        assert model.valor_fixo is None
        assert model.percentual is None
        assert model.e_multa_solidaria is False

    def test_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            Multa()


class TestObrigacao:
    def test_valid_minimal(self) -> None:
        model = Obrigacao(descricao_obrigacao="Determinar ao IPERN ...")
        assert model.de_fazer is True
        assert model.tem_multa_cominatoria is False

    def test_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            Obrigacao()

    def test_periodo_multa_cominatoria_rejects_unknown_value(self) -> None:
        """``periodo_multa_cominatoria`` is a Literal — values outside the set fail."""
        with pytest.raises(ValidationError):
            Obrigacao(
                descricao_obrigacao="...",
                periodo_multa_cominatoria="anual",
            )


class TestRessarcimento:
    def test_valid_empty(self) -> None:
        """All fields on ``Ressarcimento`` are Optional — empty is valid."""
        model = Ressarcimento()
        assert model.descricao_ressarcimento is None


class TestRecomendacao:
    def test_valid_empty(self) -> None:
        """All fields on ``Recomendacao`` are Optional — empty is valid."""
        model = Recomendacao()
        assert model.descricao_recomendacao is None


class TestDecisao:
    def test_none_lists_coerced_to_empty(self) -> None:
        """``field_validator convert_none_to_empty_list`` rewrites None → []."""
        model = Decisao(
            multas=None, obrigacoes=None, ressarcimentos=None, recomendacoes=None
        )
        assert model.multas == []
        assert model.obrigacoes == []
        assert model.ressarcimentos == []
        assert model.recomendacoes == []

    def test_valid_with_entries(self) -> None:
        model = Decisao(
            multas=[Multa(descricao_multa="...")],
            obrigacoes=[],
            ressarcimentos=[],
            recomendacoes=[],
        )
        assert len(model.multas) == 1


# ======================================================================
# Helper choice models
# ======================================================================


class TestCitationChoice:
    def test_valid(self) -> None:
        model = CitationChoice(index=1, justification="Citation 1 has the deadline.")
        assert model.index == 1

    def test_invalid_index_type(self) -> None:
        with pytest.raises(ValidationError):
            CitationChoice(index="not-an-int", justification="...")


class TestResponsibleChoice:
    def test_valid(self) -> None:
        model = ResponsibleChoice(nome_responsavel="FULANO DE TAL", cargo="Prefeito")
        assert model.nome_responsavel == "FULANO DE TAL"

    def test_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            ResponsibleChoice(nome_responsavel="FULANO DE TAL")
