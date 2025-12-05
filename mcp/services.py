import os
import json
import pymssql
import unicodedata

import pandas as pd
import numpy as np

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from rapidfuzz import process, fuzz  # pip install rapidfuzz
from dotenv import load_dotenv


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

def get_responsible_unit(id_unit: int, session_date: str) -> pd.DataFrame:
    sql_resp = open("../sql/responsible_unit.sql").read()
    return pd.read_sql(sql_resp.format(id_unit=id_unit, session_date=session_date), get_connection('BdSIAI'))