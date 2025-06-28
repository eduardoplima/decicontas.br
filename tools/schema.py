from typing import Literal, List
from pydantic import BaseModel, Field, field_validator
from datetime import date

# ====================
# Modelos de Entidades Nomeada
# ====================

# Recriar as entidades por label e pegar somente descrição
# fazer o span depois

class NERMultaFixa(BaseModel):
    descricao_multafixa: str = Field(..., description="Descrição da multa de valor fixa aplicada em decisão do TCE/RN.")

class NERMultaPercentual(BaseModel):
    descricao_multapercentual: str = Field(..., description="Descrição da multa percentual aplicada sobre o dano.")

class NERObrigacaoMulta(BaseModel):
    descricao_obrigacaomulta: str = Field(..., description="Descrição da obrigação sujeita à multa cominatória aplicada em decisão do TCE/RN.")

class NERRessarcimento(BaseModel):
    descricao_ressarcimento: str = Field(..., description="Descrição do dano que gerou o ressarcimento imposto ao responsável.")

class NERObrigacao(BaseModel):
    descricao_obrigacao: str = Field(..., description="Descrição da obrigação de fazer ou não fazer imposta em decisão do TCE/RN.")

class NERRecomendacao(BaseModel):
    descricao_recomendacao: str = Field(..., description="Descrição da recomendação proferida em decisão do TCE/RN.")

# ====================
# Modelo de Entidade Nomeada para decisão
# ====================

class NERDecisao(BaseModel):
    """
    Entidade Nomeada que agrupa todas as entidades extraídas de uma decisão do TCE/RN.
    Contém listas de entidades nomeadas para cada tipo de informação extraída.
    """
    multas_fixas: List[NERMultaFixa] = Field(default_factory=list, description="Lista de multas fixas aplicadas.")
    multas_percentuais: List[NERMultaPercentual] = Field(default_factory=list, description="Lista de multas percentuais sobre ressarcimento.")
    obrigacoes_multa: List[NERObrigacaoMulta] = Field(default_factory=list, description="Lista de multas cominatórias aplicadas.")
    ressarcimentos: List[NERRessarcimento] = Field(default_factory=list, description="Lista de ressarcimentos imputados.")
    obrigacoes: List[NERObrigacao] = Field(default_factory=list, description="Lista de obrigações de fazer ou não fazer impostas.")
    recomendacoes: List[NERRecomendacao] = Field(default_factory=list, description="Lista de recomendações proferidas sem força vinculante.")


# ====================
# Modelos de entidades para informações estruturadas
# ====================

class MultaFixa(BaseModel):
    """
    Representa multa de valor fixo aplicada em decisão do TCE/RN.
    """
    descricao_multafixa: str | None = Field(default=None, description="Descrição da multa aplicada.")
    valor_original_multafixa: float | None = Field(default=None, description="Valor original da multa fixada.")
    nome_responsavel_multafixa: str | None = Field(default=None, description="Nome do responsável pela multa.")


class MultaPercentual(BaseModel):
    """
    Representa multa calculada como percentual sobre o dano.
    """
    descricao_multapercentual: str | None = Field(default=None, description="Descrição da multa percentual aplicada.")
    percentual_multapercentual: float | None = Field(default=None, description="Percentual aplicado sobre o dano.")
    base_calculo_multapercentual: float | None = Field(default=None, description="Valor base sobre o qual o percentual foi aplicado.")
    # devedor? melhorar o texto da descrição
    nome_responsavel_multapercentual: str | None = Field(default=None, description="Nome do responsável pela multa.")
    e_multa_solidaria_multapercentual: bool | None = Field(default=False, description="Indica se a multa é solidária.")
    solidarios_multapercentual: list[str] | None = Field(default=None, description="Lista de responsáveis solidários pela multa percentual.")


