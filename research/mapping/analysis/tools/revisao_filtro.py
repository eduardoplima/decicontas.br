"""Critérios de exclusão da revisão sistemática (cells 20-24 de revisao.ipynb).

Filtra `artigos_extraidos.csv` deixando apenas:
- títulos com `status == 'Accepted'` em `todos_artigos.xlsx`
- PDFs com `>= 4` páginas (cell 22 do notebook)
- PDFs lidos sem erro
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from PyPDF2 import PdfReader
from langdetect import DetectorFactory, LangDetectException, detect_langs

from tools.pdf_loader import extract_text

DetectorFactory.seed = 0  # determinístico

MIN_PAGINAS = 4
IDIOMAS_ACEITOS = {"en", "pt"}
TAMANHO_AMOSTRA_IDIOMA = 5000

# PDFs cujo conteúdo não corresponde ao registro em todos_artigos.xlsx
# (downloader pegou paper errado; sem versão OA disponível para re-baixar).
#
# Os rótulos deste módulo descrevem o ARQUIVO em pdfs_artigos/, não o estudo.
# O motivo de exclusão de cada estudo na fase de elegibilidade está em
# data/revisao/exclusoes_elegibilidade.csv (ex.: o PDF de 1 página é só a
# primeira página de um artigo de periódico; "idioma_es" é ruído do detector
# sobre um PDF sem texto extraível).
EXCLUIR_PDF_CONTEUDO_TROCADO = {
    "BERT-Based Ensemble Model for Statute Law Retrieval and Legal Information Entailment.pdf",
    "A systematical procedure to extracting legal entities from Indonesian judicial decisions.pdf",
    "A Study on the Impact of Intradomain Finetuning of Deep Language Models for Legal Named Entity Recognition in Portuguese.pdf",
    # Li 2025 (DOI 10.1177/14727978251323131) — PDF baixado é Narayan 2022, dup do
    # arquivo "Detecting Regulation Violations…". SAGE OA mas Cloudflare bloqueia bot.
    "Legal information extraction and classification using BERT, Bi-LSTM, and CRF models.pdf",
}


def _norm(s: str) -> str:
    s = str(s).lower()
    s = re.sub(r'[\\/:*?"<>|]+', "_", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _stem_pdf(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"^\d+_", "", stem)
    return _norm(stem)


def carregar_aceitos(xlsx_path: Path) -> pd.DataFrame:
    todos = pd.read_excel(xlsx_path)
    acc = todos[todos["status"] == "Accepted"].copy()
    acc["__norm"] = acc["title"].map(_norm)
    return acc


def contar_paginas(pdf_path: Path) -> int | None:
    try:
        return len(PdfReader(pdf_path).pages)
    except Exception:
        return None


def detectar_idioma(pdf_path: Path) -> str | None:
    """Idioma dominante nos primeiros TAMANHO_AMOSTRA_IDIOMA chars do PDF."""
    try:
        sample = extract_text(pdf_path)[:TAMANHO_AMOSTRA_IDIOMA].strip()
        if not sample:
            return None
        return detect_langs(sample)[0].lang
    except (LangDetectException, Exception):
        return None


def aplicar_filtros(
    df_extracoes: pd.DataFrame,
    pdfs_dir: Path,
    aceitos: pd.DataFrame,
) -> pd.DataFrame:
    """Devolve `df_extracoes` apenas com linhas que passam nos critérios."""
    aceitos_set = set(aceitos["__norm"])
    aceitos_year = dict(zip(aceitos["__norm"], aceitos["year"]))
    keep_idx = []
    motivos: list[str] = []
    ano_aceito: dict = {}  # idx -> ano do registro aceito correspondente
    for i, row in df_extracoes.iterrows():
        pdf_name = row["pdf_arquivo"]
        if pdf_name in EXCLUIR_PDF_CONTEUDO_TROCADO:
            motivos.append("conteudo_pdf_trocado")
            continue
        norm_pdf = _stem_pdf(pdf_name)
        # match: igual, prefixo de qualquer lado
        matched = next(
            (
                n
                for n in aceitos_set
                if norm_pdf == n or norm_pdf.startswith(n) or n.startswith(norm_pdf)
            ),
            None,
        )
        if matched is None:
            motivos.append("nao_aceito_no_xlsx")
            continue
        pdf_path = pdfs_dir / pdf_name
        n_pag = contar_paginas(pdf_path)
        if n_pag is None:
            motivos.append("erro_leitura_pdf")
            continue
        if n_pag < MIN_PAGINAS:
            motivos.append(f"menos_de_{MIN_PAGINAS}_paginas")
            continue
        idioma = detectar_idioma(pdf_path)
        if idioma not in IDIOMAS_ACEITOS:
            motivos.append(f"idioma_{idioma or 'desconhecido'}")
            continue
        keep_idx.append(i)
        ano_aceito[i] = aceitos_year.get(matched)
        motivos.append("ok")
    df_extracoes = df_extracoes.copy()
    df_extracoes["__motivo"] = motivos
    # Backfill do ano quando o LLM não o extraiu (ano == 0/NaN): usa o ano
    # registrado em todos_artigos.xlsx para o título aceito correspondente.
    # Sem isso, gráficos por ano descartam silenciosamente esses artigos.
    for idx, ano in ano_aceito.items():
        atual = df_extracoes.at[idx, "ano"]
        if (pd.isna(atual) or atual == 0) and pd.notna(ano):
            df_extracoes.at[idx, "ano"] = int(ano)
    return df_extracoes.loc[keep_idx].drop(columns=["__motivo"]), df_extracoes


def relatorio_exclusoes(df_marcado: pd.DataFrame) -> pd.DataFrame:
    return (
        df_marcado.loc[df_marcado["__motivo"] != "ok", ["pdf_arquivo", "__motivo"]]
        .rename(columns={"__motivo": "motivo_exclusao"})
        .reset_index(drop=True)
    )
