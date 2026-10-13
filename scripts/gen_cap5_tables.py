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
# marcados com dagger no capítulo: grupo do líder sob Holm sobre todos os pares
_LIDER = pd.read_csv(paths.EVALUATION_DIR / "J_leader_group.csv")
DAGGER = set(_LIDER.loc[_LIDER["in_leader_group"], "display"])


CLASSES = ["MULTA", "OBRIGACAO", "RECOMENDACAO", "RESSARCIMENTO"]
NOMES_CLASSE = {"MULTA": "Multa", "OBRIGACAO": "Obrigação", "RECOMENDACAO": "Recomendação", "RESSARCIMENTO": "Ressarcimento"}


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
    ordem = CLASSES
    linhas = []
    for disp in modelos:
        if disp not in piv.index:
            continue
        cols = [v(piv.loc[disp, lab], piv.loc[disp, lab] == piv[lab].max()) for lab in ordem]
        linhas.append(
            f"        \\texttt{{{NOMES.get(disp, disp)}}} & " + " & ".join(cols) + " \\\\"
        )
    return "\n".join(linhas)


def _num(x: float) -> str:
    """Valor com sinal explícito e vírgula decimal (``$-$`` para negativos)."""
    t = f"{abs(x):.3f}".replace(".", ",")
    return ("+" if x >= 0 else "$-$") + t


def _p(x: float) -> str:
    return "$< 0{,}001$" if x < 0.001 else "$" + f"{x:.3f}".replace(".", "{,}") + "$"


def tabela_bootstrap(df: pd.DataFrame) -> str:
    """Linhas de pares do bootstrap: A | B | Δ | IC | p | p_Holm (171) | Sig.

    Cada par é orientado para que o primeiro modelo seja o de maior F1 (Δ >= 0)
    e as linhas seguem |Δ| decrescente. ``p_holm_all`` é a correção de Holm sobre
    o conjunto completo de pares.
    """
    linhas = []
    for _, r in df.reindex(df["diff_f1"].abs().sort_values(ascending=False).index).iterrows():
        a, b = NOMES[r["display_a"]], NOMES[r["display_b"]]
        d, lo, hi = r["diff_f1"], r["ci_lower"], r["ci_upper"]
        if d < 0:
            a, b, d, lo, hi = b, a, -d, -hi, -lo
        sig = "sim" if r["p_holm_all"] < 0.05 else "não"
        linhas.append(
            f"        \\texttt{{{a}}} & \\texttt{{{b}}} & {_num(d)} & "
            f"[{_num(lo)};\\ {_num(hi)}] & {_p(r['p_value'])} & {_p(r['p_holm_all'])} & {sig} \\\\"
        )
    return "\n".join(linhas)


def tabela_iou(df: pd.DataFrame) -> str:
    """Corpo de tab:iou_sensitivity (``K_iou_sensitivity_wide.csv``), ordenado por IoU >= 0,5."""
    linhas = []
    for _, r in df.sort_values("0.5", ascending=False).iterrows():
        nome = NOMES.get(r["display"], r["display"])
        cols = " & ".join(v(r[c]) for c in ("0.3", "0.5", "0.7", "exact"))
        linhas.append(f"        \\texttt{{{nome}}} & {cols} \\\\")
    return "\n".join(linhas)


def tabela_prompting(df: pd.DataFrame, modelos: list[str]) -> str:
    """Corpo de tab:tecnicas_prompting (``H_prompting_overall.csv``): few-shot | CoT | two-stage."""
    piv = df.pivot_table(index="model", columns="technique", values="span_f1_macro")
    linhas = []
    for m in modelos:
        vals = [piv.loc[m, tec] for tec in ("few_shot", "cot", "two_stage")]
        melhor = max(vals)
        linhas.append(f"        \\texttt{{{m}}} & " + " & ".join(v(x, x == melhor) for x in vals) + " \\\\")
    return "\n".join(linhas)


