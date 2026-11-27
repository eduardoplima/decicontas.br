"""Gera estudos_aprovados.bib com os artigos filtrados (79 na versão final).

Tipo bibtex inferido de `document_type` na xlsx:
  Article          -> @article
  Conference paper -> @inproceedings
  Book chapter     -> @incollection
  qualquer outro   -> @misc

Combina:
- artigos_filtrados.csv (verdade sobre quem entra)
- todos_artigos.xlsx    (campos bibliográficos: author, journal, doi, ...)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CSV = ROOT / "data" / "revisao" / "artigos_filtrados.csv"
XLSX = ROOT / "todos_artigos.xlsx"
OUT = ROOT / "outputs" / "estudos_aprovados.bib"


def _norm(s: str) -> str:
    s = str(s).lower()
    s = re.sub(r'[\\/:*?"<>|]+', "_", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _surname(author_field: str) -> str:
    """Pega o sobrenome do primeiro autor do campo BibTeX-style.

    Formato esperado em todos_artigos.xlsx: 'Sobrenome, Nome and Sobrenome, Nome'.
    """
    if not isinstance(author_field, str) or not author_field.strip():
        return "anon"
    primeiro = author_field.split(" and ")[0]
    if "," in primeiro:
        sobrenome = primeiro.split(",", 1)[0]
    else:
        sobrenome = primeiro.strip().split(" ")[-1]
    sobrenome = re.sub(r"[^A-Za-z]", "", sobrenome)
    return sobrenome.lower() or "anon"


def _bib_escape(s: str) -> str:
    if not isinstance(s, str):
        return ""
    # preserva acentos UTF-8; escapa apenas chaves e ampersand
    return s.replace("\\", r"\textbackslash{}").replace("&", r"\&")


def _campo(nome: str, valor) -> str | None:
    if pd.isna(valor):
        return None
    s = str(valor).strip()
    if not s:
        return None
    return f"  {nome} = {{{_bib_escape(s)}}},"


def _tipo_bibtex(doctype) -> tuple[str, str]:
    """Devolve (tipo_bibtex, campo_venue) baseado em document_type.

    Para @inproceedings o "venue" vai em `booktitle`; em @article vai em `journal`.
    """
    if not isinstance(doctype, str):
        return "article", "journal"
    d = doctype.strip().lower()
    if d == "conference paper":
        return "inproceedings", "booktitle"
    if d == "book chapter":
        return "incollection", "booktitle"
    if d in ("article", "review"):
        return "article", "journal"
    return "misc", "howpublished"


def _gerar_chave(surname: str, ano, usadas: set[str]) -> str:
    base = f"{surname}{int(ano) if pd.notna(ano) else 'XXXX'}"
    if base not in usadas:
        usadas.add(base)
        return base
    # sufixo a, b, c, ...
    for suf in "abcdefghijklmnopqrstuvwxyz":
        cand = base + suf
        if cand not in usadas:
            usadas.add(cand)
            return cand
    raise RuntimeError(f"chaves esgotadas para {base}")


def main() -> int:
    df_csv = pd.read_csv(CSV)
    xlsx = pd.read_excel(XLSX)
    xlsx["__norm"] = xlsx["title"].map(_norm)

    entradas = []
    usadas: set[str] = set()
    sem_match: list[str] = []

    # ordenar por ano, depois título — para uma .bib estável
    df_csv = df_csv.sort_values(["ano", "titulo"], na_position="last")

    for _, row in df_csv.iterrows():
        pdf_name = row["pdf_arquivo"]
        norm_pdf = _norm(Path(pdf_name).stem)
        # match contra xlsx por norm de título
        cand = xlsx[
            xlsx["__norm"].apply(
                lambda n: n == norm_pdf
                or norm_pdf.startswith(n)
                or n.startswith(norm_pdf)
            )
        ]
        if cand.empty:
            sem_match.append(pdf_name)
            x = {}
        else:
            x = cand.iloc[0].to_dict()

        title = x.get("title") or row["titulo"]
        author = x.get("author")
        if pd.isna(author) or not isinstance(author, str) or not author.strip():
            # fallback: lista de autores da extração
            try:
                import ast
                lista = ast.literal_eval(row["autores"]) if isinstance(row["autores"], str) else []
            except Exception:
                lista = []
            author = " and ".join(lista) if lista else None

        ano_x = x.get("year")
        ano = int(ano_x) if pd.notna(ano_x) else int(row["ano"]) if row.get("ano") else None

        sobrenome = _surname(author or "")
        chave = _gerar_chave(sobrenome, ano, usadas)

        venue = x.get("journal")
        if pd.isna(venue) or not isinstance(venue, str) or not venue.strip():
            # fallback: venue da extração (frequentemente nome de conferência)
            venue = row.get("venue") if pd.notna(row.get("venue")) else None

        tipo, campo_venue = _tipo_bibtex(x.get("document_type"))

        linhas = [f"@{tipo}{{{chave},"]
        for k, v in [
            ("author", author),
            ("title", title),
            (campo_venue, venue),
            ("year", ano),
            ("volume", x.get("volume")),
            ("pages", x.get("pages")),
            ("doi", x.get("doi")),
            ("url", x.get("url")),
            ("publisher", x.get("publisher")),
        ]:
            campo = _campo(k, v)
            if campo:
                linhas.append(campo)
        linhas.append("}")
        entradas.append("\n".join(linhas))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"% Estudos aprovados no mapeamento sistemático: {len(entradas)} artigos\n"
        "% Gerado por scripts/gerar_bibtex.py — não editar à mão.\n\n"
    )
    OUT.write_text(header + "\n\n".join(entradas) + "\n", encoding="utf-8")

    print(f"escritos {len(entradas)} entradas em {OUT}")
    if sem_match:
        print(f"\n{len(sem_match)} sem match em todos_artigos.xlsx (usaram dados do CSV de extração):")
        for n in sem_match:
            print(f"  - {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
