"""Roda a extração estruturada em todos os PDFs de pdfs_artigos/.

Idempotente via cache em data/revisao/cache/.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.revisao_batch import (  # noqa: E402
    run_batch,
    to_dataframe_rows,
    write_errors_csv,
)
from tools.revisao_pipeline import build_extraction_chain  # noqa: E402

PDFS_DIR = ROOT / "pdfs_artigos"
CACHE_DIR = ROOT / "data" / "revisao" / "cache"
OUT_CSV = ROOT / "data" / "revisao" / "artigos_extraidos.csv"
ERR_CSV = ROOT / "data" / "revisao" / "erros_extracao.csv"


def main() -> int:
    load_dotenv()
    chain = build_extraction_chain()

    pdfs = sorted(PDFS_DIR.glob("*.pdf"))
    print(f"[{datetime.now():%H:%M:%S}] início: {len(pdfs)} PDFs", flush=True)

    def progress(name, tag, dt, err):
        ts = datetime.now().strftime("%H:%M:%S")
        suffix = f" — {err}" if err else ""
        print(f"[{ts}] [{tag:5s}] {dt:5.1f}s  {name}{suffix}", flush=True)

    t0 = time.time()
    results = run_batch(pdfs, chain, CACHE_DIR, progress=progress)
    dt = time.time() - t0

    rows = to_dataframe_rows(results)
    df = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8")

    n_err = write_errors_csv(results, ERR_CSV)
    n_low = int((df.get("confianca_extracao", pd.Series([], dtype=float)) < 0.6).sum())

    print(
        f"\n[{datetime.now():%H:%M:%S}] fim em {dt/60:.1f} min  "
        f"sucesso={len(rows)} falhas={n_err} baixa_confianca={n_low}",
        flush=True,
    )
    print(f"CSV: {OUT_CSV}", flush=True)
    if n_err:
        print(f"erros: {ERR_CSV}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