class ObrigacaoMulta(BaseModel):
    """
    Representa multa cominatória aplicada em obrigação de fazer/não fazer.
    """
    descricao_obrigacaomulta: str | None = Field(default=None, description="Descrição da obrigação sujeita à multa cominatória.")
    valor_obrigacaomulta: float | None = Field(default=None, description="Valor diário da multa.")
    periodo_obrigacaomulta: Literal["diário", "semanal", "mensal"] | None = Field(default=None, description="Período de incidência da multa (diário, semanal ou mensal).")
    prazo_obrigacaomulta: str | None = Field(default=None, description="Descrição do prazo para incidência da multa.")
    data_cumprimento_obrigacaomulta: date | None = Field(default=None, description="Data de eventual cumprimento da obrigação.")
    nome_responsavel_obrigacaomulta: str | None = Field(default=None, description="Nome do responsável pela obrigação sujeita à multa.")
    orgao_responsavel_obrigacaomulta: str | None = Field(default=None, description="Órgão responsável pela obrigação sujeita à multa.")


class Ressarcimento(BaseModel):
    """
    Representa ressarcimento imposto ao responsável.
    """
    descricao_ressarcimento: str | None = Field(default=None, description="Descrição do dano que gerou o ressarcimento.")
    valor_dano_ressarcimento: float | None = Field(default=None, description="Valor integral do dano apurado.")
    percentual_imputado_ressarcimento: float | None = Field(default=None, description="Percentual de responsabilidade atribuída ao agente.")
    valor_imputado_ressarcimento: float | None = Field(default=None, description="Valor efetivamente imputado ao responsável.")
    responsavel_ressarcimento: str | None = Field(default=None, description="Nome do responsável pelo ressarcimento.")

class Obrigacao(BaseModel):
    """
    Representa obrigações de fazer ou não fazer impostas.
    """
    descricao_obrigacao: str | None = Field(default=None, description="Descrição da obrigação.")
    tipo_obrigacao: Literal["fazer", "não fazer"] | None = Field(default=None, description="Tipo da obrigação.")
    prazo_cumprimento_obrigacao: str | None = Field(default=None, description="Prazo estipulado para cumprimento.")
    data_cumprimento_obrigacao: date | None = Field(default=None, description="Data de cumprimento efetivo.")
    nome_responsavel_obrigacaomulta: str | None = Field(default=None, description="Nome do responsável pela obrigação.")
    orgao_responsavel_obrigacaomulta: str | None = Field(default=None, description="Órgão responsável pela obrigação.")


class Recomendacao(BaseModel):
    """
    Representa recomendações proferidas sem força obrigatória.
    """
    descricao_recomendacao: str | None = Field(default=None, description="Descrição da recomendação.")
    prazo_cumprimento_recomendacao: str | None = Field(default=None, description="Prazo sugerido para adoção da recomendação.")
    data_cumprimento_recomendacao: date | None = Field(default=None, description="Data de eventual cumprimento.")
    nome_responsavel_recomendacao: str | None = Field(default=None, description="Nome do responsável pela recomendação.")
    orgao_responsavel_recomendacao: str | None = Field(default=None, description="Órgão responsável pela recomendação.")
    

# ==========================
# Modelo principal de agrupamento
# ==========================

class Decisao(BaseModel):
    """
    Entidades extraídas das decisões do TCE/RN.
    Se não houver entidade extraída, as listas estarão vazias.
    """

    multas_fixas: list[MultaFixa] | None = Field(default=None, description="Multas fixas aplicadas.")
    multas_percentuais: list[MultaPercentual] | None = Field(default=None, description="Multas percentuais sobre ressarcimento.")
    obrigacoes_multa: list[ObrigacaoMulta] | None = Field(default=None, description="Multas cominatórias aplicadas.")
    ressarcimentos: list[Ressarcimento] | None = Field(default=None, description="Ressarcimentos imputados.")
    obrigacoes: list[Obrigacao] | None = Field(default=None, description="Obrigações de fazer ou não fazer.")
    recomendacoes: list[Recomendacao] | None = Field(default=None, description="Recomendações sem força vinculante.")

    @field_validator("multas_fixas", "multas_percentuais", "obrigacoes_multa", "ressarcimentos", "obrigacoes", "recomendacoes")
    def convert_none_to_empty_list(cls, value):
        if value is None:
            return []
        return value
