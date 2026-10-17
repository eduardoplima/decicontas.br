"""Candidate person mentions in the Label Studio export, from three sources.

spaCy (PER entities), honorific/upper-case patterns and one structured LLM call
per document. Each candidate records which sources found it. Output:
``docs/privacy/persons_candidates.json`` with the document texts and the
candidates (``id``, ``doc_id``, ``text``, ``start``, ``end``, ``sources``,
``context``).

    uv run python -m tools.review.find_persons            # all sources
    uv run python -m tools.review.find_persons --no-llm   # spaCy + patterns only
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydantic import BaseModel, Field

from research.release import paths
from tools.review.grouping import normalise_tokens
from tools.review.names import strip_role_prefix

logger = logging.getLogger("tools.review.find_persons")

OUT_PATH = paths.REPO_ROOT / "docs" / "privacy" / "persons_candidates.json"
CONTEXT = 80

NAME_TOKEN = r"[A-ZÁ-Ú][A-Za-zÁ-Úá-ú'’-]+"
HONORIFIC_RE = re.compile(
    r"(?:\b(?:Sr|Sra|Srª|Senhor|Senhora|Dr|Dra|Exm[oa]|Ilm[oa])\.?\s+(?:Sr\.?a?\s+)?)"
    rf"((?:{NAME_TOKEN})(?:\s+(?:d[aeo]s?\s+)?{NAME_TOKEN}){{0,6}})"
)
CAPS_RE = re.compile(r"\b([A-ZÁ-Ú]{2,}(?:\s+(?:D[AEO]S?\s+)?[A-ZÁ-Ú]{2,}){1,6})\b")

# Tokens that mark a candidate as not a person (bodies, acts, legal references).
STOP_TOKENS = {
    "tribunal", "contas", "estado", "municipio", "municipal", "camara", "prefeitura", "secretaria",
    "instituto", "previdencia", "conselho", "ministerio", "publico", "diretoria", "corte", "poder",
    "executivo", "legislativo", "lei", "complementar", "resolucao", "decisao", "acordao", "inciso",
    "artigo", "art", "decidem", "acordam", "provimento", "recurso", "processo", "prestacao",
    "tomada", "regimento", "interno", "relator", "relatora", "conselheiro", "conselheira",
    "procurador", "procuradora", "decisum", "sessao", "plenario", "justica", "eleitoral", "fundo",
    "sistema", "programa", "secretario", "secretaria", "gestor", "gestora", "unidade", "tecnica",
    "ato", "aposentador", "aposentadoria", "pensao", "regular", "irregular", "aprovacao", "rejeicao",
    "denegacao", "registro", "negar", "negativa", "dar", "conhecimento", "siai", "rgf", "rreo",
    "lrf", "cf", "lc", "lce", "tce", "rn", "secex", "conju", "ipern", "dae", "ddp", "dap",
}
STOP_TOKENS |= {
    "assessor", "juridico", "juridica", "professor", "professora", "especialista", "suporte",
    "pedagogico", "imputacao", "debito", "desaprovacao", "lastro", "validade", "fundamento",
    "penalidade", "pecuniaria", "fato", "gerador", "multa", "ressarcimento", "recomendacao",
    "determinacao", "intimacao", "notificacao", "representacao", "arquivamento", "prescricao",
    "renovacao", "aplicacao", "demanda", "fiscalizatoria", "auditoria", "inspecao", "parecer",
    "previo", "julgamento", "contas", "gestao", "exercicio", "orgao", "entidade", "fundacao",
    "autarquia", "empresa", "companhia", "sociedade", "associacao", "sindicato", "banco",
}
STOP_FIRST = {"inciso", "art", "lei", "decisum", "relator", "negar", "art."}


class Pessoas(BaseModel):
    nomes: list[str] = Field(default_factory=list, description="Nomes de pessoas naturais, exatamente como escritos no texto")


PROMPT = (
    "Liste os nomes de PESSOAS NATURAIS (seres humanos) citados no texto a seguir, exatamente como "
    "aparecem escritos, um por item, sem títulos (Sr., Dr.) e sem cargos. Não inclua órgãos, "
    "municípios, empresas, leis nem cargos. Se não houver pessoas, devolva lista vazia.\n\n"
)


def _looks_like_person(text: str, sources: set[str]) -> bool:
    toks = normalise_tokens(text)
    if not toks or toks[0] in STOP_FIRST or any(t in STOP_TOKENS for t in toks):
        return False
    if any(c in text for c in "`´\"()[]/\\0123456789"):
        return False
    # a lone token found by spaCy alone is usually a false positive
    return len(toks) >= 2 or sources - {"spacy", "caps"}


def _find_all(text: str, needle: str) -> list[tuple[int, int]]:
    out, start = [], 0
    while True:
        i = text.find(needle, start)
        if i < 0:
            return out
        out.append((i, i + len(needle)))
        start = i + 1


def spacy_candidates(nlp, text: str) -> list[tuple[int, int, str]]:
    return [(e.start_char, e.end_char, "spacy") for e in nlp(text).ents if e.label_ == "PER"]


def pattern_candidates(text: str) -> list[tuple[int, int, str]]:
    out = [(m.start(1), m.end(1), "honorific") for m in HONORIFIC_RE.finditer(text)]
    out += [(m.start(1), m.end(1), "caps") for m in CAPS_RE.finditer(text)]
    return out


def llm_candidates(llm, text: str) -> list[tuple[int, int, str]]:
    result = llm.invoke(PROMPT + text)
    out = []
    for name in result.nomes:
        name = name.strip()
        if len(name) < 3:
            continue
        hits = _find_all(text, name) or [
            (m.start(), m.end()) for m in re.finditer(re.escape(name), text, re.IGNORECASE)
        ]
        out += [(s, e, "llm") for s, e in hits]
    return out


def merge_candidates(text: str, found: list[tuple[int, int, str]]) -> list[dict]:
    """Overlapping hits collapse into the longest span, keeping every source."""
    found = sorted(found, key=lambda x: (x[0], -(x[1] - x[0])))
    merged: list[dict] = []
    for s, e, src in found:
        if merged and s < merged[-1]["end"]:
            last = merged[-1]
            last["end"] = max(last["end"], e)
            last["sources"].add(src)
            continue
        merged.append({"start": s, "end": e, "sources": {src}})
    out = []
    for m in merged:
        mention, offset = strip_role_prefix(text[m["start"] : m["end"]].strip())
        if not mention or not _looks_like_person(mention, m["sources"]):
            continue
        start = text.index(mention, m["start"] + offset)
        out.append({"text": mention, "start": start, "end": start + len(mention), "sources": sorted(m["sources"])})
    return out


def run(use_llm: bool = True, limit: int | None = None, out_path: Path = OUT_PATH) -> dict:
    tasks = json.loads(paths.LABELED_CORPUS.read_text(encoding="utf-8"))
    docs = {int(t["id"]): t["data"]["text"] for t in tasks}
    if limit:
        docs = dict(list(docs.items())[:limit])

    import spacy

    nlp = spacy.load("pt_core_news_lg", disable=["parser", "lemmatizer"])
    llm = None
    if use_llm:
        from dotenv import load_dotenv

        load_dotenv(paths.REPO_ROOT / ".env")
        from research.release.run_llm_inference import make_llm

        llm = make_llm(azure_deployment="DeepSeek-V4-Flash", temperature=0).with_structured_output(
            Pessoas, method="function_calling"
        )

    def one_llm(item):
        doc_id, text = item
        for attempt in range(4):
            try:
                return doc_id, llm_candidates(llm, text)
            except Exception as exc:  # noqa: BLE001
                logger.warning("doc %s: llm attempt %d failed: %s", doc_id, attempt + 1, exc)
        return doc_id, []

    llm_hits: dict[int, list] = {}
    if llm is not None:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for doc_id, hits in pool.map(one_llm, docs.items()):
                llm_hits[doc_id] = hits

    candidates = []
    for doc_id, text in docs.items():
        found = spacy_candidates(nlp, text) + pattern_candidates(text) + llm_hits.get(doc_id, [])
        for i, c in enumerate(merge_candidates(text, found)):
            c.update(
                id=f"{doc_id}:{i}",
                doc_id=doc_id,
                context=text[max(0, c["start"] - CONTEXT) : c["end"] + CONTEXT],
            )
            candidates.append(c)

    payload = {"documents": {str(k): v for k, v in docs.items()}, "candidates": candidates}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    logger.info("%d candidates in %d documents -> %s", len(candidates), len({c["doc_id"] for c in candidates}), out_path)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run(use_llm=not args.no_llm, limit=args.limit)


if __name__ == "__main__":
    main()
