"""Align an extracted span (``descricao``) back to the source text.

Used by the review UI to highlight where a staged obligation / recommendation
came from in the full ``texto_acordao``. Pure, side-effect-free.
"""

from __future__ import annotations

from typing import Optional

from rapidfuzz import fuzz

_FUZZY_THRESHOLD = 90.0


def find_span_in_text(descricao: str, texto_acordao: str) -> Optional[str]:
    """Locate ``descricao`` inside ``texto_acordao`` and return the matched slice.

    Strategy:
      1. Exact case-sensitive substring.
      2. Case-insensitive substring (preserves original casing via offset slice).
      3. Fuzzy fallback via ``rapidfuzz.fuzz.partial_ratio``; returns the best
         substring of ``texto_acordao`` if the score is ``>= 90``.

    Returns the matched substring from ``texto_acordao`` (never from
    ``descricao``), or ``None`` if no acceptable match exists.
    """
    if not descricao or not texto_acordao:
        return None

    idx = texto_acordao.find(descricao)
    if idx != -1:
        return texto_acordao[idx : idx + len(descricao)]

    lower_desc = descricao.lower()
    lower_text = texto_acordao.lower()
    idx = lower_text.find(lower_desc)
    if idx != -1:
        return texto_acordao[idx : idx + len(descricao)]

    alignment = fuzz.partial_ratio_alignment(descricao, texto_acordao)
    if alignment is None or alignment.score < _FUZZY_THRESHOLD:
        return None

    start = alignment.dest_start
    end = alignment.dest_end
    if start is None or end is None or end <= start:
        return None
    return texto_acordao[start:end]
