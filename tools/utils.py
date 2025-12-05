import os
import json
import pymssql

import pandas as pd
import numpy as np

from pprint import pprint
from datetime import datetime
from typing import List, Dict, Any, Optional
from langchain_openai import  AzureChatOpenAI, ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from dotenv import load_dotenv

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, Boolean, Text, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.schema import DDL, CheckConstraint
from sqlalchemy.engine import Engine

from tools.prompt import generate_few_shot_ner_prompts
from tools.models import (
    ObrigacaoORM, 
    RecomendacaoORM, 
    BeneficioORM, 
    NERDecisaoORM, 
    NERMultaORM, 
    NERObrigacaoORM, 
    NERRecomendacaoORM, 
    NERRessarcimentoORM,
    EstagioBeneficio,
    CaracteristicaBeneficio,
    TipoBeneficio,
    SubtipoBeneficio,
)
from tools.schema import (
    NERDecisao,
    Obrigacao,
    Recomendacao
)

def safe_int(value):
    if pd.isna(value):
        return None
    return int(value)

def get_connection(db: str = 'processo') -> Engine:
    server = os.getenv("SQL_SERVER_HOST")
    user = os.getenv("SQL_SERVER_USER")
    password = os.getenv("SQL_SERVER_PASS")
    port = os.getenv("SQL_SERVER_PORT", "1433")  # default MSSQL port
    database = db
    connection_string = f"mssql+pymssql://{user}:{password}@{server}/{database}"
    engine = create_engine(connection_string)
    return engine


def find_obrigacao_by_descricao(df_ob: pd.DataFrame, descricao: str) -> List[int]:
    return [i for i,r in df_ob.iterrows() if descricao in r['obrigacoes'][0].descricao_obrigacao][0]

def get_id_pessoa_multa_cominatoria(row, result_obrigacao) -> List[int]:
    """
    Obtém o ID da pessoa responsável pela multa cominatória.
    """
    if result_obrigacao.documento_responsavel_multa_cominatoria:
        return [p['id_pessoa'] for p in row['responsaveis'] if p['documento_responsavel'] == result_obrigacao.documento_responsavel_multa_cominatoria][0]
    return None

def get_pessoas_str(pessoas: List[Dict[str, Any]]) -> str:    
    pessoas_str = []
    for pessoa in pessoas:
        nome = pessoa.get('nome_responsavel', 'Desconhecido')
        documento = pessoa.get('documento_responsavel', 'Desconhecido')
        tipo = pessoa.get('tipo_responsavel', 'Desconhecido')
        if tipo == 'F':
            tipo = 'Física'
        elif tipo == 'J':
            tipo = 'Jurídica'
        pessoas_str.append(f"{nome} ({tipo} - {documento})")
    
    return ", ".join(pessoas_str)

# Obrigação

