"""LaTeX table bodies and scalar macros for the dissertation.

Emits, under ``dataset/results/models_outputs/chapter5/tex/`` (and
``chapter4/tex/`` for the corpus-analysis tables), the row blocks of every
large results table plus a ``macros_resultados.tex`` with ``\\newcommand``
definitions for the numbers cited in prose. The goal is to eliminate manual
transcription of ~200 numbers across 19 models: the ``.tex`` files can be
``\\input`` by the Overleaf project or used as verified copy-paste sources.

Conventions match the dissertation: ``\\texttt{}`` lowercase model names,
decimal comma (``0{,}731``), three decimals, best value per column in bold.

Run (after ``chapter5_numbers`` and ``corpus_analysis``):
    uv run python -m research.release.latex_fragments
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from research.release import paths

CH5 = paths.CHAPTER5_DIR
CH4 = paths.CHAPTER4_DIR
OUT5 = CH5 / "tex"
OUT4 = CH4 / "tex"

logger = logging.getLogger("research.release.latex_fragments")

# Model key -> \texttt{} name used in running text and results tables.
TEXTTT_NAMES = {
    "gpt-4.1_few_shot": "gpt-4.1",
    "gpt-4.1-mini_few_shot": "gpt-4.1-mini",
    "gpt-4.1-nano_few_shot": "gpt-4.1-nano",
    "gpt-5-mini_few_shot": "gpt-5-mini",
    "gpt-5.1_few_shot": "gpt-5.1",
    "gpt-5.2_few_shot": "gpt-5.2",
    "deepseek-v4-flash_few_shot": "deepseek-v4-flash",
    "llama-3.3-70b_few_shot": "llama-3.3-70b",
    "qwen2.5-72b_few_shot": "qwen2.5-72b",
    "rufimelo_Legal-BERTimbau-base__supervised": "legal-bertimbau-base",
    "neuralmind_bert-base-portuguese-cased__supervised": "bertimbau-base",
    "neuralmind_bert-large-portuguese-cased__supervised": "bertimbau-large",
    "bilstm-crf__supervised": "bilstm-crf",
    "alfaneo_jurisbert-base-portuguese-uncased__supervised": "jurisbert",
    "alfaneo_bertimbaulaw-base-portuguese-cased__supervised": "bertimbaulaw",
    "raquelsilveira_legalbertpt_fp__supervised": "legalbert-pt-fp",
    "ulysses-camara_legal-bert-pt-br__supervised": "legal-bert-pt-br",
    "dominguesm_legal-bert-base-cased-ptbr__supervised": "legal-bert-stf",
    "dccmpmgfinalisticas_GovBERT-BR__supervised": "govbert-br",
}

# Supervised checkpoints (mirrors research/kfold/config.py:SUPERVISED_MODELS).
SUPERVISED_CHECKPOINTS = {
    "bilstm-crf__supervised": "--- (implementação própria)",
    "neuralmind_bert-base-portuguese-cased__supervised": "neuralmind/bert-base-portuguese-cased",
    "neuralmind_bert-large-portuguese-cased__supervised": "neuralmind/bert-large-portuguese-cased",
    "rufimelo_Legal-BERTimbau-base__supervised": "rufimelo/Legal-BERTimbau-base",
    "alfaneo_jurisbert-base-portuguese-uncased__supervised": (
        "alfaneo/jurisbert-base-portuguese-uncased"
    ),
    "alfaneo_bertimbaulaw-base-portuguese-cased__supervised": (
        "alfaneo/bertimbaulaw-base-portuguese-cased"
    ),
    "raquelsilveira_legalbertpt_fp__supervised": "raquelsilveira/legalbertpt_fp",
    "ulysses-camara_legal-bert-pt-br__supervised": "ulysses-camara/legal-bert-pt-br",
    "dominguesm_legal-bert-base-cased-ptbr__supervised": "dominguesm/legal-bert-base-cased-ptbr",
    "dccmpmgfinalisticas_GovBERT-BR__supervised": "dccmpmgfinalisticas/GovBERT-BR",
}

ENTITY_ORDER = ["MULTA", "OBRIGACAO", "RECOMENDACAO", "RESSARCIMENTO"]


def _num(x: float, nd: int = 3) -> str:
    """Format a float with decimal comma for LaTeX: 0.7306 -> ``0{,}731``."""
    return f"{x:.{nd}f}".replace(".", "{,}")


def _tt(model_key: str) -> str:
    return "\\texttt{" + TEXTTT_NAMES.get(model_key, model_key) + "}"


def _is_sup(model_key: str) -> bool:
    return model_key.endswith("__supervised")


def _cell(value: float, best: float, nd: int = 3) -> str:
    s = _num(value, nd)
    return f"\\textbf{{{s}}}" if f"{value:.{nd}f}" == f"{best:.{nd}f}" else s


def _write(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("wrote %s", path)


# ----- Table bodies --------------------------------------------------------


def tab_resultados_gerais() -> pd.DataFrame:
    """Rows of ``tab:resultados_gerais`` sorted by span F1 macro (primary)."""
    df = pd.read_csv(CH5 / "C_main_results.csv").sort_values(
        "span_f1_macro", ascending=False
    )
    leader = None
    leader_csv = CH5 / "J_leader_group.csv"
    if leader_csv.exists():
        lg = pd.read_csv(leader_csv)
        leader = set(lg[lg["in_leader_group"]]["model"])
    cols = ["token_f1", "span_f1_macro", "span_f1", "span_precision", "span_recall"]
    best = {c: df[c].max() for c in cols}
    lines = []
    for _, r in df.iterrows():
        marker = "$^{\\dagger}$" if leader and r["model"] in leader else ""
        cells = " & ".join(_cell(r[c], best[c]) for c in cols)
        tipo = "Sup." if _is_sup(r["model"]) else "LLM"
        lines.append(f"{_tt(r['model'])}{marker} & {tipo} & {cells} \\\\")
    _write(OUT5 / "tab_resultados_gerais_rows.tex", lines)
    return df


def tab_f1_entidade(order: list[str]) -> None:
    """Rows of ``tab:f1_entidade`` — LLM block first, then supervised block."""
    per = pd.read_csv(CH5 / "D_per_entity.csv")
    pivot = per.pivot(index="model", columns="label", values="f1")[ENTITY_ORDER]
    best = {c: pivot[c].max() for c in ENTITY_ORDER}
    lines = []
    for block in (False, True):  # LLMs first, supervised second
        for m in order:
            if _is_sup(m) != block or m not in pivot.index:
                continue
            cells = " & ".join(_cell(pivot.loc[m, c], best[c]) for c in ENTITY_ORDER)
            lines.append(f"{_tt(m)} & {cells} \\\\")
        if not block:
            lines.append("\\hline")
    _write(OUT5 / "tab_f1_entidade_rows.tex", lines)


def tab_iou_sensitivity() -> None:
    """Rows of ``tab:iou_sensitivity`` (span F1 micro por limiar) + Spearman."""
    long_df = pd.read_csv(CH5 / "K_iou_sensitivity.csv")
    pivot = long_df.pivot(index="model", columns="iou_threshold", values="span_f1")
    pivot = pivot.sort_values("0.5", ascending=False)
    lines = []
    for m, r in pivot.iterrows():
        cells = " & ".join(_num(r[c]) for c in ("0.3", "0.5", "0.7", "exact"))
        lines.append(f"{_tt(m)} & {cells} \\\\")
    stab = pd.read_csv(CH5 / "K_iou_ranking_stability.csv").set_index("iou_threshold")
    spearman = " & ".join(
        _num(stab.loc[c, "spearman_vs_0.5"]) for c in ("0.3", "0.5", "0.7", "exact")
    )
    lines.append("\\midrule")
    lines.append(f"\\textit{{Spearman vs.\\ $0{{,}}5$}} & {spearman} \\\\")
    _write(OUT5 / "tab_iou_sensitivity_rows.tex", lines)


def tab_bootstrap_paired() -> None:
    """Rows of ``tab:bootstrap_paired`` from the highlighted-pairs family."""
    df = pd.read_csv(CH5 / "J_bootstrap_paired_highlighted.csv")
    lines = []
    for _, r in df.iterrows():
        sig = "sim" if r["sig_holm_5pct"] else "não"
        p = "$<0{,}001$" if r["p_value"] < 0.001 else _num(r["p_value"])
        p_holm = "$<0{,}001$" if r["p_holm"] < 0.001 else _num(r["p_holm"])
        lines.append(
            f"{_tt(r['model_a'])} vs.\\ {_tt(r['model_b'])} & "
            f"{_num(r['diff_f1'])} & "
            f"[{_num(r['ci_lower'])}; {_num(r['ci_upper'])}] & "
            f"{p} & {p_holm} & {sig} \\\\"
        )
    _write(OUT5 / "tab_bootstrap_paired_rows.tex", lines)


def tab_reprodutibilidade_sup() -> None:
    """Supervised rows for ``tab:reprodutibilidade_modelos`` (checkpoint ids)."""
    lines = []
    for key, ckpt in SUPERVISED_CHECKPOINTS.items():
        ckpt_tex = ckpt if ckpt.startswith("---") else "\\texttt{" + ckpt + "}"
        lines.append(f"{_tt(key)} & {ckpt_tex} \\\\")
    _write(OUT5 / "tab_reprodutibilidade_sup_rows.tex", lines)


# ----- Chapter 4 corpus tables ---------------------------------------------


def tab_corpus_chapter4() -> None:
    hist = pd.read_csv(CH4 / "A41_entities_per_doc_hist.csv")
    lines = []
    for _, r in hist.iterrows():
        pct_inf = (
            "---"
            if pd.isna(r["pct_informative_docs"])
            else _num(r["pct_informative_docs"] * 100, 1) + "\\%"
        )
        lines.append(
            f"{r['n_entities']} & {int(r['n_docs'])} & "
            f"{_num(r['pct_all_docs'] * 100, 1)}\\% & {pct_inf} \\\\"
        )
    _write(OUT4 / "tab_entidades_por_doc_rows.tex", lines)

    cooc = pd.read_csv(CH4 / "A41_cooccurrence.csv", index_col=0)
    lines = []
    for lab, r in cooc.iterrows():
        cells = " & ".join(str(int(r[c])) for c in cooc.columns)
        lines.append(f"\\textsc{{{lab.capitalize()}}} & {cells} \\\\")
    _write(OUT4 / "tab_coocorrencia_rows.tex", lines)

    pos = pd.read_csv(CH4 / "A41_span_position_summary.csv")
    lines = []
    for _, r in pos.iterrows():
        lines.append(
            f"\\textsc{{{r['label'].capitalize()}}} & {int(r['count'])} & "
            f"{_num(r['median'])} & [{_num(r['q25'])}; {_num(r['q75'])}] & "
            f"{_num(r['frac_in_final_third'] * 100, 1)}\\% \\\\"
        )
    _write(OUT4 / "tab_posicao_spans_rows.tex", lines)

    verbs = pd.read_csv(CH4 / "A41_performative_verbs.csv")
    lines = []
    for _, r in verbs.iterrows():
        cells = " & ".join(
            _num(r[f"{lab}_rate"] * 100, 1) + "\\%" for lab in ENTITY_ORDER
        )
        lines.append(
            f"\\texttt{{{r['stem']}-}} & {_num(r['doc_rate'] * 100, 1)}\\% & {cells} \\\\"
        )
    _write(OUT4 / "tab_verbos_performativos_rows.tex", lines)


# ----- Scalar macros -------------------------------------------------------


def _macro(name: str, value: str) -> str:
    return f"\\newcommand{{\\{name}}}{{{value}}}"


def macros_resultados(df_main: pd.DataFrame) -> None:
    """Scalar macros for the numbers the prose cites most."""
    df = df_main.sort_values("span_f1_macro", ascending=False).reset_index(drop=True)
    lider = df.iloc[0]
    vice = df.iloc[1]
    sup = df[df["model"].str.endswith("__supervised")]
    melhor_sup = sup.iloc[0]
    n_llm = int((~df["model"].str.endswith("__supervised")).sum())

    macros = [
        "% Gerado por research.release.latex_fragments — não editar à mão.",
        _macro("liderNome", "\\texttt{" + TEXTTT_NAMES.get(lider["model"], "") + "}"),
        _macro("liderSpanMacro", _num(lider["span_f1_macro"])),
        _macro("liderSpanMicro", _num(lider["span_f1"])),
        _macro("liderTokenF", _num(lider["token_f1"])),
        _macro("viceNome", "\\texttt{" + TEXTTT_NAMES.get(vice["model"], "") + "}"),
        _macro("viceSpanMacro", _num(vice["span_f1_macro"])),
        _macro("melhorSupNome", "\\texttt{" + TEXTTT_NAMES.get(melhor_sup["model"], "") + "}"),
        _macro("melhorSupSpanMacro", _num(melhor_sup["span_f1_macro"])),
        _macro("melhorSupSpanMicro", _num(melhor_sup["span_f1"])),
        _macro("melhorSupSpanPrec", _num(melhor_sup["span_precision"])),
        _macro("melhorSupSpanRev", _num(melhor_sup["span_recall"])),
        _macro(
            "deltaMacroLLMSup", _num(lider["span_f1_macro"] - melhor_sup["span_f1_macro"])
        ),
        _macro("deltaMicroLLMSup", _num(lider["span_f1"] - melhor_sup["span_f1"])),
        _macro("nModelosAvaliados", str(len(df))),
        _macro("nLLMAvaliados", str(n_llm)),
        _macro("nSupAvaliados", str(len(sup))),
    ]

    summary_path = CH5 / "J_bootstrap_summary.csv"
    if summary_path.exists():
        s = pd.read_csv(summary_path).set_index("metric")["value"]
        macros += [
            _macro("nParesTotal", str(int(float(s["n_total_pairs"])))),
            _macro("nParesSig", str(int(float(s["n_significant_5pct_uncorrected"])))),
        ]
        if "leader_group_size_holm" in s.index:
            macros.append(_macro("grupoLiderTam", str(int(float(s["leader_group_size_holm"])))))

    hist_path = CH4 / "A41_entities_per_doc_hist.csv"
    if hist_path.exists():
        hist = pd.read_csv(hist_path).set_index("n_entities")["n_docs"]
        n_inf = int(hist["1"] + hist["2"] + hist["3+"])
        macros += [
            _macro("nDocsCorpus", str(int(hist.sum()))),
            _macro("nDocsInformativos", str(n_inf)),
            _macro("nDocsUmaEntidade", str(int(hist["1"]))),
            _macro("nDocsDuasEntidades", str(int(hist["2"]))),
            _macro("nDocsTresMaisEntidades", str(int(hist["3+"]))),
        ]

    trans_path = CH5 / "B_transition_matrix.csv"
    if trans_path.exists():
        trans = pd.read_csv(trans_path, index_col=0)
        n_mo = int(trans.loc["I-MULTA", "I-OBRIGACAO"]) + int(
            trans.loc["I-OBRIGACAO", "I-MULTA"]
        )
        macros += [
            _macro("nTokensSinalizados", str(int(trans.values.sum()))),
            _macro("nTransMultaObrig", str(n_mo)),
        ]

    _write(OUT5 / "macros_resultados.tex", macros)


# ----- Orchestration -------------------------------------------------------


def run() -> None:
    OUT5.mkdir(parents=True, exist_ok=True)
    OUT4.mkdir(parents=True, exist_ok=True)
    df_main = tab_resultados_gerais()
    order = df_main.sort_values("span_f1_macro", ascending=False)["model"].tolist()
    tab_f1_entidade(order)
    tab_iou_sensitivity()
    tab_bootstrap_paired()
    tab_reprodutibilidade_sup()
    if (CH4 / "A41_entities_per_doc_hist.csv").exists():
        tab_corpus_chapter4()
    else:
        logger.warning("chapter4 CSVs missing — run corpus_analysis first")
    macros_resultados(df_main)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run()


if __name__ == "__main__":
    main()
