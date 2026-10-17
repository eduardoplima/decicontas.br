"""Reduce a mention to the person's name: drop vocatives, roles and honorifics in front of it."""

from __future__ import annotations

import re

ROLE_WORDS = (
    "prefeit[oa]", "vice-prefeit[oa]", "vereador[a]?", "presidente", "secret[áa]ri[oa]", "gestor[a]?",
    "ordenador[a]?", "servidor[a]?", "respons[áa]vel", "recorrente", "recorrid[oa]", "requerente",
    "requerid[oa]", "interessad[oa]", "denunciante", "denunciad[oa]", "representante", "representad[oa]",
    "advogad[oa]", "procurador[a]?", "conselheir[oa]", "auditor[a]?", "relator[a]?", "diretor[a]?",
    "chefe", "superintendente", "coordenador[a]?", "tesoureir[oa]", "contador[a]?", "pregoeir[oa]",
    "substitut[oa]", "senhor[a]?", "sr\\.?[ªa]?", "dr[a]?", "doutor[a]?", "exm[oa]", "ilm[oa]",
    "excelent[íi]ssim[oa]", "ilustr[íi]ssim[oa]", "merit[íi]ssim[oa]", "ex-[\\w-]+",
    "d[oa]s?", "[oa]s?", "e",
)
_PREFIX_RE = re.compile(r"^(?:" + "|".join(ROLE_WORDS) + r")\.?,?\s+", re.IGNORECASE)


def strip_role_prefix(text: str) -> tuple[str, int]:
    """``(name, offset)``: the mention without leading role words and how many characters were dropped."""
    offset = 0
    while True:
        m = _PREFIX_RE.match(text[offset:])
        if not m or offset + m.end() >= len(text):
            break
        offset += m.end()
    return text[offset:].strip(), offset
