"""A 35-token synthetic decision shared by the adjudication tests (tokens 22-26 are a SECEX clause)."""

from __future__ import annotations

from research.dataset_io import token_offsets
from tools.adjudication.divergences import DocView

# fmt: off
WORDS = [
    "ACORDAM", "os", "Conselheiros,", "julgar:", "a)", "multa", "de", "R$", "1.000,00", "ao",      # 0-9
    "gestor;", "b)", "obrigação", "de", "fazer", "x;", "c)", "ressarcimento", "de", "R$",          # 10-19
    "50,00;", "d)", "recomende", "à", "SECEX", "que", "acompanhe;", "e)", "recomendação", "ao",   # 20-29
    "órgão", "para", "cumprir", "a", "lei.",                                                       # 30-34
]
# fmt: on
TEXT = " ".join(WORDS)
OFFSETS = token_offsets(TEXT)
MULTA = (5, 11, "MULTA")


def view(a1, a2, a3, doc_id=7) -> DocView:
    return DocView(doc_id, TEXT, OFFSETS, {"A1": sorted(a1), "A2": sorted(a2), "A3": sorted(a3)})


def char_span(start: int, end: int) -> tuple[int, int]:
    """Character bounds of the half-open token range ``[start, end)``."""
    return OFFSETS[start][0], OFFSETS[end - 1][1]