def get_prompt_obrigacao(row: Dict[str, Any], obrigacao: Obrigacao) -> str:
    data_sessao = row['data_sessao']
    texto_acordao = row['texto_acordao']
    orgao_responsavel = row['orgao_responsavel']
    pessoas_responsaveis = row['responsaveis']


    return f"""
    Você é um Auditor de Controle Externo do TCE/RN. Sua tarefa é analisar o voto e extrair a obrigação imposta, preenchendo os campos do objeto Obrigacao.

    Data da Sessão: {data_sessao.strftime('%d/%m/%Y')}
    Obrigação detectada: {obrigacao.descricao_obrigacao}
    Texto do Acordão: {texto_acordao}
    Órgão Responsável: {orgao_responsavel}
    Pessoas Responsáveis: {get_pessoas_str(pessoas_responsaveis)}

    Dado esse contexto, preencha os campos da seguinte forma:
    - descricao_obrigacao: Descrição da obrigação imposta.
    - tipo: Tipo da obrigação (fazer/não fazer).
    - prazo: Prazo estipulado para cumprimento. Extraia o texto indicando o prazo, se houver. Exemplo: "90 dias".
    - data_cumprimento: Extraia do prazo do acórdão como data de início e faça o cálculo da data de cumprimento. Exemplo: 2025-09-13
    - orgao_responsavel: Órgão responsável pelo cumprimento da obrigação. Pessoa jurídica.
    - tem_multa_cominatoria: Indique se há multa cominatória associada à obrigação.
    - nome_responsavel_multa_cominatoria: Nome do responsável pela obrigação, se houver multa cominatória. Pessoa física responsável.
    - documento_responsavel_multa_cominatoria: Documento do responsável pela obrigação, se houver multa cominatória.
    - valor_multa_cominatoria: Se houver multa cominatória, preencha o valor.
    - periodo_multa_cominatoria: Período da multa cominatória, se houver.
    - e_multa_cominatoria_solidaria: Indique se a multa cominatória é solidária.
    - solidarios_multa_cominatoria: Lista de responsáveis solidários da multa cominatória.

    Use somente as informações do texto do acórdão e dos dados fornecidos. Não inclua informações adicionais ou suposições.
    Se o órgão responsável não estiver disponível, preencha o campo orgão_responsavel com "Desconhecido".
    """

def extract_obrigacao(extractor: BaseChatModel, row: Dict[str, Any], obrigacao: Obrigacao) -> Obrigacao:
    prompt_obrigacao = get_prompt_obrigacao(row, obrigacao)
    return extractor.invoke(prompt_obrigacao)

def insert_obrigacao(db_session, obrigacao: Obrigacao, row: Dict[str, Any]):
    orm_obj = ObrigacaoORM(
        IdProcesso=safe_int(row['id_processo']),
        IdComposicaoPauta=safe_int(row['id_composicao_pauta']),
        IdVotoPauta=safe_int(row['id_voto_pauta']),
        DescricaoObrigacao=obrigacao.descricao_obrigacao,
        DeFazer=obrigacao.de_fazer,
        Prazo=obrigacao.prazo,
        DataCumprimento=obrigacao.data_cumprimento,
        OrgaoResponsavel=obrigacao.orgao_responsavel,
        IdOrgaoResponsavel=safe_int(row['id_orgao_responsavel']),
        TemMultaCominatoria=obrigacao.tem_multa_cominatoria,
        NomeResponsavelMultaCominatoria=obrigacao.nome_responsavel_multa_cominatoria,
        DocumentoResponsavelMultaCominatoria=obrigacao.documento_responsavel_multa_cominatoria,
        IdPessoaMultaCominatoria=get_id_pessoa_multa_cominatoria(row, obrigacao),
        ValorMultaCominatoria=obrigacao.valor_multa_cominatoria,
        PeriodoMultaCominatoria=obrigacao.periodo_multa_cominatoria,
        EMultaCominatoriaSolidaria=obrigacao.e_multa_cominatoria_solidaria,
        SolidariosMultaCominatoria=obrigacao.solidarios_multa_cominatoria
    )
    db_session.add(orm_obj)
    db_session.commit()
    return orm_obj

# Recomendação

def get_prompt_recomendacao(row, recomendacao):
    data_sessao = row['datasessao']
    texto_acordao = row['texto_acordao']
    orgao_responsavel = row['orgao_responsavel']
    pessoas_responsaveis = row['responsaveis']


    return f"""
    Você é um Auditor de Controle Externo do TCE/RN. Sua tarefa é analisar o voto e extrair a recomendação feita, preenchendo os campos do objeto Recomendacao.

    Data da Sessão: {data_sessao.strftime('%d/%m/%Y')}
    Recomendação detectada: {recomendacao}
    Texto do Acordão: {texto_acordao}
    Órgão Responsável: {orgao_responsavel}
    Pessoas Responsáveis: {get_pessoas_str(pessoas_responsaveis)}

    Dado esse contexto, preencha os campos da seguinte forma:
    - descricao_recomendacao: Descrição da recomendação feita.
    - prazo_cumprimento_recomendacao: Prazo estipulado para cumprimento. Extraia o texto indicando o prazo, se houver. Exemplo: "90 dias".
    - data_cumprimento_recomendacao: Extraia do prazo do acórdão como data de início e faça o cálculo da data de cumprimento. Exemplo: 2025-09-13
    - orgao_responsavel_recomendacao: Órgão responsável pelo cumprimento da recomendação. Pessoa jurídica.
    - nome_responsavel_recomendacao: Nome do responsável pela recomendação. Pessoa física responsável.

    Use somente as informações do texto do acórdão e dos dados fornecidos. Não inclua informações adicionais ou suposições.
    Se o órgão responsável não estiver disponível, preencha o campo orgão_responsavel com "Desconhecido".
    """

