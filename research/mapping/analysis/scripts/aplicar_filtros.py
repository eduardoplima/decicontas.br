"""Gera artigos_filtrados.csv aplicando critérios de exclusão.

Mantém artigos_extraidos.csv intocado.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.revisao_analise import gerar_figuras, gerar_latex  # noqa: E402
from tools.revisao_filtro import (  # noqa: E402
    aplicar_filtros,
    carregar_aceitos,
    relatorio_exclusoes,
)


def main() -> int:
    csv_in = ROOT / "data" / "revisao" / "artigos_extraidos.csv"
    csv_out = ROOT / "data" / "revisao" / "artigos_filtrados.csv"
    csv_excl = ROOT / "data" / "revisao" / "exclusoes_filtros.csv"
    xlsx = ROOT / "todos_artigos.xlsx"

    df = pd.read_csv(csv_in)
    aceitos = carregar_aceitos(xlsx)
    df_ok, df_marcado = aplicar_filtros(df, ROOT / "pdfs_artigos", aceitos)

    df_ok.to_csv(csv_out, index=False, encoding="utf-8")
    rel = relatorio_exclusoes(df_marcado)
    rel.to_csv(csv_excl, index=False, encoding="utf-8")

    print(f"entrada: {len(df)}")
    print(f"saída (filtrada): {len(df_ok)}")
    print(f"excluídos: {len(rel)}")
    print()
    print("motivos:")
    print(rel["motivo_exclusao"].value_counts().to_string())
    print()
    print("excluídos detalhados:")
    print(rel.to_string(index=False))

    # versão final = filtrada. outputs/figures e outputs/latex são canônicos.
    fig_dir = ROOT / "outputs" / "figures"
    tex_dir = ROOT / "outputs" / "latex"
    gerar_figuras(df_ok, fig_dir)
    gerar_latex(
        df_ok,
        tex_dir,
        xlsx_path=xlsx,
        citekeys_path=ROOT / "data" / "revisao" / "citekeys.csv",
    )
    print(f"\nfiguras: {fig_dir}")
    print(f"latex:   {tex_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