def tabela_fc_js(overall: pd.DataFrame, modelos: list[str]) -> str:
    """Corpo de tab:saida_estruturada (``F_fc_vs_json_overall.csv``): FC, JS e Δ por modelo.

    As colunas são Token F1, span F1 (micro), precisão e revocação; o Δ de span
    F1 vai em negrito. Blocos separados por ``\\hline`` (sem o ``\\hline`` final).
    """
    cols = ("token_f1", "span_f1", "span_precision", "span_recall")
    blocos = []
    for m in modelos:
        fc = overall[(overall["model"] == m) & (overall["method"] == "function_calling")].iloc[0]
        js = overall[(overall["model"] == m) & (overall["method"] == "json_schema")].iloc[0]
        deltas = [fc[c] - js[c] for c in cols]
        delta_fmt = [_num(d) for d in deltas]
        delta_fmt[1] = f"\\textbf{{{delta_fmt[1]}}}"
        blocos.append(
            "\n".join(
                [
                    f"        \\multirow{{3}}{{*}}{{\\texttt{{{m}}}}}",
                    "        & FC       & " + " & ".join(v(fc[c]) for c in cols) + " \\\\",
                    "        & JS       & " + " & ".join(v(js[c]) for c in cols) + " \\\\",
                    "        & $\\Delta$ & " + " & ".join(delta_fmt) + " \\\\",
                ]
            )
        )
    return "\n        \\hline\n".join(blocos)


_TIPOS_FP = [("FP", "Espúrio"), ("boundary", "Fronteira incorreta"), ("duplicate", "Duplicata"), ("type_error", "Tipo errado")]
_TIPOS_FN = [("FN_overlap", "Com sobreposição insuficiente"), ("FN_no_pred", "Sem predição")]