def extract_recomendacao(row, recomendacao, extractor):
    prompt_recomendacao = get_prompt_recomendacao(row, recomendacao)
    return extractor.invoke(prompt_recomendacao)

def insert_recomendacao(db_session, recomendacao: Recomendacao, row):
    orm_obj = RecomendacaoORM(
        IdProcesso=safe_int(row['idprocesso']),
        IdComposicaoPauta=safe_int(row['idcomposicaopauta']),
        IdVotoPauta=safe_int(row['idvotopauta']),
        DescricaoRecomendacao=recomendacao.descricao_recomendacao,
        PrazoCumprimentoRecomendacao=recomendacao.prazo_cumprimento_recomendacao,
        DataCumprimentoRecomendacao=recomendacao.data_cumprimento_recomendacao,
        OrgaoResponsavel=recomendacao.orgao_responsavel_recomendacao,
        IdOrgaoResponsavel=safe_int(row['id_orgao_responsavel']),
        NomeResponsavel=recomendacao.nome_responsavel_recomendacao
    )
    db_session.add(orm_obj)
    db_session.commit()
    return orm_obj

# NER

def get_decisions_by_year_and_months(ano: int, meses: List[int]):
    sql_dec = open("sql/decisions_by_year_months.sql", "r").read()
    return pd.read_sql_query(sql_dec.format(ano=ano, meses=",".join([str(m) for m in meses])), get_connection(os.getenv("SQL_SERVER_DB_PROCESSOS")))

def get_decisions_by_process(process_list: List[str]):
    sql_dec = open("sql/decisions_by_processes.sql", "r").read()
    return pd.read_sql_query(sql_dec.format(processes=",".join([f"'{m}'" for m in process_list])), get_connection(os.getenv("SQL_SERVER_DB_PROCESSOS")))

def get_ner_decision(extractor: BaseChatModel, texto_acordao: str) -> Dict[str, Any]:
    prompt_with_few_shot = generate_few_shot_ner_prompts(texto_acordao)
    return extractor.invoke(prompt_with_few_shot)

def get_existing_ner_decision(
    session: Session,
    process_id: int,
    composition_id: int,
    vote_id: int,
) -> Optional[NERDecisaoORM]:
    return (
        session.query(NERDecisaoORM)
        .filter(
            NERDecisaoORM.IdProcesso == process_id,
            NERDecisaoORM.IdComposicaoPauta == composition_id,
            NERDecisaoORM.IdVotoPauta == vote_id,
        )
        .one_or_none()
    )

