from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Subdominio(str, Enum):
    LEGISLACAO = "legislacao"
    DECISOES_JUDICIAIS = "decisoes_judiciais"
    CONTRATOS = "contratos"
    REGULACAO_COMPLIANCE = "regulacao_compliance"
    TRIBUNAIS_ADMINISTRATIVOS = "tribunais_administrativos"
    TRIBUTARIO = "tributario"
    CRIMINAL = "criminal"
    OUTROS = "outros"


class TarefaPrincipal(str, Enum):
    NER = "ner"
    EXTRACAO_RELACOES = "extracao_relacoes"
    CLASSIFICACAO = "classificacao"
    SUMARIZACAO = "sumarizacao"
    GRAFO_CONHECIMENTO = "grafo_conhecimento"
    PIPELINE_COMPLETO = "pipeline_completo"
    OUTROS = "outros"


class TecnicaPrincipal(str, Enum):
    REGRAS = "regras"
    CRF = "crf"
    BILSTM_CRF = "bilstm_crf"
    TRANSFORMER_GENERICO = "transformer_generico"
    TRANSFORMER_DOMINIO = "transformer_dominio"
    LLM_ZERO_SHOT = "llm_zero_shot"
    LLM_FEW_SHOT = "llm_few_shot"
    HIBRIDO = "hibrido"


class EsquemaAnotacao(str, Enum):
    BIO_IOB = "bio_iob"
    SPAN_BASED = "span_based"
    JSON_INDICES = "json_indices"
    XML = "xml"
    ONTOLOGICO = "ontologico"
    OUTROS = "outros"
    NAO_REPORTADO = "nao_reportado"


class MetricaTipo(str, Enum):
    MACRO = "macro"
    MICRO = "micro"
    WEIGHTED = "weighted"
    NAO_REPORTADO = "nao_reportado"


class ArtigoExtraido(BaseModel):
    """Dados extraídos de um artigo do mapeamento sistemático."""

    referencia_curta: str = Field(
        ...,
        description="Citação curta no formato 'Sobrenome et al. (Ano)' ou 'Sobrenome (Ano)'.",
    )
    titulo: str = Field(..., description="Título completo do artigo.")
    autores: List[str] = Field(
        ..., description="Lista de autores no formato 'Sobrenome, Nome'."
    )
    ano: int = Field(..., description="Ano de publicação.")
    venue: Optional[str] = Field(None, description="Conferência ou periódico.")
    pais_corpus: Optional[str] = Field(
        None,
        description="País de origem do corpus utilizado, se identificável.",
    )
    idioma_corpus: Optional[str] = Field(
        None,
        description="Idioma do corpus em código ISO 639-1 (e.g., 'pt', 'en', 'de', 'zh').",
    )
    subdominio: Subdominio = Field(
        ..., description="Subdomínio jurídico tratado pelo artigo."
    )
    tarefa_principal: TarefaPrincipal = Field(
        ..., description="Principal tarefa de PLN abordada."
    )
    tecnica_principal: TecnicaPrincipal = Field(
        ..., description="Principal família de técnica utilizada."
    )
    modelos_usados: List[str] = Field(
        default_factory=list,
        description="Modelos específicos avaliados, e.g. ['BERT', 'RoBERTa', 'GPT-4'].",
    )
    entidades_anotadas: List[str] = Field(
        default_factory=list,
        description="Tipos de entidades anotadas no esquema do artigo.",
    )
    num_classes_entidade: Optional[int] = Field(
        None,
        description="Número total de classes de entidades, se reportado.",
    )
    esquema_anotacao: EsquemaAnotacao = Field(
        EsquemaAnotacao.NAO_REPORTADO,
        description="Esquema de anotação utilizado.",
    )
    corpus_publico: Optional[bool] = Field(
        None,
        description="True se o corpus é publicamente disponível, False se privado, None se não claro.",
    )
    f1_melhor_reportado: Optional[float] = Field(
        None,
        description="Melhor F1 reportado no artigo, em percentual (0-100). None se não reportado.",
    )
    metrica_tipo: MetricaTipo = Field(
        MetricaTipo.NAO_REPORTADO,
        description="Tipo de média da métrica F1.",
    )
    compara_llm_supervisionado: bool = Field(
        False,
        description="True se o artigo compara explicitamente LLMs com modelos supervisionados.",
    )
    contribuicao_principal: str = Field(
        ...,
        description="Resumo em 1-2 frases da contribuição principal do artigo.",
    )
    citacao_relevante_para_tce: Optional[str] = Field(
        None,
        description=(
            "Trecho ou observação de até 200 caracteres que torna o artigo "
            "relevante para o domínio de Tribunais de Contas. None se não houver."
        ),
    )
    confianca_extracao: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Confiança autoavaliada da extração, considerando cobertura do PDF "
            "e clareza das informações."
        ),
    )