def _pct(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def tabela_taxonomia(by_kind: pd.DataFrame) -> str:
    """Corpo de tab:taxonomia_erros (``I_errors_by_kind.csv``): contagem e % dos erros."""
    c = {k: int(n) for k, n in zip(by_kind["kind"], by_kind["count"])}
    fp = sum(c.get(k, 0) for k, _ in _TIPOS_FP)
    fn = sum(c.get(k, 0) for k, _ in _TIPOS_FN)
    total = fp + fn
    linhas = [
        f"        {'Acerto (verdadeiro positivo)':<36} & {c.get('match', 0)} & --- \\\\",
        "        \\hline",
        f"        \\multicolumn{{3}}{{l}}{{\\textit{{Falsos positivos ({fp})}}}} \\\\",
    ]
    for k, nome in _TIPOS_FP:
        linhas.append(f"        \\quad {nome:<30} & {c.get(k, 0):>3} & {_pct(100 * c.get(k, 0) / total):>4}\\% \\\\")
    linhas.append(f"        \\multicolumn{{3}}{{l}}{{\\textit{{Falsos negativos ({fn})}}}} \\\\")
    for k, nome in _TIPOS_FN:
        linhas.append(f"        \\quad {nome:<30} & {c.get(k, 0):>3} & {_pct(100 * c.get(k, 0) / total):>4}\\% \\\\")
    linhas += [
        "        \\hline",
        f"        {'\\textbf{Total de erros}':<36} & \\textbf{{{total}}} & \\textbf{{100,0\\%}} \\\\",
    ]
    return "\n".join(linhas)


def tabela_erros_classe(cross: pd.DataFrame) -> str:
    """Corpo de tab:cross_erros (``I_errors_label_x_kind.csv``): erros por classe e tipo."""
    linhas = []
    for lab in CLASSES:
        if lab not in set(cross["label"]):
            continue
        r = cross[cross["label"] == lab].iloc[0]
        g = lambda k: int(r[k]) if k in cross.columns else 0  # noqa: E731
        fp, fr, du, ty, so, sp = g("FP"), g("boundary"), g("duplicate"), g("type_error"), g("FN_overlap"), g("FN_no_pred")
        total = fp + fr + du + ty + so + sp
        rotulo = f"\\textsc{{{NOMES_CLASSE[lab]}}}"
        linhas.append(f"        {rotulo:<22} & {fp:>2} & {fr:>2} & {du} & {ty} & {so:>2} & {sp:>2} & {total} \\\\")
    return "\n".join(linhas)


_REFERENCIAS = [("anotador1", "Padrão-ouro (Anotador 1)"), ("anotador2", "Anotadora 2"), ("anotador3", "Anotadora 3")]


def tabela_classe_referencias(per_class: pd.DataFrame, modelos: list[str]) -> str:
    """Corpo de tab:f1_classe_referencias (``reference_sensitivity_per_class.csv``).

    Um bloco por referência: cabeçalho, linha de suporte e uma linha por modelo
    (F1 por classe + macro), com o melhor valor por coluna em negrito dentro do bloco.
    """
    blocos = []
    for ref, titulo in _REFERENCIAS:
        sub = per_class[per_class["reference"] == ref]
        if sub.empty:
            continue
        piv = sub.pivot_table(index="display", columns="label", values="f1")
        sup = sub.pivot_table(index="display", columns="label", values="support").iloc[0]
        valores = {m: [piv.loc[m, lab] for lab in CLASSES] for m in modelos if m in piv.index}
        for m in valores:
            valores[m].append(sum(valores[m]) / len(CLASSES))
        melhores = [max(valores[m][i] for m in valores) for i in range(5)]
        linhas = [
            f"        \\multicolumn{{6}}{{l}}{{\\textit{{{titulo}}}}} \\\\",
            "        Suporte ($n$) & " + " & ".join(str(int(sup[lab])) for lab in CLASSES) + f" & {int(sum(sup[lab] for lab in CLASSES))} \\\\",
        ]
        for m, vals in valores.items():
            linhas.append(
                f"        \\texttt{{{NOMES.get(m, m)}}} & "
                + " & ".join(v(x, x == melhores[i]) for i, x in enumerate(vals))
                + " \\\\"
            )
        blocos.append("\n".join(linhas))
    return "\n        \\hline\n".join(blocos)


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

    destacados = pd.read_csv(paths.EVALUATION_DIR / "J_bootstrap_paired_highlighted.csv")
    todos = pd.read_csv(paths.EVALUATION_DIR / "J_bootstrap_paired_all.csv")
    iou = pd.read_csv(paths.EVALUATION_DIR / "K_iou_sensitivity_wide.csv")
    fc_js = pd.read_csv(paths.EVALUATION_DIR / "F_fc_vs_json_overall.csv")
    prompting = pd.read_csv(paths.EVALUATION_DIR / "H_prompting_overall.csv")
    by_kind = pd.read_csv(paths.EVALUATION_DIR / "I_errors_by_kind.csv")
    cross = pd.read_csv(paths.EVALUATION_DIR / "I_errors_label_x_kind.csv")
    per_class = pd.read_csv(
        paths.RESULTS_ROOT / "experiments" / "reference_sensitivity" / "reference_sensitivity_per_class.csv"
    )
    saidas = {
        "tab_resultados_gerais": tabela_geral(principal),
        "tab_f1_entidade": tabela_entidade(entidade, quatro),
        "tab_bootstrap_paired": tabela_bootstrap(destacados),
        "tab_bootstrap_todos": tabela_bootstrap(todos),
        "tab_iou_sensitivity": tabela_iou(iou),
        "tab_saida_estruturada": tabela_fc_js(fc_js, ["deepseek-v4-flash", "gpt-4.1"]),
        "tab_tecnicas_prompting": tabela_prompting(
            prompting, ["deepseek-v4-flash", "gpt-4.1", "gpt-5.2", "qwen2.5-72b", "llama-3.3-70b"]
        ),
        "tab_taxonomia_erros": tabela_taxonomia(by_kind),
        "tab_cross_erros": tabela_erros_classe(cross),
        "tab_f1_classe_referencias": tabela_classe_referencias(
            per_class, ["DeepSeek-V4-Flash", "GPT-4.1", "LegalBert-pt"]
        ),
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