def save_ner_decision(
    session: Session,
    process_id: int,
    composition_id: int,
    vote_id: int,
    ner_decision: NERDecisao,  # your Pydantic model
    model_name: Optional[str] = None,
    prompt_version: Optional[str] = None,
    run_id: Optional[str] = None,
) -> int:
    db_decision = NERDecisaoORM(
        IdProcesso=process_id,
        IdComposicaoPauta=composition_id,
        IdVotoPauta=vote_id,
        Modelo=model_name,
        VersaoPrompt=prompt_version,
        RunId=run_id,
        RawJson=ner_decision.model_dump_json(),
    )

    # Multas
    for idx, multa in enumerate(ner_decision.multas):
        db_decision.multas.append(
            NERMultaORM(
                Ordem=idx,
                DescricaoMulta=multa.descricao_multa,
            )
        )

    # Ressarcimentos
    for idx, ressarcimento in enumerate(ner_decision.ressarcimentos):
        db_decision.ressarcimentos.append(
            NERRessarcimentoORM(
                Ordem=idx,
                DescricaoRessarcimento=ressarcimento.descricao_ressarcimento,
            )
        )

    # Obrigações
    for idx, obrigacao in enumerate(ner_decision.obrigacoes):
        db_decision.obrigacoes.append(
            NERObrigacaoORM(
                Ordem=idx,
                DescricaoObrigacao=obrigacao.descricao_obrigacao,
            )
        )

    # Recomendações
    for idx, recomendacao in enumerate(ner_decision.recomendacoes):
        db_decision.recomendacoes.append(
            NERRecomendacaoORM(
                Ordem=idx,
                DescricaoRecomendacao=recomendacao.descricao_recomendacao,
            )
        )

    session.add(db_decision)
    session.commit()

    return db_decision.IdNerDecisao

import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def process_decision_row(
    session: Session,
    row,
    extractor: BaseChatModel,
    model_name: str,
    prompt_version: str,
    run_id: str | None = None,
    overwrite: bool = False,
) -> int | None:
    """
    Process a single decision row:
    - Check if a NERDecisao already exists for (IdProcesso, IdComposicaoPauta, IdVotoPauta).
    - If exists and overwrite=False, skip.
    - If overwrite=True, delete the old one and re-run extraction.
    - If not exists, run LLM extraction and save.

    Returns:
        IdNerDecisao or None if skipped.
    """

    process_id = int(row.id_processo)
    composition_id = int(row.id_composicao_pauta)
    vote_id = int(row.id_voto_pauta)

    # 1. Check for existing NER decision
    existing = get_existing_ner_decision(
        session=session,
        process_id=process_id,
        composition_id=composition_id,
        vote_id=vote_id,
    )

    if existing and not overwrite:
        logger.info(
            "Skipping NER extraction for process=%s, composition=%s, vote=%s "
            "because an entry already exists (IdNerDecisao=%s).",
            process_id, composition_id, vote_id, existing.IdNerDecisao,
        )
        return existing.IdNerDecisao

    if existing and overwrite:
        logger.info(
            "Overwriting existing NERDecisao %s for process=%s, composition=%s, vote=%s.",
            existing.IdNerDecisao, process_id, composition_id, vote_id,
        )
        session.delete(existing)
        session.commit()

    # 2. Run NER extraction with GPT-4 Turbo (your current logic)
    decision_text = row.texto_acordao  # adapt to the real column name
    ner_decision = get_ner_decision(extractor, decision_text)

    # 3. Save to SQL Server
    ner_id = save_ner_decision(
        session=session,
        process_id=process_id,
        composition_id=composition_id,
        vote_id=vote_id,
        ner_decision=ner_decision,
        model_name=model_name,
        prompt_version=prompt_version,
        run_id=run_id,
    )

    logger.info(
        "Saved NERDecisao IdNerDecisao=%s for process=%s, composition=%s, vote=%s.",
        ner_id, process_id, composition_id, vote_id,
    )

    return ner_id

def run_ner_pipeline_for_dataframe(df, extractor: BaseChatModel, model_name: str, prompt_version: str, run_id: str | None = None):
    engine = get_connection(os.getenv("SQL_SERVER_DB_DECISOES"))
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        for _, row in df.iterrows():
            process_decision_row(
                session=session,
                row=row,
                extractor=extractor,
                model_name=model_name,
                prompt_version=prompt_version,
                run_id=run_id,
                overwrite=False,  # set to True if you want to reprocess
            )
    finally:
        session.close()

