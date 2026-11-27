"""Geração de figuras e snippets LaTeX a partir de artigos_extraidos.csv."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


TECNICA_LABEL = {
    "regras": "Regras",
    "crf": "CRF",
    "bilstm_crf": "BiLSTM-CRF",
    "transformer_generico": "Transformer (genérico)",
    "transformer_dominio": "Transformer (domínio)",
    "llm_zero_shot": "LLM zero-shot",
    "llm_few_shot": "LLM few-shot",
    "hibrido": "Híbrido",
}

IDIOMA_LABEL = {
    "en": "Inglês",
    "pt": "Português",
    "zh": "Chinês",
    "de": "Alemão",
    "fr": "Francês",
    "it": "Italiano",
    "es": "Espanhol",
    "ja": "Japonês",
    "ar": "Árabe",
    "ro": "Romeno",
    "ru": "Russo",
    "uk": "Ucraniano",
    "tr": "Turco",
    "uz": "Uzbeque",
    "th": "Tailandês",
    "vi": "Vietnamita",
    "id": "Indonésio",
    "nl": "Holandês",
    "ND": "Não definido",
}


def _codigos_idioma(s: str) -> list[str]:
    """Separa 'en, pt' / 'zh; en' na lista de códigos ISO 639-1."""
    if not isinstance(s, str) or not s.strip():
        return []
    return [p.strip().lower() for p in s.replace(";", ",").split(",") if p.strip()]


def _idioma_extenso(s: str, sep: str = ", ") -> str:
    """Mapeia código(s) ISO 639-1 para nome em português.

    Aceita formas compostas separadas por ',' ou ';' (ex.: 'en, pt' ou 'zh; en').
    """
    codigos = _codigos_idioma(s)
    if not codigos:
        return IDIOMA_LABEL["ND"]
    return sep.join(IDIOMA_LABEL.get(c, c) for c in codigos)


SUBDOMINIO_LABEL = {
    "legislacao": "Legislação",
    "decisoes_judiciais": "Decisões judiciais",
    "contratos": "Contratos",
    "regulacao_compliance": "Regulação/Compliance",
    "tribunais_administrativos": "Tribunais administrativos",
    "tributario": "Tributário",
    "criminal": "Criminal",
    "outros": "Outros",
}


def _save(fig, base: Path) -> None:
    base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".png"), bbox_inches="tight", dpi=150)
    plt.close(fig)


def fig_dist_artigos_anos(df: pd.DataFrame, out: Path) -> None:
    cnt = df.loc[df["ano"] > 0, "ano"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(cnt.index.astype(int).astype(str), cnt.values, color="#4c78a8")
    ax.set_xlabel("Ano")
    ax.set_ylabel("Nº de artigos")
    ax.set_title("Distribuição de artigos incluídos por ano")
    for i, v in enumerate(cnt.values):
        ax.text(i, v + 0.1, str(v), ha="center", va="bottom", fontsize=9)
    _save(fig, out)


def _bubble(
    df: pd.DataFrame,
    x: str,
    y: str,
    x_label: str,
    y_label: str,
    out: Path,
    x_order=None,
    y_order=None,
) -> None:
    g = df.groupby([x, y]).size().reset_index(name="n")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    if x_order is None:
        x_order = sorted(g[x].unique())
    if y_order is None:
        y_order = sorted(g[y].unique())
    x_idx = {v: i for i, v in enumerate(x_order)}
    y_idx = {v: i for i, v in enumerate(y_order)}
    xs = [x_idx[v] for v in g[x]]
    ys = [y_idx[v] for v in g[y]]
    sizes = (g["n"] * 90).tolist()
    ax.scatter(xs, ys, s=sizes, alpha=0.6, color="#4c78a8", edgecolor="#1f3a5a")
    for xi, yi, n in zip(xs, ys, g["n"]):
        ax.text(xi, yi, str(int(n)), ha="center", va="center", fontsize=8, color="white")
    ax.set_xticks(range(len(x_order)))
    ax.set_xticklabels([str(v) for v in x_order], rotation=30, ha="right")
    ax.set_yticks(range(len(y_order)))
    ax.set_yticklabels([str(v) for v in y_order])
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(True, alpha=0.3, linestyle=":")
    _save(fig, out)


def fig_bubble_tecnica_ano(df: pd.DataFrame, out: Path) -> None:
    d = df.copy()
    d["tecnica_lbl"] = d["tecnica_principal"].map(TECNICA_LABEL).fillna(d["tecnica_principal"])
    d = d[d["ano"] > 0]
    anos = sorted(d["ano"].dropna().astype(int).unique().tolist())
    tecnicas = [TECNICA_LABEL[k] for k in TECNICA_LABEL if TECNICA_LABEL[k] in d["tecnica_lbl"].values]
    _bubble(d, "ano", "tecnica_lbl", "Ano", "Técnica", out, x_order=anos, y_order=tecnicas)


def fig_bubble_tecnica_subdominio(df: pd.DataFrame, out: Path) -> None:
    d = df.copy()
    d["tecnica_lbl"] = d["tecnica_principal"].map(TECNICA_LABEL).fillna(d["tecnica_principal"])
    d["sub_lbl"] = d["subdominio"].map(SUBDOMINIO_LABEL).fillna(d["subdominio"])
    subs = [SUBDOMINIO_LABEL[k] for k in SUBDOMINIO_LABEL if SUBDOMINIO_LABEL[k] in d["sub_lbl"].values]
    tecnicas = [TECNICA_LABEL[k] for k in TECNICA_LABEL if TECNICA_LABEL[k] in d["tecnica_lbl"].values]
    _bubble(d, "sub_lbl", "tecnica_lbl", "Subdomínio", "Técnica", out, x_order=subs, y_order=tecnicas)


def fig_cross_idioma_subdominio(df: pd.DataFrame, out: Path) -> None:
    d = df.copy()
    d["idioma_corpus"] = d["idioma_corpus"].fillna("ND").map(_idioma_extenso)
    d["sub_lbl"] = d["subdominio"].map(SUBDOMINIO_LABEL).fillna(d["subdominio"])
    pivot = pd.crosstab(d["idioma_corpus"], d["sub_lbl"])
    fig, ax = plt.subplots(figsize=(9, max(3, 0.45 * len(pivot))))
    sns.heatmap(pivot, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax)
    ax.set_xlabel("Subdomínio")
    ax.set_ylabel("Idioma do corpus")
    ax.set_title("Idioma × Subdomínio (contagem de artigos)")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    _save(fig, out)


def fig_dist_f1_por_tecnica(df: pd.DataFrame, out: Path) -> None:
    d = df.dropna(subset=["f1_melhor_reportado"]).copy()
    d["tecnica_lbl"] = d["tecnica_principal"].map(TECNICA_LABEL).fillna(d["tecnica_principal"])
    counts = d["tecnica_lbl"].value_counts()
    keep = counts[counts >= 3].index.tolist()
    d = d[d["tecnica_lbl"].isin(keep)]
    if d.empty:
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.text(0.5, 0.5, "n < 3 em todas as técnicas", ha="center", va="center")
        ax.set_axis_off()
        _save(fig, out)
        return
    order = [TECNICA_LABEL[k] for k in TECNICA_LABEL if TECNICA_LABEL[k] in keep]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.boxplot(data=d, x="tecnica_lbl", y="f1_melhor_reportado", order=order, ax=ax, color="#4c78a8")
    mediana_global = d["f1_melhor_reportado"].median()
    ax.axhline(mediana_global, ls="--", color="gray",
               label=f"mediana global = {mediana_global:.1f}")
    ax.set_xlabel("Técnica")
    ax.set_ylabel("F1 melhor reportado (%)")
    ax.set_title("F1 por família de técnica (técnicas com n ≥ 3)")
    ax.legend()
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    _save(fig, out)


def gerar_figuras(df: pd.DataFrame, fig_dir: Path) -> None:
    fig_dist_artigos_anos(df, fig_dir / "dist_artigos_anos")
    fig_bubble_tecnica_ano(df, fig_dir / "bubble_tecnica_ano")
    fig_bubble_tecnica_subdominio(df, fig_dir / "bubble_tecnica_subdominio")
    fig_cross_idioma_subdominio(df, fig_dir / "cross_idioma_subdominio")
    fig_dist_f1_por_tecnica(df, fig_dir / "dist_f1_por_tecnica")


def _fmt_pct(x: float) -> str:
    return f"{x:.1f}".replace(".", "{,}") + r"\%"


def _fmt_int(n) -> str:
    return str(int(n))


def _latex_escape(s: str) -> str:
    if not isinstance(s, str):
        return ""
    return (
        s.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("$", r"\$")
        .replace("#", r"\#")
        .replace("_", r"\_")
        .replace("{", r"\{")
        .replace("}", r"\}")
    )


def gerar_inline_stats(df: pd.DataFrame, out: Path) -> None:
    total = len(df)
    tecnicas = df["tecnica_principal"]

    transformer_mask = tecnicas.isin(["transformer_generico", "transformer_dominio"])
    llm_mask = tecnicas.isin(["llm_zero_shot", "llm_few_shot"])
    hibrido_mask = tecnicas.eq("hibrido")

    perc_transformer = transformer_mask.sum() / total * 100 if total else 0
    perc_llm = llm_mask.sum() / total * 100 if total else 0
    perc_hibrido = hibrido_mask.sum() / total * 100 if total else 0

    med_f_trans = df.loc[transformer_mask, "f1_melhor_reportado"].dropna().median()
    med_f_bilstm = df.loc[tecnicas.eq("bilstm_crf"), "f1_melhor_reportado"].dropna().median()

    n_tribunal = int(df["subdominio"].eq("tribunais_administrativos").sum())
    n_pt = int(df["idioma_corpus"].fillna("").str.contains("pt", case=False).sum())
    n_pub = int((df["corpus_publico"] == True).sum())  # noqa: E712
    anos_validos = df.loc[df["ano"] > 0, "ano"].dropna()
    ano_med = int(anos_validos.median()) if not anos_validos.empty else 0

    def _opt_pct(v):
        return _fmt_pct(v) if pd.notna(v) else "ND"

    lines = [
        r"% Gerado automaticamente — não editar à mão",
        rf"\newcommand{{\totalIncluidos}}{{{_fmt_int(total)}}}",
        rf"\newcommand{{\percTransformer}}{{{_fmt_pct(perc_transformer)}}}",
        rf"\newcommand{{\percLLM}}{{{_fmt_pct(perc_llm)}}}",
        rf"\newcommand{{\percHibrido}}{{{_fmt_pct(perc_hibrido)}}}",
        rf"\newcommand{{\medianaFTransformer}}{{{_opt_pct(med_f_trans)}}}",
        rf"\newcommand{{\medianaFBilstm}}{{{_opt_pct(med_f_bilstm)}}}",
        rf"\newcommand{{\nArtigosTribunalContas}}{{{_fmt_int(n_tribunal)}}}",
        rf"\newcommand{{\nArtigosPortugues}}{{{_fmt_int(n_pt)}}}",
        rf"\newcommand{{\nArtigosCorpusPublico}}{{{_fmt_int(n_pub)}}}",
        rf"\newcommand{{\anoMedianaPub}}{{{ano_med}}}",
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def gerar_lacunas(out: Path) -> None:
    body = (
        r"\begin{itemize}" "\n"
        r"  \item Apenas \nArtigosTribunalContas{} dos \totalIncluidos{} artigos analisados "
        r"tratam de tribunais administrativos ou Cortes de Contas." "\n"
        r"  \item Em português jurídico, foram identificados \nArtigosPortugues{} estudos, "
        r"a maioria voltada a decisões judiciais ou textos legislativos." "\n"
        r"  \item Apenas \nArtigosCorpusPublico{} artigos disponibilizam o corpus utilizado, "
        r"o que limita a reprodutibilidade dos resultados." "\n"
        r"\end{itemize}" "\n"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")


def _normalizar_referencia(ref: str) -> str:
    """Substitui '(nao_reportado)' / '(None)' por '(s.d.)' em refs com ano ausente."""
    if not isinstance(ref, str):
        return ""
    return (
        ref.replace("(nao_reportado)", "(s.d.)")
        .replace("(None)", "(s.d.)")
    )


def _chave_titulo(s: str) -> str:
    """Normaliza um título para casamento com o mapa de citekeys."""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def carregar_citekeys(path: Path | None) -> dict[str, str]:
    """Lê data/revisao/citekeys.csv (titulo, citekey) → {titulo normalizado: citekey}.

    O arquivo é curado à mão: é a ponte entre o corpus extraído e as chaves do
    refs_*.bib da tese. Ausente ou incompleto, a tabela cai para autor-ano.
    """
    if path is None or not Path(path).exists():
        return {}
    m = pd.read_csv(path)
    return {
        _chave_titulo(r["titulo"]): str(r["citekey"]).strip()
        for _, r in m.iterrows()
        if isinstance(r.get("citekey"), str) and r["citekey"].strip()
    }


#: acima de quantos idiomas a célula vira "Multilíngue" + nota de rodapé
_MAX_IDIOMAS_INLINE = 2


def gerar_tab_resumo(df: pd.DataFrame, out: Path, citekeys_path: Path | None = None) -> None:
    citekeys = carregar_citekeys(citekeys_path)
    d = df.copy()
    d["tecnica_lbl"] = d["tecnica_principal"].map(TECNICA_LABEL).fillna(d["tecnica_principal"])
    d["sub_lbl"] = d["subdominio"].map(SUBDOMINIO_LABEL).fillna(d["subdominio"])
    d["ano_sort"] = d["ano"].where(d["ano"] > 0, 9999)
    d = d.sort_values(["ano_sort", "referencia_curta"], na_position="last").reset_index(drop=True)
    d["referencia_curta"] = d["referencia_curta"].map(_normalizar_referencia)

    rows: list[str] = []
    notas: list[str] = []
    sem_citekey: list[str] = []
    for _, r in d.iterrows():
        chave = citekeys.get(_chave_titulo(r["titulo"]))
        if chave:
            ref = rf"\citeonline{{{chave}}}"
        else:
            sem_citekey.append(str(r["titulo"]))
            ref = _latex_escape(str(r.get("referencia_curta", "")))

        codigos = _codigos_idioma(r.get("idioma_corpus"))
        if len(codigos) > _MAX_IDIOMAS_INLINE:
            marcador = chr(ord("a") + len(notas))
            nomes = [IDIOMA_LABEL.get(c, c) for c in codigos]
            # primeiro em maiúscula (início da nota), demais em caixa baixa e o
            # último ligado por "e": "Inglês, português, alemão, turco e ucraniano"
            lista = ", ".join([nomes[0]] + [n.lower() for n in nomes[1:-1]])
            lista = f"{lista} e {nomes[-1].lower()}"
            notas.append(rf"{{\footnotesize $^{{{marcador}}}$\,{lista}.\par}}")
            idioma = rf"Multilíngue\,$^{{{marcador}}}$"
        else:
            idioma = _latex_escape(_idioma_extenso(r.get("idioma_corpus"), sep="/"))

        rows.append(
            "  "
            + " & ".join(
                [ref, _latex_escape(str(r["sub_lbl"])), idioma, _latex_escape(str(r["tecnica_lbl"]))]
            )
            + r" \\"
        )

    if sem_citekey:
        print(f"aviso: {len(sem_citekey)} artigo(s) sem citekey em {citekeys_path}:")
        for t in sem_citekey:
            print(f"  - {t}")

    cabecalho = r"Referência & Subdomínio & Idioma do corpus & Técnica \\"
    body = (
        r"% Tabela longtable — requer \usepackage{longtable, booktabs}" "\n"
        r"% Gerado por tools/revisao_analise.py — não editar à mão." "\n"
        r"% Coluna Referência vem de data/revisao/citekeys.csv (chaves do refs_*.bib)." "\n"
        r"\begingroup\footnotesize" "\n"
        r"\setlength{\tabcolsep}{4pt}" "\n"
        r"\begin{longtable}{p{0.36\linewidth}p{0.20\linewidth}p{0.18\linewidth}p{0.18\linewidth}}" "\n"
        r"\caption{Artigos incluídos no mapeamento sistemático.}" "\n"
        r"\label{tab:resumo-artigos}\\" "\n"
        r"\toprule" "\n"
        + cabecalho + "\n"
        r"\midrule" "\n"
        r"\endfirsthead" "\n"
        r"\multicolumn{4}{c}{\tablename\ \thetable\ -- \textit{continuação}}\\" "\n"
        r"\toprule" "\n"
        + cabecalho + "\n"
        r"\midrule" "\n"
        r"\endhead" "\n"
        r"\midrule" "\n"
        r"\multicolumn{4}{r}{\textit{continua na próxima página}} \\" "\n"
        r"\endfoot" "\n"
        r"\bottomrule" "\n"
        r"\endlastfoot" "\n"
        + "\n".join(rows) + "\n"
        r"\end{longtable}" "\n"
        + ("\\vspace{-0.5em}\n" + "\n".join(notas) + "\n" if notas else "")
        + r"\endgroup" "\n"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")


def gerar_tab_status_fontes(xlsx_path: Path, out: Path) -> None:
    """Tabela status × source ao fim da triagem por título e resumo.

    Reporta exatamente o que está em `todos_artigos.xlsx`. As exclusões da fase
    de elegibilidade (texto completo) não entram aqui: estão em
    `data/revisao/exclusoes_elegibilidade.csv`.
    """
    df = pd.read_excel(xlsx_path)
    cross = df.groupby(["status", "source"]).size().unstack(fill_value=0)

    sources = ["ACM", "IEEE", "Scopus"]
    cross = cross.reindex(columns=sources, fill_value=0)
    cross = cross.reindex(["Accepted", "Duplicated", "Rejected"], fill_value=0)

    aceito = cross.loc["Accepted"]
    duplic = cross.loc["Duplicated"]
    rejeit = cross.loc["Rejected"]
    total = aceito + duplic + rejeit

    def linha(rotulo, ser):
        cells = [f"{int(ser[s]):>3}" for s in sources] + [f"{int(ser.sum()):>3}"]
        return f"{rotulo:<9} & " + " & ".join(cells) + r" \\"

    body = (
        r"\begin{table}[h]" "\n"
        r"\centering" "\n"
        r"\caption{Status dos artigos por fonte de dados após a triagem por título e resumo.}" "\n"
        r"\label{tab:status_fontes}" "\n"
        r"\begin{tabular}{lrrrr}" "\n"
        r"\toprule" "\n"
        r"Status & ACM & IEEE & Scopus & Total \\" "\n"
        r"\midrule" "\n"
        + linha("Aceito", aceito) + "\n"
        + linha("Duplicado", duplic) + "\n"
        + linha("Rejeitado", rejeit) + "\n"
        + r"\midrule" + "\n"
        + linha("Identificado", total) + "\n"
        + r"\bottomrule" + "\n"
        + r"\end{tabular}" + "\n"
        + r"\end{table}" + "\n"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")


def gerar_latex(
    df: pd.DataFrame,
    latex_dir: Path,
    xlsx_path: Path | None = None,
    citekeys_path: Path | None = None,
) -> None:
    gerar_inline_stats(df, latex_dir / "inline_stats.tex")
    gerar_lacunas(latex_dir / "lacunas_quantitativas.tex")
    gerar_tab_resumo(df, latex_dir / "tab_resumo_artigos.tex", citekeys_path=citekeys_path)
    if xlsx_path is not None:
        gerar_tab_status_fontes(xlsx_path, latex_dir / "tab_status_fontes.tex")
