"""Sensibilidade do ranking à escolha da anotação de referência.

O gold do corpus é a anotação do primeiro autor (A1), auditada por confident
learning. Duas servidoras da unidade que alimenta o CGAD reanotaram o corpus
inteiro de forma independente e cega (A2, A3), e as divergências nunca foram
adjudicadas. Os pareceres da JURIX apontam, com razão, que uma conclusão de
superioridade medida contra A1 pode estar medindo aderência à política de
anotação de A1 em vez de qualidade de extração.

Este script repontua as MESMAS predições de todos os modelos contra cada uma
das três referências e reporta, por referência: o F1 de span macro e micro de
cada modelo, o ranking, o Spearman contra o ranking obtido com A1, e o
contraste central entre o melhor LLM e o melhor encoder.

Nada aqui re-executa modelo: só muda o gold contra o qual as predições
existentes são comparadas.

Com ``--per-class``, grava também ``reference_sensitivity_per_class.csv``:
precisão, revocação, F1 e suporte de cada classe por (modelo, referência),
com o mesmo pareamento. Como o pareamento exige rótulo igual, ele se decompõe
exatamente por classe, e a média dos quatro F1 reproduz o macro do CSV
agregado (a checagem é impressa ao final).

Uso:
    uv run python scripts/reference_sensitivity.py
    uv run python scripts/reference_sensitivity.py --per-class
    uv run python scripts/reference_sensitivity.py --per-class --models \\
        deepseek-v4-flash_few_shot raquelsilveira_legalbertpt_fp__supervised
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

from research.dataset_io import collapse_label
from research.ner_metrics import bipartite_greedy_match
from research.release import paths
from research.release.annotator_agreement import ANNOTATOR_IDS, load_annotator
from research.release.evaluation_numbers import (
    DISPLAY_NAMES,
    MODELS,
    _load_llm_df,
    _load_supervised_df,
    _is_supervised_model,
    _drop_fewshot,
)

logger = logging.getLogger("reference_sensitivity")

OUT_DIR = paths.RAW_EXPERIMENTS_DIR / "reference_sensitivity"
IOU = 0.5
ENTITY_LABELS = ("MULTA", "OBRIGACAO", "RESSARCIMENTO", "RECOMENDACAO")


def reference_token_spans() -> dict[str, dict[int, list[tuple[int, int, str]]]]:
    """``{anotador: {release_index: [(tok_start, tok_end, label)]}}``.

    Os três anotadores cobrem os mesmos 861 documentos; a ordem do release
    (ordenada por id) define o índice usado para casar com as predições, que
    já vêm sem as cinco posições de few-shot.
    """
    release = sorted(
        json.loads(paths.CORRECTED_GOLD_JSON.read_text(encoding="utf-8")),
        key=lambda d: d["id"],
    )
    id_to_index = {doc["id"]: i for i, doc in enumerate(release)}

    out: dict[str, dict[int, list[tuple[int, int, str]]]] = {}
    for name in ANNOTATOR_IDS:
        docs = load_annotator(paths.ANNOTATORS_DIR / f"{name}.jsonl")
        per_doc: dict[int, list[tuple[int, int, str]]] = {}
        for doc_id, rec in docs.items():
            idx = id_to_index.get(doc_id)
            if idx is None:
                continue
            per_doc[idx] = [
                (s, e, collapse_label(lab)) for s, e, lab in rec["token_spans"]
            ]
        out[name] = per_doc
    return out


def per_class_counts(
    pred_by_doc: dict[int, list], gold_by_doc: dict[int, list]
) -> dict[str, dict[str, int]]:
    """``{classe: {tp, fp, fn}}`` das predições contra uma referência.

    Pareamento guloso bipartido com IoU >= 0,5 e rótulo igual, documento a
    documento. É a única função que pareia; ``score_against`` e
    ``per_class_scores`` só agregam estas contagens, de modo que o macro
    reportado e a decomposição por classe nunca podem divergir.
    """
    per_class = {lab: {"tp": 0, "fp": 0, "fn": 0} for lab in ENTITY_LABELS}
    for idx, gold in gold_by_doc.items():
        pred = pred_by_doc.get(idx, [])
        matched = bipartite_greedy_match(pred, gold, iou_threshold=IOU)
        matched_p = {p for p, _ in matched}
        matched_g = {g for _, g in matched}
        for p_i, _ in matched:
            per_class[pred[p_i][2]]["tp"] += 1
        for i, sp in enumerate(pred):
            if i not in matched_p:
                per_class[sp[2]]["fp"] += 1
        for i, sp in enumerate(gold):
            if i not in matched_g:
                per_class[sp[2]]["fn"] += 1
    return per_class


def score_against(pred_by_doc: dict[int, list], gold_by_doc: dict[int, list]) -> dict:
    """F1 de span micro e macro das predições contra uma referência."""
    per_class = per_class_counts(pred_by_doc, gold_by_doc)

    tp = sum(c["tp"] for c in per_class.values())
    fp = sum(c["fp"] for c in per_class.values())
    fn = sum(c["fn"] for c in per_class.values())
    micro = 2 * tp / (2 * tp + fp + fn) if tp else 0.0

    f1s = []
    for lab in ENTITY_LABELS:
        c = per_class[lab]
        d = 2 * c["tp"] + c["fp"] + c["fn"]
        f1s.append(2 * c["tp"] / d if d else 0.0)
    return {"span_f1": micro, "span_f1_macro": sum(f1s) / len(f1s)}


def predictions_by_doc(
    models: list[str] | None = None,
) -> dict[str, dict[int, list[tuple[int, int, str]]]]:
    """Predições de cada modelo, já em índices de token e sem os few-shot.

    ``models`` restringe a lista (chaves como nos nomes dos JSONs, p. ex.
    ``deepseek-v4-flash_few_shot``); ``None`` carrega todos os ``MODELS``.
    """
    if models is None:
        wanted = list(MODELS)
    else:
        keep = set(models)
        unknown = sorted(keep - set(MODELS))
        if unknown:
            raise ValueError(f"modelos desconhecidos: {unknown}")
        wanted = [m for m in MODELS if m in keep]
    out: dict[str, dict[int, list[tuple[int, int, str]]]] = {}
    for model in wanted:
        path = paths.OUTPUT_CORRECTED_DIR / f"models_results_decicontas_{model}.json"
        if not path.exists():
            logger.warning("faltando %s", path)
            continue
        df = _load_supervised_df(path) if _is_supervised_model(model) else _load_llm_df(path)
        df = _drop_fewshot(df)
        out[model] = {
            i: [(a["start"], a["end"], a["labels"][0]) for a in (row or [])]
            for i, row in enumerate(df["pred_as_golden"])
        }
    return out


def run(out_dir: Path = OUT_DIR) -> pd.DataFrame:
    out_dir.mkdir(parents=True, exist_ok=True)
    refs = reference_token_spans()
    preds = predictions_by_doc()
    logger.info("%d modelos, %d referências", len(preds), len(refs))

    rows = []
    for ref_name, gold in refs.items():
        for model, pred in preds.items():
            sc = score_against(pred, gold)
            rows.append(
                {
                    "reference": ref_name,
                    "model": model,
                    "display": DISPLAY_NAMES.get(model, model),
                    "is_supervised": _is_supervised_model(model),
                    **sc,
                }
            )
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "reference_sensitivity_scores.csv", index=False)

    # Estabilidade do ranking e contraste central por referência
    base = ANNOTATOR_IDS[0]
    base_order = (
        df[df.reference == base].sort_values("span_f1_macro", ascending=False).model.tolist()
    )
    summary = []
    for ref_name in ANNOTATOR_IDS:
        sub = df[df.reference == ref_name].set_index("model")
        ranks_base = [base_order.index(m) for m in sub.index]
        ranks_here = sub["span_f1_macro"].rank(ascending=False).tolist()
        rho = spearmanr(ranks_base, ranks_here).statistic
        best_llm = sub[~sub.is_supervised].span_f1_macro.idxmax()
        best_sup = sub[sub.is_supervised].span_f1_macro.idxmax()
        summary.append(
            {
                "reference": ref_name,
                "best_llm": DISPLAY_NAMES.get(best_llm, best_llm),
                "best_llm_macro": sub.loc[best_llm, "span_f1_macro"],
                "best_supervised": DISPLAY_NAMES.get(best_sup, best_sup),
                "best_supervised_macro": sub.loc[best_sup, "span_f1_macro"],
                "gap_macro": sub.loc[best_llm, "span_f1_macro"]
                - sub.loc[best_sup, "span_f1_macro"],
                "spearman_vs_A1": rho,
            }
        )
    df_sum = pd.DataFrame(summary)
    df_sum.to_csv(out_dir / "reference_sensitivity_summary.csv", index=False)

    print("\n=== Contraste central por referência ===")
    print(df_sum.to_string(index=False))
    print("\n=== Top 6 por referência (macro) ===")
    for ref_name in ANNOTATOR_IDS:
        sub = df[df.reference == ref_name].nlargest(6, "span_f1_macro")
        print(f"\n[{ref_name}]")
        print(sub[["display", "span_f1", "span_f1_macro"]].round(4).to_string(index=False))
    return df


def per_class_scores(models: list[str] | None = None) -> pd.DataFrame:
    """Precisão, revocação, F1 e suporte por (modelo, referência, classe).

    Uma linha por combinação, com as colunas ``model, display, reference,
    label, precision, recall, f1, support``. O suporte é o número de spans da
    referência naquela classe (``tp + fn``). As contagens vêm de
    :func:`per_class_counts`, o mesmo pareamento do CSV agregado; com rótulo
    igual exigido no pareamento, a média dos quatro F1 de uma linha de
    ``reference_sensitivity_scores.csv`` é exatamente o seu ``span_f1_macro``
    (ver :func:`check_macro_recomposition`). ``models=None`` cobre todos.
    """
    refs = reference_token_spans()
    preds = predictions_by_doc(models)
    rows = []
    for ref_name, gold in refs.items():
        for model, pred in preds.items():
            counts = per_class_counts(pred, gold)
            for lab in ENTITY_LABELS:
                c = counts[lab]
                tp, fp, fn = c["tp"], c["fp"], c["fn"]
                rows.append(
                    {
                        "model": model,
                        "display": DISPLAY_NAMES.get(model, model),
                        "reference": ref_name,
                        "label": lab,
                        "precision": tp / (tp + fp) if tp + fp else 0.0,
                        "recall": tp / (tp + fn) if tp + fn else 0.0,
                        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
                        "support": tp + fn,
                    }
                )
    return pd.DataFrame(rows)


def check_macro_recomposition(per_class: pd.DataFrame, scores: pd.DataFrame) -> float:
    """Maior |média dos F1 por classe − span_f1_macro| sobre (referência, modelo).

    ``scores`` é o DataFrame de :func:`run` (ou o CSV agregado relido). Um
    valor acima de ~1e-12 indica que os dois caminhos deixaram de compartilhar
    o pareamento.
    """
    macro = per_class.groupby(["reference", "model"])["f1"].mean()
    agg = scores.set_index(["reference", "model"])["span_f1_macro"]
    common = macro.index.intersection(agg.index)
    if common.empty:
        raise ValueError("nenhum (referência, modelo) em comum para a checagem")
    return float((macro.loc[common] - agg.loc[common]).abs().max())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, default=OUT_DIR)
    p.add_argument(
        "--per-class",
        action="store_true",
        help="grava também reference_sensitivity_per_class.csv (P/R/F1/suporte por classe)",
    )
    p.add_argument(
        "--models",
        nargs="+",
        metavar="MODEL",
        help="restringe o CSV por classe a estes modelos (chaves dos JSONs); padrão: todos",
    )
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    scores = run(args.out_dir)
    if not args.per_class:
        return

    per_class = per_class_scores(args.models)
    out_path = args.out_dir / "reference_sensitivity_per_class.csv"
    per_class.to_csv(out_path, index=False)
    logger.info("gravado %s (%d linhas)", out_path, len(per_class))

    diff = check_macro_recomposition(per_class, scores)
    print(f"\n=== Checagem: max |média dos F1 por classe − span_f1_macro| = {diff:.2e} ===")
    print("\n=== Span F1 por classe e referência ===")
    table = per_class.pivot_table(
        index=["display", "reference"], columns="label", values="f1", sort=False
    )[list(ENTITY_LABELS)]
    print(table.round(3).to_string())


if __name__ == "__main__":
    main()
