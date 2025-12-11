import os
import unicodedata
import pandas as pd

from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from rapidfuzz import process, fuzz 
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from fastmcp import FastMCP

mcp = FastMCP("Decisoes")

load_dotenv()

def get_connection(db: str = 'processo') -> Engine:
    load_dotenv()
    server = os.getenv("SQL_SERVER_HOST")
    user = os.getenv("SQL_SERVER_USER")
    password = os.getenv("SQL_SERVER_PASS")
    port = os.getenv("SQL_SERVER_PORT", "1433")  # default MSSQL port
    database = db

    # Construct connection string for SQLAlchemy using pymssql
    connection_string = f"mssql+pymssql://{user}:{password}@{server}/{database}"

    # Create and return SQLAlchemy engine
    engine = create_engine(connection_string)
    return engine

def normalize_text(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    s = s.strip().upper()
    # Remove acentos
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s

def get_all_units() -> pd.DataFrame:
    sql_unidades = open("../sql/units.sql").read()
    return pd.read_sql(sql_unidades, get_connection('BdSIAI'))

def find_unit(query: str, limit=5, score_cutoff=70):
    """
    Returns the best matches of NomeUnidade for the string `query`.
    """
    # Ensure a copy to not alter the original
    df = get_all_units()
    # Normalized column (can save permanently in the DF if you want)
    df["NomeUnidade_norm"] = df["NomeUnidade"].apply(normalize_text)
    query_norm = normalize_text(query)
    # Build list of options to compare
    nomes_norm = df["NomeUnidade_norm"].tolist()
    # Fuzzy search
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

def get_responsible_unit(unit: str, session_date: str) -> pd.DataFrame:
    id_unit = find_unit(unit, limit=1).iloc[0]["IdUnidadeJurisdicionada"]
    sql_resp = open("../sql/responsible_unit.sql").read()
    return pd.read_sql(sql_resp.format(id_unit=id_unit, session_date=session_date), get_connection('BdSIAI')).to_dict(orient='records')

def get_citations(process: str) -> pd.DataFrame:
    sql_citacoes = open("../sql/citations_by_process.sql").read()
    return pd.read_sql(sql_citacoes.format(process=process), get_connection('processo')).to_dict(orient='records')

def get_citations_after(process: str, session_date: str) -> pd.DataFrame:
    sql_citacoes = open("../sql/citations_by_process_after.sql").read()
    return pd.read_sql(sql_citacoes.format(process=process, session_date=session_date), get_connection('processo')).to_dict(orient='records')


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

class CitationChoice(BaseModel):
    index: int
    justification: str

llm = ChatOpenAI(model="gpt-4.1-mini")

def get_deadline_from_citations(process_number: str, session_date: str, responsible: str) -> dict:
    """
    Returns:
        - deadline_text: "X days"
        - deadline_date: "YYYY-MM-DD"
        - chosen_citation: citation row chosen by the LLM
        - justification: why that citation was selected
    """

    # 1. Fetch citation records
    records = get_citations_after(process_number, session_date)

    if not records:
        return {
            "deadline_text": None,
            "deadline_date": None,
            "chosen_citation": None,
            "justification": "No citation records found."
        }

    # 2. Filter citations by responsible entity/person (fuzzy match)
    filtered = filter_by_responsible(records, responsible)

    if not filtered:
        return {
            "deadline_text": None,
            "deadline_date": None,
            "chosen_citation": None,
            "justification": f"No citation matched responsible '{responsible}'."
        }

    # 3. Build readable text for the LLM
    lines = []
    for i, r in enumerate(filtered):
        lines.append(
            f"{i}: CitationNumber={r.get('Numero_Citacao')}/{r.get('Ano_citacao')}, "
            f"Organ={r.get('Orgao')}, Name={r.get('Nome')}, "
            f"StartCountDate={r.get('DataInicioContagem')}, "
            f"FinalResponseDate={r.get('DataFinalResposta')}"
        )

    citations_text = "\n".join(lines)

    prompt = f"""
    Você é um auditor que precisa escolher qual citação é a base para o prazo
    de resposta do processo {process_number}.

    Data da sessão do acórdão: {session_date}.

    Abaixo estão as citações registradas (uma por linha, com um índice):

    {citations_text}

    Regras gerais (simplificadas, ajuste conforme seu critério real):
    - Prefira citações mais recentes que sejam relevantes para o cumprimento da obrigação
      discutida na sessão.
    - Em caso de várias citações parecidas, escolha a que melhor representa o prazo
      principal dado ao órgão.
    - Se nenhuma for adequada, escolha a que parecer mais razoável e explique.

    Informe apenas:
    - o índice da citação escolhida (campo 'indice');
    - uma justificativa curta (campo 'justificativa').

    Responda em JSON.
    """

    choice: CitationChoice = llm.with_structured_output(CitationChoice).invoke(prompt)
    idx = choice.index
    chosen = filtered[idx]

    # 5. Convert date fields
    start_date = chosen.get("data_inicio_contagem")
    final_date = chosen.get("data_final_resposta")

    # Convert to datetime
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date)
    if isinstance(final_date, str):
        final_date = datetime.fromisoformat(final_date)

    # 6. Compute deadline
    days = (final_date.date() - start_date.date()).days
    deadline_text = f"{days} days"

    return {
        "deadline_text": deadline_text,
        "deadline_date": final_date.date().isoformat(),
        "chosen_citation": chosen,
        "justification": choice.justification
    }