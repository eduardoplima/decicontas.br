"""Gera os corpos de tabela do Capítulo 5 da dissertação a partir dos CSVs.

O capítulo usa nomes em \\texttt{} minúsculos e decimais com vírgula, que não
correspondem aos rótulos de exibição dos artefatos. Este script faz a ponte,
para que a atualização dos números seja mecânica e verificável em vez de
digitada à mão.

Uso:
    uv run python scripts/gen_cap5_tables.py            # imprime no stdout
    uv run python scripts/gen_cap5_tables.py --out DIR  # grava um .tex por tabela
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from research.release import paths

# rótulo de exibição dos artefatos -> nome \texttt{} usado na dissertação
NOMES = {
    "DeepSeek-V4-Flash": "deepseek-v4-flash",
    "GPT-4.1": "gpt-4.1",
    "GPT-4.1-mini": "gpt-4.1-mini",
    "GPT-4.1-nano": "gpt-4.1-nano",
    "GPT-5-mini": "gpt-5-mini",
    "GPT-5.1": "gpt-5.1",
    "GPT-5.2": "gpt-5.2",
    "Qwen2.5-72B": "qwen2.5-72b",
    "Llama-3.3-70B": "llama-3.3-70b",
    "LegalBert-pt": "legalbert-pt-fp",
    "BERTimbauLaw": "bertimbaulaw",
    "BERTimbau-base": "bertimbau-base",
    "BERTimbau-large": "bertimbau-large",
    "JurisBERT": "jurisbert",
    "Legal-BERT-STF": "legal-bert-stf",
    "GovBERT-BR": "govbert-br",
    "Legal-BERTimbau-base": "legal-bertimbau-base",
    "LegalBERTPT-br": "legal-bert-pt-br",
    "BiLSTM-CRF": "bilstm-crf",
}
# marcados com dagger no capítulo (grupo do líder sob Holm)
DAGGER = {"DeepSeek-V4-Flash", "GPT-4.1"}


def v(x: float, negrito: bool = False) -> str:
    t = f"{x:.3f}".replace(".", ",")
    return f"\\textbf{{{t}}}" if negrito else t


def tabela_geral(df: pd.DataFrame) -> str:
    """Corpo de tab:resultados_gerais: Token F1 | macro | micro | P | R."""
    df = df.sort_values("span_f1_macro", ascending=False)
    melhores = {c: df[c].max() for c in
                ("token_f1", "span_f1_macro", "span_f1", "span_precision", "span_recall")}
    linhas = []
    for _, r in df.iterrows():
        nome = NOMES.get(r["display"], r["display"])
        tipo = "Sup." if r["model"].endswith("__supervised") else "LLM"
        marca = "$^{\\dagger}$" if r["display"] in DAGGER else ""
        cols = [v(r[c], r[c] == melhores[c]) for c in
                ("token_f1", "span_f1_macro", "span_f1", "span_precision", "span_recall")]
        linhas.append(
            f"        \\texttt{{{nome}}}{marca} & {tipo}  & " + " & ".join(cols) + " \\\\"
        )
    return "\n".join(linhas)


def tabela_entidade(df: pd.DataFrame, modelos: list[str]) -> str:
    """Corpo de tab:f1_entidade para os modelos indicados."""
    piv = df.pivot_table(index="display", columns="label", values="f1")
    ordem = ["MULTA", "OBRIGACAO", "RESSARCIMENTO", "RECOMENDACAO"]
    linhas = []
    for disp in modelos:
        if disp not in piv.index:
            continue
        cols = [v(piv.loc[disp, lab], piv.loc[disp, lab] == piv[lab].max()) for lab in ordem]
        linhas.append(
            f"        \\texttt{{{NOMES.get(disp, disp)}}} & " + " & ".join(cols) + " \\\\"
        )
    return "\n".join(linhas)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    principal = pd.read_csv(paths.EVALUATION_DIR / "C_main_results.csv")
    entidade = pd.read_csv(paths.EVALUATION_DIR / "D_per_entity.csv")

    # os quatro mais fortes por macro, dois de cada paradigma
    sup = principal[principal.model.str.endswith("__supervised")]
    llm = principal[~principal.model.str.endswith("__supervised")]
    quatro = (
        llm.nlargest(2, "span_f1_macro").display.tolist()
        + sup.nlargest(2, "span_f1_macro").display.tolist()
    )

    saidas = {
        "tab_resultados_gerais": tabela_geral(principal),
        "tab_f1_entidade": tabela_entidade(entidade, quatro),
    }
    for nome, corpo in saidas.items():
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / f"{nome}.tex").write_text(corpo + "\n", encoding="utf-8")
            print(f"gravado {args.out / (nome + '.tex')}")
        else:
            print(f"% ===== {nome} =====")
            print(corpo)
            print()
    print(f"% modelos da tabela por entidade: {', '.join(quatro)}")


if __name__ == "__main__":
    main()
