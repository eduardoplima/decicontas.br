from __future__ import annotations

import hashlib
from pathlib import Path

import pdfplumber


def extract_text(pdf_path: Path | str) -> str:
    """Extrai todo o texto de um PDF preservando ordem das páginas.

    Junta páginas com '\\n\\n'. Páginas sem texto extraível viram string vazia.
    """
    pdf_path = Path(pdf_path)
    pages_text: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            pages_text.append(page.extract_text() or "")
    return "\n\n".join(pages_text)


def sha1_prefix(pdf_path: Path | str, n: int = 100_000) -> str:
    """Hash SHA-1 dos primeiros n bytes do arquivo. Chave de cache estável."""
    pdf_path = Path(pdf_path)
    h = hashlib.sha1()
    with pdf_path.open("rb") as f:
        h.update(f.read(n))
    return h.hexdigest()
