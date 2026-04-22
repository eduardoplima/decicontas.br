import os
import unicodedata
import asyncio
import json
import logging

import pandas as pd

from datetime import datetime, date
from typing import List, Dict, Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from rapidfuzz import process, fuzz

from sqlalchemy import (
    create_engine,
    select
)
from sqlalchemy.orm import sessionmaker, Session
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
    ProcessedObrigacaoORM,
    ProcessedRecomendacaoORM
)
from tools.schema import (
    NERDecisao,
    Obrigacao,
    Recomendacao,
    CitationChoice,
    ResponsibleChoice
)

from dotenv import load_dotenv
 
load_dotenv()

DB_PROCESSOS = os.getenv("SQL_SERVER_DB_PROCESSOS", "processo")
DB_DECISOES = os.getenv("SQL_SERVER_DB_DECISOES", "BdDIP")
DB_SIAI = os.getenv("SQL_SERVER_DB_SIAI", "BdSIAI")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQL_DIR = os.path.join(BASE_DIR, "..", "sql")

def safe_int(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    # pandas às vezes traz 123.0 (float) e strings "123.0"
    if isinstance(value, str):
        v = value.strip()
        if v == "":
            return None
        try:
            # tenta int direto
            return int(v)
        except ValueError:
            try:
                return int(float(v))
            except ValueError:
                return None

    if isinstance(value, float):
        if value != value:  # NaN guard
            return None
        return int(value)

    try:
        return int(value)
    except Exception:
        return None
    
def get_connection(db: str = 'processo') -> Engine:
    server = os.getenv("SQL_SERVER_HOST")
    user = os.getenv("SQL_SERVER_USER")
    password = os.getenv("SQL_SERVER_PASS")
    port = os.getenv("SQL_SERVER_PORT", "1433")  # default MSSQL port
    database = db
    connection_string = f"mssql+pymssql://{user}:{password}@{server}/{database}"
    engine = create_engine(connection_string)
    return engine

def get_session(db: str = 'processo') -> Session:
    engine = get_connection(db)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def find_obrigacao_by_descricao(df_ob: pd.DataFrame, descricao: str) -> List[int]:
    return [i for i,r in df_ob.iterrows() if descricao in r['obrigacoes'][0].descricao_obrigacao][0]

def get_id_pessoa_multa_cominatoria(row, result_obrigacao) -> List[int]:
    """
    Obtém o ID da pessoa responsável pela multa cominatória.
    """
    if result_obrigacao.documento_responsavel_multa_cominatoria:
        try:
            return [p['id_pessoa'] for p in row['responsaveis'] if p['documento_responsavel'] == result_obrigacao.documento_responsavel_multa_cominatoria][0]
        except:
            return None
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


def _session_date_iso(raw_session_date) -> str:
    if isinstance(raw_session_date, str):
        try:
            dt = datetime.fromisoformat(raw_session_date)
        except ValueError:
            dt = datetime.strptime(raw_session_date, "%Y-%m-%d")
        return dt.date().isoformat()
    if hasattr(raw_session_date, "date"):
        return raw_session_date.date().isoformat()
    return raw_session_date.isoformat()


def _prepare_extraction_context(
    row: Dict[str, Any] | Any,
    extractor_responsible: BaseChatModel,
):
    if not isinstance(row, dict):
        row = row.to_dict()
    session_date_str = _session_date_iso(row["data_sessao"])
    responsible = get_responsible_unit(
        extractor_responsible,
        unit=row.get("orgao_responsavel", ""),
        session_date=session_date_str,
    )
    citacao = get_deadline_from_citations(
        process_number=row["processo"],
        session_date=session_date_str,
        responsible=responsible.nome_responsavel,
        extractor=extractor_responsible,
    )
    return row, responsible, citacao


# Obrigação

def get_prompt_obrigacao(
    row: Dict[str, Any],
    obrigacao: Obrigacao,
    citacao: dict | None = None,
    responsavel: ResponsibleChoice | None = None,
) -> str:
    data_sessao = row["data_sessao"]      # datetime/date
    texto_acordao = row["texto_acordao"]
    orgao_responsavel = row["orgao_responsavel"]
    pessoas_responsaveis = row["responsaveis"]



    return f"""
    Você é um Auditor de Controle Externo do TCE/RN. Sua tarefa é analisar o voto e extrair a obrigação imposta, preenchendo os campos do objeto Obrigacao.

    Dados do contexto:
    - Data da Sessão: {data_sessao.strftime('%d/%m/%Y')}
    - Obrigação detectada: {obrigacao.descricao_obrigacao}
    - Órgão Responsável (se conhecido): {orgao_responsavel}
    - Pessoas Responsáveis (se conhecidas): {get_pessoas_str(pessoas_responsaveis)}

    - Responsável sugerido: {responsavel.nome_responsavel if responsavel else 'N/A'
    } ({responsavel.cargo if responsavel else 'N/A'})
    - Citação sugerida para prazo: {str(citacao)}

    Texto do Acordão:
    {texto_acordao}
    

    Dado esse contexto, preencha os campos da seguinte forma:

    - descricao_obrigacao: Descrição da obrigação imposta.
    - de_fazer: Verdadeiro se for uma obrigação de fazer, falso se for de não fazer.
    - prazo: Prazo estipulado para cumprimento. Priorize o texto do acórdão; se ele for omisso,
      você pode utilizar como referência o prazo sugerido nas informações adicionais de prazo.
    - data_cumprimento: Data de cumprimento no formato YYYY-MM-DD. Se o acórdão não trouxer
      uma data clara, utilize a data de cumprimento sugerida nas informações adicionais.
    - orgao_responsavel: Órgão responsável pelo cumprimento da obrigação. Pessoa jurídica.
      Se não for possível identificar, preencha com "Desconhecido".
    - tem_multa_cominatoria: Indique se há multa cominatória associada à obrigação.
    - nome_responsavel_multa_cominatoria: Nome do responsável pela obrigação, se houver multa cominatória.
    - documento_responsavel_multa_cominatoria: Documento do responsável pela obrigação, se houver multa cominatória.
    - valor_multa_cominatoria: Se houver multa cominatória, preencha o valor.
    - periodo_multa_cominatoria: Período da multa cominatória, se houver (horário, diário, semanal, mensal).
    - e_multa_cominatoria_solidaria: Indique se a multa cominatória é solidária.
    - solidarios_multa_cominatoria: Lista de responsáveis solidários da multa cominatória.

    Use somente as informações do texto do acórdão, dos dados fornecidos e das informações adicionais de prazo.
    Não inclua suposições.
    """

def extract_obrigacao(
    extractor: BaseChatModel,
    extractor_responsible: BaseChatModel,
    row: Dict[str, Any] | Any,
    obrigacao_rascunho: Obrigacao,
) -> Obrigacao:
    row, responsible, citacao = _prepare_extraction_context(row, extractor_responsible)
    prompt = get_prompt_obrigacao(
        row=row,
        obrigacao=obrigacao_rascunho,
        citacao=citacao,
        responsavel=responsible,
    )
    return extractor.invoke(prompt)


def insert_obrigacao(db_session, obrigacao: Obrigacao, row):
    # 0) Recupera IdNerObrigacao do dataframe (obrigatório)
    id_ner_obrigacao = safe_int(
        row.get("id_ner_obrigacao")
        or row.get("IdNerObrigacao")
        or row.get("idnerobrigacao")
    )
    if not id_ner_obrigacao:
        raise ValueError("row não contém id_ner_obrigacao / IdNerObrigacao (necessário para gravar ObrigacaoProcessada).")

    # 1) Se já processada, não insere nada (idempotência)
    ja_processada = db_session.execute(
        select(ProcessedObrigacaoORM.IdObrigacaoProcessada)
        .where(ProcessedObrigacaoORM.IdNerObrigacao == id_ner_obrigacao)
    ).first()
    if ja_processada:
        return None  # ou retorne o que fizer sentido no seu pipeline

    # 2) Insere a obrigação “estruturada” (tabela final)
    orm_obj = ObrigacaoORM(
        IdProcesso=safe_int(row["id_processo"]),
        IdComposicaoPauta=safe_int(row.get("id_composicao_pauta")),
        IdVotoPauta=safe_int(row.get("id_voto_pauta")),
        DescricaoObrigacao=obrigacao.descricao_obrigacao,
        DeFazer=obrigacao.de_fazer,
        Prazo=obrigacao.prazo,
        DataCumprimento=obrigacao.data_cumprimento,
        OrgaoResponsavel=obrigacao.orgao_responsavel,
        IdOrgaoResponsavel=safe_int(row.get("id_orgao_responsavel")),
        TemMultaCominatoria=obrigacao.tem_multa_cominatoria,
        NomeResponsavelMultaCominatoria=obrigacao.nome_responsavel_multa_cominatoria,
        DocumentoResponsavelMultaCominatoria=obrigacao.documento_responsavel_multa_cominatoria,
        IdPessoaMultaCominatoria=get_id_pessoa_multa_cominatoria(row, obrigacao),
        ValorMultaCominatoria=obrigacao.valor_multa_cominatoria,
        PeriodoMultaCominatoria=obrigacao.periodo_multa_cominatoria,
        EMultaCominatoriaSolidaria=obrigacao.e_multa_cominatoria_solidaria,
        SolidariosMultaCominatoria=obrigacao.solidarios_multa_cominatoria,
    )
    db_session.add(orm_obj)

    # 3) Gera IdObrigacao (IDENTITY) antes de criar ObrigacaoProcessada
    db_session.flush()  # após isto, orm_obj.IdObrigacao já está preenchido

    # 4) Marca como processada, salvando também o IdObrigacao recém-criado
    processed = ProcessedObrigacaoORM(
        IdNerObrigacao=id_ner_obrigacao,
        IdObrigacao=orm_obj.IdObrigacao,
        DataProcessamento=datetime.now(),
    )
    db_session.add(processed)

    # 5) Commit único
    db_session.commit()
    return orm_obj



# Recomendação

def get_prompt_recomendacao(
    row: Dict[str, Any],
    recomendacao: Recomendacao,
    citacao: dict | None = None,
    responsavel: ResponsibleChoice | None = None,
) -> str:
    data_sessao = row["data_sessao"]  # datetime/date
    texto_acordao = row["texto_acordao"]
    orgao_responsavel = row.get("orgao_responsavel", "")
    pessoas_responsaveis = row.get("responsaveis", [])

    return f"""
Você é um Auditor de Controle Externo do TCE/RN. Sua tarefa é analisar o voto e extrair a recomendação feita, preenchendo os campos do objeto Recomendacao.

Dados do contexto:
- Data da Sessão: {data_sessao.strftime('%d/%m/%Y')}
- Recomendação detectada: {recomendacao.descricao_recomendacao}
- Órgão Responsável (se conhecido): {orgao_responsavel}
- Pessoas Responsáveis (se conhecidas): {get_pessoas_str(pessoas_responsaveis)}

- Responsável sugerido: {responsavel.nome_responsavel if responsavel else 'N/A'} ({responsavel.cargo if responsavel else 'N/A'})
- Citação sugerida para prazo: {str(citacao)}

Texto do Acordão:
{texto_acordao}

Dado esse contexto, preencha os campos da seguinte forma:

- descricao_recomendacao: Descrição da recomendação feita.
- prazo_cumprimento_recomendacao: Prazo estipulado para cumprimento. Priorize o texto do acórdão; se ele for omisso,
  você pode utilizar como referência o prazo sugerido nas informações adicionais de prazo.
- data_cumprimento_recomendacao: Data de cumprimento no formato YYYY-MM-DD. Se o acórdão não trouxer
  uma data clara, utilize a data de cumprimento sugerida nas informações adicionais.
- orgao_responsavel_recomendacao: Órgão responsável pelo cumprimento da recomendação (pessoa jurídica).
  Se não for possível identificar, preencha com "Desconhecido".
- nome_responsavel_recomendacao: Nome do responsável pela recomendação (pessoa física).
  Se não for possível identificar, preencha com "Desconhecido".

Use somente as informações do texto do acórdão, dos dados fornecidos e das informações adicionais de prazo.
Não inclua suposições.
""".strip()


def extract_recomendacao(
    extractor: BaseChatModel,
    extractor_responsible: BaseChatModel,
    row: Dict[str, Any] | Any,
    recomendacao_rascunho: Recomendacao,
) -> Recomendacao:
    row, responsible, citacao = _prepare_extraction_context(row, extractor_responsible)
    prompt = get_prompt_recomendacao(
        row=row,
        recomendacao=recomendacao_rascunho,
        citacao=citacao,
        responsavel=responsible,
    )
    return extractor.invoke(prompt)


def insert_recomendacao(db_session, recomendacao: Recomendacao, row):
    orm_obj = RecomendacaoORM(
        IdProcesso=safe_int(row['id_processo']),
        IdComposicaoPauta=safe_int(row['id_composicao_pauta']),
        IdVotoPauta=safe_int(row['id_voto_pauta']),
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

##################
## NER Pipeline ##
##################

def _load_decisions_sql(filter_clause: str) -> str:
    sql = open(os.path.join(SQL_DIR, "decisions_base.sql")).read()
    return sql.replace("{filter_clause}", filter_clause)

def get_decisions_by_year_and_months(year: int, months: List[int]):
    sql = _load_decisions_sql("YEAR(d.DataSessao) = {ano} AND MONTH(d.DataSessao) IN ({meses})")
    return pd.read_sql_query(
        sql.format(ano=year, meses=",".join(str(m) for m in months)),
        get_connection(DB_PROCESSOS),
    )

def get_decisions_by_dates(start_date: date, end_date: date):
    sql = _load_decisions_sql("d.DataSessao BETWEEN '{start_date}' AND '{end_date}'")
    return pd.read_sql_query(
        sql.format(start_date=start_date.isoformat(), end_date=end_date.isoformat()),
        get_connection(DB_PROCESSOS),
    )

def get_decisions_by_process(process_list: List[str]):
    sql = _load_decisions_sql("CONCAT(p.Numero_Processo, '/', p.Ano_Processo) IN ({processes})")
    return pd.read_sql_query(
        sql.format(processes=",".join(f"'{m}'" for m in process_list)),
        get_connection(DB_PROCESSOS),
    )

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

    decision_text = row.texto_acordao  # adapt to the real column name
    ner_decision = get_ner_decision(extractor, decision_text)
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
    engine = get_connection(DB_DECISOES)
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
                overwrite=False,  
            )
    finally:
        session.close()


###################
# Helper Services #
###################

def normalize_text(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    s = s.strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s

def get_all_units() -> pd.DataFrame:
    sql_unidades = open(os.path.join(SQL_DIR, "units.sql")).read()
    return pd.read_sql(sql_unidades, get_connection(DB_SIAI))

def find_unit(query: str, limit=5, score_cutoff=70):
    """
    Returns the best matches of NomeUnidade for the string `query`.
    """
    df = get_all_units()
    df["NomeUnidade_norm"] = df["NomeUnidade"].apply(normalize_text)
    query_norm = normalize_text(query)
    nomes_norm = df["NomeUnidade_norm"].tolist()
    resultados = process.extract(
        query_norm,
        nomes_norm,
        scorer=fuzz.WRatio,
        limit=limit,
        score_cutoff=score_cutoff,
    )
    indices = [idx for _, _, idx in resultados]
    df_result = df.iloc[indices].copy()
    df_result["score"] = [score for _, score, _ in resultados]
    df_result = df_result.sort_values("score", ascending=False)
    return df_result[["IdUnidadeJurisdicionada", "NomeUnidade", "score"]]

def get_responsible_unit(extractor: BaseChatModel, unit: str, session_date: str) -> pd.DataFrame:
    id_unit = find_unit(unit, limit=1).iloc[0]["IdUnidadeJurisdicionada"]
    sql_resp = open(os.path.join(SQL_DIR, "responsible_unit.sql")).read()
    resp = pd.read_sql(sql_resp.format(id_unit=id_unit, session_date=session_date), get_connection(DB_SIAI)).to_dict(orient='records')

    prompt = f"""
    Você é um analista cuja tarefa é idenficar o responsável por uma unidade administrativa com base no cargo.
    Dado um conjunto de responsáveis identificados por cargos, e uma unidade administrativa, identifique o responsável adequado.

    Unidade administrativa: {unit}
    Responsáveis disponíveis:
    {json.dumps(resp, indent=2, ensure_ascii=False, default=str)}
    """
    response = extractor.invoke(prompt)
    return response

def get_citations(process: str) -> pd.DataFrame:
    sql_citacoes = open(os.path.join(SQL_DIR, "citations_by_process.sql")).read()
    return pd.read_sql(sql_citacoes.format(process=process), get_connection(DB_PROCESSOS)).to_dict(orient='records')

def get_citations_after(process: str, session_date: str) -> pd.DataFrame:
    sql_citacoes = open(os.path.join(SQL_DIR, "citations_by_process_after.sql")).read()
    return pd.read_sql(sql_citacoes.format(process=process, session_date=session_date), get_connection(DB_PROCESSOS)).to_dict(orient='records')

def filter_by_responsible(records: list[dict], responsible: str, threshold: int = 70) -> list[dict]:
    """
    Filters citation records by fuzzy-matching the 'Name' field.
    Returns only records with match score >= threshold.
    """
    if not responsible:
        return records

    results = []
    for rec in records:
        name = rec.get("nome", "")
        score = fuzz.ratio(name.lower(), responsible.lower())
        if score >= threshold:
            results.append({**rec, "match_score": score})
    return results


def _first_present(d: dict, keys: list[str]):
    for k in keys:
        if k in d and d.get(k) is not None:
            return d.get(k)
    return None

def _to_datetime_safe(x):
    """
    Converte x para datetime (python) ou retorna None se inválido/NaT.
    Aceita: str, datetime, date, pandas Timestamp.
    """
    if x is None:
        return None

    # pandas NaT
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass

    # já é datetime
    if isinstance(x, datetime):
        return x

    # pandas Timestamp
    if isinstance(x, pd.Timestamp):
        if pd.isna(x):
            return None
        return x.to_pydatetime()

    # string/qualquer coisa parseável
    dt = pd.to_datetime(x, errors="coerce")
    if pd.isna(dt):
        return None
    return dt.to_pydatetime()


def get_deadline_from_citations(
    process_number: str,
    session_date: str,
    responsible: str,
    extractor: BaseChatModel,
) -> dict:
    records = get_citations_after(process_number, session_date)

    if not records:
        return {
            "deadline_text": None,
            "deadline_date": None,
            "chosen_citation": None,
            "justification": "No citation records found."
        }

    filtered = filter_by_responsible(records, responsible)

    if not filtered:
        return {
            "deadline_text": None,
            "deadline_date": None,
            "chosen_citation": None,
            "justification": f"No citation matched responsible '{responsible}'."
        }

    lines = []
    for i, r in enumerate(filtered):
        lines.append(
            f"{i}: CitationNumber={r.get('Numero_Citacao')}/{r.get('Ano_citacao')}, "
            f"Organ={r.get('Orgao')}, Name={r.get('Nome')}, "
            f"StartCountDate={r.get('DataInicioContagem') or r.get('data_inicio_contagem')}, "
            f"FinalResponseDate={r.get('DataFinalResposta') or r.get('data_final_resposta')}"
        )
    citations_text = "\n".join(lines)

    prompt = f"""
Você é um auditor que precisa escolher qual citação é a base para o prazo
de resposta do processo {process_number}.

Data da sessão do acórdão: {session_date}.

Abaixo estão as citações registradas (uma por linha, com um índice):

{citations_text}

ESCOLHA SEMPRE A CITAÇÃO MAIS RECENTE!

Informe apenas:
- o índice da citação escolhida (campo 'index');
- uma justificativa curta (campo 'justification').

Responda em JSON.
""".strip()

    choice: CitationChoice = extractor.with_structured_output(CitationChoice).invoke(prompt)
    idx = choice.index
    chosen = filtered[idx]

    # Tenta várias chaves possíveis (ajuste se seus dicts tiverem outros nomes)
    start_raw = _first_present(chosen, ["data_inicio_contagem", "DataInicioContagem", "DataInicioContagem".lower()])
    final_raw = _first_present(chosen, ["data_final_resposta", "DataFinalResposta", "DataFinalResposta".lower()])

    start_dt = _to_datetime_safe(start_raw)
    final_dt = _to_datetime_safe(final_raw)

    if not start_dt or not final_dt:
        return {
            "deadline_text": None,
            "deadline_date": None,
            "chosen_citation": chosen,
            "justification": (
                f"{choice.justification} | Missing/invalid dates in chosen citation. "
                f"start_raw={start_raw}, final_raw={final_raw}"
            ),
        }

    days = (final_dt.date() - start_dt.date()).days
    deadline_text = f"{days} days"

    return {
        "deadline_text": deadline_text,
        "deadline_date": final_dt.date().isoformat(),
        "chosen_citation": chosen,
        "justification": choice.justification
    }


######################
# Obrigacao Pipeline #
######################

def fetch_df_obrigacoes_nao_processadas_raw(
    conn
) -> pd.DataFrame:
    sql_obrigacao_processar = open(os.path.join(SQL_DIR, "obligations_nonprocessed.sql")).read()
    return pd.read_sql(
        sql_obrigacao_processar,
        conn
    )

def aggregate_responsaveis(df_raw: pd.DataFrame) -> pd.DataFrame:
    person_cols = ["nome_responsavel", "documento_responsavel", "tipo_responsavel", "id_pessoa"]
    group_cols = [c for c in df_raw.columns if c not in person_cols]

    df_aug = (
        df_raw.groupby(group_cols, dropna=False)
        .apply(
            lambda x: pd.Series(
                {
                    "responsaveis": x[person_cols]
                    .apply(lambda y: y.dropna().to_dict(), axis=1)
                    .tolist()
                }
            )
        )
        .reset_index()
    )
    return df_aug


def process_obrigacao_row(
    session: Session,
    row,
    extractor_obrigacao,        # seu LLM extractor (ex: extractor_obrigacao_gpt4turbo)
    extractor_responsible,      # seu extractor de responsáveis (se aplicável)
    run_id: str | None = None,
    overwrite: bool = False,
) -> int | None:
    """
    Processa uma NERObrigacao (row do df_ob_aug):
    - Se já existe ObrigacaoProcessada(IdNerObrigacao) e overwrite=False, pula.
    - Se overwrite=True, pode deletar a marcação e recriar (ou lógica equivalente).
    - Extrai obrigação estruturada via LLM e salva em Obrigacao + ObrigacaoProcessada(IdObrigacao).

    Returns:
        IdObrigacao (tabela final) ou None se pulou.
    """
    id_ner_obrigacao = int(row.id_ner_obrigacao)

    existing = session.execute(
        select(ProcessedObrigacaoORM)
        .where(ProcessedObrigacaoORM.IdNerObrigacao == id_ner_obrigacao)
    ).scalar_one_or_none()

    if existing and not overwrite:
        logger.info(
            "Skipping Obrigacao for IdNerObrigacao=%s because it is already processed (IdObrigacaoProcessada=%s).",
            id_ner_obrigacao, existing.IdObrigacaoProcessada,
        )
        return existing.IdObrigacao  # pode ser None se você marcou antes de vincular

    if existing and overwrite:
        logger.info("Overwriting ObrigacaoProcessada=%s for IdNerObrigacao=%s.", existing.IdObrigacaoProcessada, id_ner_obrigacao)
        session.delete(existing)
        session.commit()

    # rascunho (mesmo padrão que você já usa)
    obrigacao_rascunho = Obrigacao(
        descricao_obrigacao=row.descricao_obrigacao,
        orgao_responsavel=row.orgao_responsavel,
    )

    # Extração (usa seu pipeline atual)
    result = extract_obrigacao(
        extractor_obrigacao,
        extractor_responsible,
        row.to_dict(),
        obrigacao_rascunho=obrigacao_rascunho,
    )

    # Persistência: usa sua insert_obrigacao atualizada (que grava IdObrigacao na ObrigacaoProcessada)
    orm_obj = insert_obrigacao(session, result, row.to_dict())

    # Se insert_obrigacao retornar None quando já processada, trate aqui:
    if orm_obj is None:
        logger.info("insert_obrigacao returned None for IdNerObrigacao=%s (already processed).", id_ner_obrigacao)
        return None

    logger.info(
        "Saved Obrigacao IdObrigacao=%s for IdNerObrigacao=%s (processo=%s).",
        orm_obj.IdObrigacao, id_ner_obrigacao, getattr(row, "processo", None),
    )
    return orm_obj.IdObrigacao


def run_obrigacao_pipeline(
    extractor_obrigacao,
    extractor_responsible,
    run_id: str | None = None,
    overwrite: bool = False,
) -> pd.DataFrame:
    conn_dip = get_connection(DB_DECISOES)
    df_raw = fetch_df_obrigacoes_nao_processadas_raw(conn_dip)
    df_aug = aggregate_responsaveis(df_raw)

    engine_bddip = get_connection(DB_DECISOES)
    SessionLocal = sessionmaker(bind=engine_bddip)
    session = SessionLocal()

    try:
        for _, row in df_aug.iterrows():
            process_obrigacao_row(
                session=session,
                row=row,
                extractor_obrigacao=extractor_obrigacao,
                extractor_responsible=extractor_responsible,
                run_id=run_id,
                overwrite=overwrite,
            )
    finally:
        session.close()

    return df_aug

#########################
# Recomendacao Pipeline #
#########################

def fetch_df_recomendacoes_nao_processadas_raw(conn) -> pd.DataFrame:
    """
    Retorna dataframe com recomendações NER ainda não processadas (raw),
    geralmente vindo do banco de decisões/NER + joins necessários + responsáveis em linhas.
    """
    sql_path = os.path.join(SQL_DIR, "recommendations_nonprocessed.sql")
    sql_rec_processar = open(sql_path, "r").read()
    return pd.read_sql(sql_rec_processar, conn)


def process_recomendacao_row(
    session: Session,
    row,
    extractor_recomendacao: BaseChatModel,
    extractor_responsible: BaseChatModel,
    run_id: str | None = None,
    overwrite: bool = False,
) -> int | None:
    """
    Espelha process_obrigacao_row():
    - checa ProcessedRecomendacaoORM(IdNerRecomendacao)
    - se overwrite=True, remove marcação e reprocessa
    - extrai Recomendacao estruturada e persiste + marca como processada

    Returns:
        IdRecomendacao (tabela final) ou None se pulou.
    """
    id_ner_recomendacao = int(row.id_ner_recomendacao)

    existing = session.execute(
        select(ProcessedRecomendacaoORM)
        .where(ProcessedRecomendacaoORM.IdNerRecomendacao == id_ner_recomendacao)
    ).scalar_one_or_none()

    if existing and not overwrite:
        logger.info(
            "Skipping Recomendacao for IdNerRecomendacao=%s because it is already processed (IdRecomendacaoProcessada=%s).",
            id_ner_recomendacao, existing.IdRecomendacaoProcessada,
        )
        return existing.IdRecomendacao

    if existing and overwrite:
        logger.info(
            "Overwriting RecomendacaoProcessada=%s for IdNerRecomendacao=%s.",
            existing.IdRecomendacaoProcessada, id_ner_recomendacao
        )
        session.delete(existing)
        session.commit()

    # rascunho (padrão obrigação)
    recomendacao_rascunho = Recomendacao(
        descricao_recomendacao=row.descricao_recomendacao,
        orgao_responsavel_recomendacao=getattr(row, "orgao_responsavel", None) or "Desconhecido",
        nome_responsavel_recomendacao="Desconhecido",
        prazo_cumprimento_recomendacao=None,
        data_cumprimento_recomendacao=None,
    )

    result = extract_recomendacao(
        extractor=extractor_recomendacao,
        extractor_responsible=extractor_responsible,
        row=row.to_dict(),
        recomendacao_rascunho=recomendacao_rascunho,
    )

    orm_obj = insert_recomendacao(session, result, row.to_dict())
    if orm_obj is None:
        logger.info(
            "insert_recomendacao returned None for IdNerRecomendacao=%s (already processed).",
            id_ner_recomendacao
        )
        return None

    logger.info(
        "Saved Recomendacao IdRecomendacao=%s for IdNerRecomendacao=%s (processo=%s).",
        orm_obj.IdRecomendacao, id_ner_recomendacao, getattr(row, "processo", None),
    )
    return orm_obj.IdRecomendacao


def run_recomendacao_pipeline(
    extractor_recomendacao: BaseChatModel,
    extractor_responsible: BaseChatModel,
    run_id: str | None = None,
    overwrite: bool = False,
) -> pd.DataFrame:
    """
    - Lê recomendações não processadas (raw)
    - Agrega responsáveis em lista por recomendação
    - Processa linha a linha (idempotente)
    """
    conn = get_connection(DB_DECISOES)  # ajuste se a view/tabela estiver em outro DB
    df_raw = fetch_df_recomendacoes_nao_processadas_raw(conn)
    df_aug = aggregate_responsaveis(df_raw)

    engine = get_connection(DB_DECISOES)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        for _, row in df_aug.iterrows():
            process_recomendacao_row(
                session=session,
                row=row,
                extractor_recomendacao=extractor_recomendacao,
                extractor_responsible=extractor_responsible,
                run_id=run_id,
                overwrite=overwrite,
            )
    finally:
        session.close()

    return df_aug