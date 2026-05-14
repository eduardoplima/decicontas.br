"""Generate the LaTeX appendix tables and the consolidated MD results brief.

Reads:
- ``dataset/results/supervised_kfold/summary/grid_*.json``  (grid search per model)
- ``dataset/results/supervised_kfold/summary/cv_*.json``    (5-fold CV per model)
- ``dataset/experiments/significance_outputs/bootstrap_ci.csv``    (LLM CIs)
- ``dataset/experiments/significance_outputs/bootstrap_paired.csv`` (LLM pairs)

Writes:
- ``docs/dissertacao/tab_grid_supervisionados.tex`` (one tabular per model)
- ``docs/dissertacao/tab_cv_supervisionados.tex``   (mean ± std span F1 + per entity)
- ``dataset/results/supervised_kfold/summary/results.md`` (LLM-consumable brief)

Re-runnable any time. Missing inputs are reported but do not abort.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

from .config import REPO_ROOT, SUMMARY_DIR, SUPERVISED_MODELS, safe_name

# When ``DECICONTAS_RESULTS_SUFFIX`` is set the bootstrap CSVs live beside
# the corrected-dataset run; the LaTeX outputs gain the same suffix so the
# legacy artefacts are preserved.
_SUFFIX = os.environ.get("DECICONTAS_RESULTS_SUFFIX", "")
LLM_CI_CSV = (
    REPO_ROOT / "dataset" / "experiments" / f"significance_outputs{_SUFFIX}" / "bootstrap_ci.csv"
)
LLM_PAIRED_CSV = (
    REPO_ROOT / "dataset" / "experiments" / f"significance_outputs{_SUFFIX}" / "bootstrap_paired.csv"
)
TEX_DIR = REPO_ROOT / "docs" / "dissertacao"
TEX_DIR.mkdir(parents=True, exist_ok=True)
_TEX_SUFFIX = _SUFFIX  # e.g. "" or "_corrected"


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def _esc(s: str) -> str:
    return (
        s.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")
        .replace("#", r"\#").replace("$", r"\$")
    )


def _model_display(model: str) -> str:
    if model == "bilstm-crf":
        return "BiLSTM-CRF"
    return {
        "neuralmind/bert-base-portuguese-cased": "BERTimbau-base",
        "neuralmind/bert-large-portuguese-cased": "BERTimbau-large",
        "rufimelo/Legal-BERTimbau-base": "Legal-BERTimbau-base",
    }.get(model, model)


def _format_config(cfg: dict[str, Any]) -> str:
    keys = [k for k in cfg.keys() if k not in ("model_name", "max_epochs", "patience", "max_len",
                                               "max_length", "epochs", "weight_decay", "max_grad_norm",
                                               "early_stopping_patience", "grad_clip", "grad_accum",
                                               "per_device_batch_size")]
    if not keys:
        keys = list(cfg.keys())
    parts = []
    for k in keys:
        v = cfg[k]
        if isinstance(v, float):
            v = f"{v:g}"
        parts.append(f"{k}={v}")
    return ", ".join(parts)


def render_grid_tex(grid_summaries: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("% Auto-gerado por build_report.py — NÃO EDITAR À MÃO")
    for s in grid_summaries:
        model = s["model"]
        rows = s["rows"]
        lines.append("")
        lines.append("\\begin{table}[ht]")
        lines.append("  \\centering\\small")
        lines.append(
            f"  \\caption{{{_esc(_model_display(model))}: F1 de \\emph{{span}} no "
            f"\\emph{{dev}} para cada configuração avaliada.}}"
        )
        lines.append(f"  \\label{{tab:grid-{safe_name(model)}}}")
        lines.append("  \\begin{tabular}{lcccc}")
        lines.append("    \\hline")
        lines.append("    \\textbf{Configuração} & \\textbf{F1\\textsubscript{span}} "
                     "& \\textbf{Prec.} & \\textbf{Rec.} & \\textbf{F1\\textsubscript{tok}} \\\\")
        lines.append("    \\hline")
        for r in rows:
            cfg_str = _esc(_format_config(r["config"]))
            best = r is rows[0]
            row_fmt = (
                f"    {cfg_str} & {r['span_f1']:.4f} & {r['span_precision']:.4f} "
                f"& {r['span_recall']:.4f} & {r['token_f1']:.4f} \\\\"
            )
            if best:
                row_fmt = row_fmt.replace("\\\\", r" \textbf{(escolhida)} \\")
            lines.append(row_fmt)
        lines.append("    \\hline")
        lines.append("  \\end{tabular}")
        lines.append("\\end{table}")
    return "\n".join(lines) + "\n"


def render_cv_tex(cv_summaries: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("% Auto-gerado por build_report.py — NÃO EDITAR À MÃO")
    lines.append("\\begin{table}[ht]")
    lines.append("  \\centering\\small")
    lines.append(
        "  \\caption{Modelos supervisionados — F1 de \\emph{span} "
        "(IoU $\\geq$ 0.5) e F1 token-level via 5-fold CV "
        "($\\mathrm{seed} = 1007$). Reportamos média $\\pm$ desvio-padrão "
        "entre \\emph{folds} e a configuração vencedora do \\emph{grid search}.}"
    )
    lines.append("  \\label{tab:cv-supervisionados}")
    lines.append("  \\begin{tabular}{lccc}")
    lines.append("    \\hline")
    lines.append("    \\textbf{Modelo} & \\textbf{F1\\textsubscript{span}} "
                 "& \\textbf{F1\\textsubscript{tok}} & \\textbf{Configuração escolhida} \\\\")
    lines.append("    \\hline")
    for s in cv_summaries:
        name = _esc(_model_display(s["model"]))
        sf = s["span_f1"]
        tf = s["token_f1"]
        cfg = _esc(_format_config(s["config"]))
        lines.append(
            f"    {name} & {sf['mean']:.4f} $\\pm$ {sf['std']:.4f} "
            f"& {tf['mean']:.4f} $\\pm$ {tf['std']:.4f} & {cfg} \\\\"
        )
    lines.append("    \\hline")
    lines.append("  \\end{tabular}")
    lines.append("\\end{table}")
    return "\n".join(lines) + "\n"


def render_md(
    cv_summaries: list[dict[str, Any]],
    grid_summaries: list[dict[str, Any]],
    llm_ci: list[dict[str, str]],
    llm_paired: list[dict[str, str]],
) -> str:
    out: list[str] = []
    out.append("# Resultados consolidados — decicontas.br\n")
    out.append("Briefing pronto para consumo por uma LLM redatora do capítulo de Resultados. ")
    out.append("Cobre os modelos supervisionados (5-fold CV após grid search) e as LLMs ")
    out.append("(bootstrap pareado de documento), todos avaliados sobre os mesmos 861 documentos.\n")

    out.append("\n## Setup do experimento\n")
    out.append("- Dataset: 861 documentos (866 rotulados originais menos 5 IDs `[6, 782, 790, 817, 852]` ")
    out.append("excluídos por aparecerem como exemplos few-shot no prompt das LLMs).\n")
    out.append("- Métrica primária: F1 de **span** com IoU ≥ 0.5, calculada via tokenização spaCy ")
    out.append("`pt_core_news_sm` (mesmo pipeline `research.ner_metrics.calculate_metrics` em todos os modelos).\n")
    out.append("- Random seed: **1007** (todos os splits, shuffles e inits).\n")
    out.append("- Supervisionados: protocolo em duas etapas — grid search em split fixo 80/20 ")
    out.append("(estratificado por presença de anotação) seguido de 5-fold CV com a config vencedora.\n")
    out.append("- LLMs: zero/few-shot (12 exemplos no prompt), avaliados via bootstrap de documento ")
    out.append("(B=10.000, IoU ≥ 0.5).\n")

    out.append("\n## Modelos supervisionados — 5-fold CV\n")
    if cv_summaries:
        out.append("| Modelo | Span F1 (média ± dp) | Token F1 (média ± dp) | Configuração escolhida | Folds |\n")
        out.append("|---|---|---|---|---|\n")
        for s in cv_summaries:
            sf = s["span_f1"]
            tf = s["token_f1"]
            cfg = _format_config(s["config"])
            folds_str = ", ".join(f"{v:.3f}" for v in sf["values"])
            out.append(
                f"| {_model_display(s['model'])} | "
                f"{sf['mean']:.4f} ± {sf['std']:.4f} | "
                f"{tf['mean']:.4f} ± {tf['std']:.4f} | `{cfg}` | {folds_str} |\n"
            )
        out.append("\n### F1 por entidade (média entre folds)\n")
        entity_keys: list[str] = []
        for s in cv_summaries:
            for fm in s["fold_metrics"]:
                for k in fm.get("per_entity_f1", {}):
                    if k not in entity_keys:
                        entity_keys.append(k)
        if entity_keys:
            out.append("| Modelo | " + " | ".join(entity_keys) + " |\n")
            out.append("|" + "---|" * (len(entity_keys) + 1) + "\n")
            for s in cv_summaries:
                vals = []
                for k in entity_keys:
                    fold_vals = [fm.get("per_entity_f1", {}).get(k) for fm in s["fold_metrics"]]
                    fold_vals = [v for v in fold_vals if v is not None]
                    if fold_vals:
                        vals.append(f"{sum(fold_vals) / len(fold_vals):.4f}")
                    else:
                        vals.append("—")
                out.append(f"| {_model_display(s['model'])} | " + " | ".join(vals) + " |\n")
    else:
        out.append("_Nenhum resumo de CV encontrado em `dataset/results/supervised_kfold/summary/cv_*.json`._\n")

    out.append("\n## Grid search dos supervisionados — F1 de span no dev\n")
    for gs in grid_summaries:
        out.append(f"\n### {_model_display(gs['model'])}\n")
        out.append("| Configuração | Span F1 dev | Prec | Rec | Token F1 |\n")
        out.append("|---|---|---|---|---|\n")
        for r in gs["rows"]:
            cfg = _format_config(r["config"])
            marker = " **(escolhida)**" if r is gs["rows"][0] else ""
            out.append(
                f"| `{cfg}` | {r['span_f1']:.4f} | {r['span_precision']:.4f} | "
                f"{r['span_recall']:.4f} | {r['token_f1']:.4f} |{marker}\n"
            )

    out.append("\n## Leaderboard unificado — bootstrap CIs (95%)\n")
    out.append("Todos os modelos (LLMs e supervisionados) avaliados sob o mesmo bootstrap de documento ")
    out.append("(B=10.000, IoU ≥ 0.5). Para os supervisionados, as predições são as out-of-fold do ")
    out.append("5-fold CV — coerentes com a média±dp reportada na seção anterior, mas com IC ")
    out.append("calculado por reamostragem de documentos.\n\n")
    if llm_ci:
        out.append("| Modelo | Span F1 (pontual) | IC 95% | Largura IC |\n")
        out.append("|---|---|---|---|\n")
        for r in llm_ci:
            f1 = float(r["span_f1_point"])
            lo = float(r["ci_lower"])
            hi = float(r["ci_upper"])
            out.append(
                f"| {r['display_name']} | {f1:.4f} | [{lo:.3f}; {hi:.3f}] | {hi - lo:.4f} |\n"
            )
    else:
        out.append("_Arquivo `bootstrap_ci.csv` ausente._\n")

    out.append("\n## Comparações pareadas — bootstrap (top 15 por |Δ|)\n")
    out.append("Diferenças significativas a 5% via bootstrap pareado de documento. ")
    out.append("Inclui pares LLM-LLM, LLM-supervisionado e supervisionado-supervisionado.\n\n")
    if llm_paired:
        out.append("| A | B | Δ F1 | IC 95% (diff) | p-valor | Sig. (5%) |\n")
        out.append("|---|---|---|---|---|---|\n")
        for r in llm_paired[:15]:
            sig = "✓" if r["significant_95"] in ("True", "true", "1") else "—"
            out.append(
                f"| {r['display_a']} | {r['display_b']} | {float(r['diff_f1']):+.4f} | "
                f"[{float(r['ci_lower']):+.3f}; {float(r['ci_upper']):+.3f}] | "
                f"{float(r['p_value']):.4f} | {sig} |\n"
            )

    out.append("\n## Notas para a redação\n")
    out.append("- Os modelos supervisionados (BiLSTM/BERT) foram fine-tunados nos 861 documentos via ")
    out.append("5-fold CV; LLMs foram avaliadas em regime few-shot. A comparação mede paradigmas, ")
    out.append("não modelos sob \"mesmas condições\".\n")
    out.append("- O F1 de span usa correspondência IoU ≥ 0.5 com tokenização spaCy comum a todos os ")
    out.append("modelos — diferenças de ranking entre modelos vêm da qualidade de extração, não de ")
    out.append("variação de protocolo de avaliação.\n")
    out.append("- Para os supervisionados, a média ± dp entre folds quantifica variância entre splits; ")
    out.append("para LLMs, o IC bootstrap quantifica variância entre documentos.\n")
    return "".join(out)


def main() -> None:
    cv_summaries: list[dict[str, Any]] = []
    grid_summaries: list[dict[str, Any]] = []
    for m in SUPERVISED_MODELS:
        cv = _load_json(SUMMARY_DIR / f"cv_{safe_name(m)}.json")
        if cv:
            cv_summaries.append(cv)
        gs = _load_json(SUMMARY_DIR / f"grid_{safe_name(m)}.json")
        if gs:
            grid_summaries.append(gs)

    llm_ci = _load_csv(LLM_CI_CSV)
    llm_paired = _load_csv(LLM_PAIRED_CSV)
    if llm_paired:
        llm_paired = sorted(llm_paired, key=lambda r: abs(float(r["diff_f1"])), reverse=True)

    if grid_summaries:
        out = TEX_DIR / f"tab_grid_supervisionados{_TEX_SUFFIX}.tex"
        out.write_text(render_grid_tex(grid_summaries))
        print(f"[wrote] {out}")
    if cv_summaries:
        out = TEX_DIR / f"tab_cv_supervisionados{_TEX_SUFFIX}.tex"
        out.write_text(render_cv_tex(cv_summaries))
        print(f"[wrote] {out}")

    md_path = SUMMARY_DIR / "results.md"
    md_path.write_text(render_md(cv_summaries, grid_summaries, llm_ci, llm_paired))
    print(f"[wrote] {md_path}")

    if not cv_summaries:
        print("[note] No CV summaries — generated MD reflects partial state.")


if __name__ == "__main__":
    main()
