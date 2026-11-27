from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from tenacity import retry, stop_after_attempt, wait_exponential

from tools.pdf_loader import extract_text, sha1_prefix
from tools.revisao_pipeline import truncate_text
from tools.revisao_schema import ArtigoExtraido


@dataclass
class BatchResult:
    pdf_path: Path
    artigo: ArtigoExtraido | None
    error: str | None
    cache_hit: bool


def cache_path(cache_dir: Path, pdf_hash: str) -> Path:
    return cache_dir / f"{pdf_hash}.json"


def load_cached(cache_dir: Path, pdf_hash: str) -> ArtigoExtraido | None:
    p = cache_path(cache_dir, pdf_hash)
    if not p.exists():
        return None
    return ArtigoExtraido.model_validate_json(p.read_text(encoding="utf-8"))


def save_cache(cache_dir: Path, pdf_hash: str, artigo: ArtigoExtraido) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path(cache_dir, pdf_hash).write_text(
        artigo.model_dump_json(indent=2), encoding="utf-8"
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=30))
def _invoke_with_retry(chain, texto: str) -> ArtigoExtraido:
    return chain.invoke({"texto_artigo": texto})


def process_pdf(
    pdf_path: Path,
    chain,
    cache_dir: Path,
    max_chars: int = 60_000,
) -> BatchResult:
    pdf_hash = sha1_prefix(pdf_path)
    cached = load_cached(cache_dir, pdf_hash)
    if cached is not None:
        return BatchResult(pdf_path, cached, None, cache_hit=True)

    try:
        texto = truncate_text(extract_text(pdf_path), max_chars=max_chars)
        if not texto.strip():
            return BatchResult(pdf_path, None, "PDF vazio após extração", False)
        artigo = _invoke_with_retry(chain, texto)
        save_cache(cache_dir, pdf_hash, artigo)
        return BatchResult(pdf_path, artigo, None, cache_hit=False)
    except Exception as e:
        return BatchResult(pdf_path, None, f"{type(e).__name__}: {e}", False)


def run_batch(
    pdfs: Iterable[Path],
    chain,
    cache_dir: Path,
    progress=None,
) -> list[BatchResult]:
    results: list[BatchResult] = []
    for pdf in pdfs:
        t0 = time.time()
        res = process_pdf(pdf, chain, cache_dir)
        dt = time.time() - t0
        if progress is not None:
            tag = "cache" if res.cache_hit else ("FAIL" if res.error else "ok")
            progress(pdf.name, tag, dt, res.error)
        results.append(res)
    return results


def to_dataframe_rows(results: list[BatchResult]) -> list[dict]:
    rows = []
    for res in results:
        if res.artigo is None:
            continue
        d = res.artigo.model_dump()
        d["pdf_arquivo"] = res.pdf_path.name
        rows.append(d)
    return rows


def write_errors_csv(results: list[BatchResult], path: Path) -> int:
    errs = [r for r in results if r.error]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pdf_arquivo", "erro"])
        for r in errs:
            w.writerow([r.pdf_path.name, r.error])
    return len(errs)
