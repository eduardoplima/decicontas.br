"""Falsos positivos espúrios de Recomendação do melhor LLM frente às Anotadoras 2 e 3.

A taxonomia de erros do Capítulo 5 (``block_i_errors`` em
``research.release.evaluation_numbers``) chama de falso positivo espúrio
(``FP``) a predição que fica sem par no pareamento um-para-um com o gold
(IoU >= 0,5 e mesmo rótulo, guloso por IoU) e que não se sobrepõe a entidade
alguma do gold, de qualquer classe. Para Recomendação, o deepseek-v4-flash
(few-shot) tem 36 desses casos em 45 erros. Como as Anotadoras 2 e 3 foram
mais restritivas que o gold nessa classe (33 e 28 spans contra 52), cabe
perguntar se os trechos extraídos em excesso foram registrados por elas --- o
que apontaria ambiguidade da diretriz --- ou ignorados pelas duas --- o que
confirmaria o excesso como erro do modelo.

Este script reproduz a classificação de ``block_i_errors`` para o modelo,
recupera o span (índices de token) de cada FP espúrio de Recomendação e o
cruza com os spans das Anotadoras 2 e 3, que estão na mesma grade de tokens
``\\S+`` do release. Nada aqui re-executa modelo.

Categorias (precedência na ordem listada):

- ``recomendacao``: A2 ou A3 tem span de Recomendação com IoU >= 0,5;
- ``recomendacao_parcial``: a maior sobreposição com Recomendação de A2/A3
  é parcial (0 < IoU < 0,5);
- ``outra_classe``: nenhuma Recomendação sobreposta, mas A2 ou A3 marcou o
  trecho (IoU > 0) com outra classe;
- ``ignorado``: nenhuma das duas marcou o trecho com classe alguma.

A coluna ``formula`` agrupa FPs que repetem a mesma abertura (os cinco
tokens seguintes ao verbo, sem acentos nem pontuação), para separar
fórmulas recorrentes de recomendações singulares.

Uso:
    uv run python scripts/fp_recomendacao_annotators.py
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd

from research.dataset_io import collapse_label
from research.ner_metrics import bipartite_greedy_match, compute_iou_raw
from research.release import paths
from research.release.annotator_agreement import load_annotator
from research.release.evaluation_numbers import (
    DISPLAY_NAMES,
    _classify_pair,
    _drop_fewshot,
    _load_llm_df,
)

logger = logging.getLogger("fp_recomendacao_annotators")

MODEL = "deepseek-v4-flash_few_shot"
LABEL = "RECOMENDACAO"
IOU = 0.5
A2, A3 = "anotador2", "anotador3"
OUT_DIR = paths.RAW_EXPERIMENTS_DIR / "reference_sensitivity"
OUT_CSV = "fp_recomendacao_vs_annotators.csv"
EXCERPT_CHARS = 120

Span = tuple[int, int, str]


def release_docs() -> list[dict]:
    """Documentos do release na ordem (por id) que indexa as predições."""
    return sorted(
        json.loads(paths.CORRECTED_GOLD_JSON.read_text(encoding="utf-8")),
        key=lambda d: d["id"],
    )


def annotator_token_spans(name: str, release: list[dict]) -> dict[int, list[Span]]:
    """``{release_index: [(tok_start, tok_end, label)]}`` de um anotador.

    Mesma projeção de ``reference_sensitivity.reference_token_spans``; o
    texto do anotador é conferido contra o release para garantir que os
    índices de token estão na mesma grade das predições.
    """
    id_to_index = {doc["id"]: i for i, doc in enumerate(release)}
    out: dict[int, list[Span]] = {}
    for doc_id, rec in load_annotator(paths.ANNOTATORS_DIR / f"{name}.jsonl").items():
        idx = id_to_index.get(doc_id)
        if idx is None:
            continue
        if rec["text"] != release[idx]["text"]:
            raise ValueError(f"{name}: texto do documento {doc_id} difere do release")
        out[idx] = [(s, e, collapse_label(lab)) for s, e, lab in rec["token_spans"]]
    return out


def model_frame(model: str) -> pd.DataFrame:
    """Predições e gold do modelo em índices de token, sem os few-shot."""
    path = paths.OUTPUT_CORRECTED_DIR / f"models_results_decicontas_{model}.json"
    return _drop_fewshot(_load_llm_df(path))


def spurious_false_positives(pred: list[Span], gold: list[Span]) -> list[int]:
    """Índices das predições classificadas como ``FP`` por ``_classify_pair``.

    Sem par no pareamento um-para-um e sem sobreposição com nenhum span do
    gold, de qualquer classe.
    """
    matched = {pi for pi, _ in bipartite_greedy_match(pred, gold, iou_threshold=IOU)}
    return [
        pi
        for pi, p in enumerate(pred)
        if pi not in matched and all(compute_iou_raw(p[:2], g[:2]) == 0.0 for g in gold)
    ]


def best_overlap(span: tuple[int, int], candidates: list[Span]) -> tuple[str, float]:
    """Rótulo e IoU do candidato de maior sobreposição (``("", 0.0)`` se nenhum)."""
    best_label, best_iou = "", 0.0
    for s, e, lab in candidates:
        iou = compute_iou_raw(span, (s, e))
        if iou > best_iou:
            best_label, best_iou = lab, iou
    return best_label, best_iou


def span_text(doc: dict, tok_start: int, tok_end: int) -> str:
    """Texto do span predito, com espaços normalizados."""
    offsets = doc["token_offsets"]
    return " ".join(doc["text"][offsets[tok_start][0] : offsets[tok_end - 1][1]].split())


def excerpt(text: str) -> str:
    """Trecho de no máximo 120 caracteres."""
    return text if len(text) <= EXCERPT_CHARS else text[: EXCERPT_CHARS - 1] + "…"


def formula_key(text: str, n_tokens: int = 5) -> str:
    """Os ``n_tokens`` seguintes ao verbo, em minúsculas e sem acentos nem pontuação."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z]+", ascii_text.lower())
    return " ".join(words[1 : 1 + n_tokens])


def categorise(row: dict) -> str:
    rec = max(row["a2_rec_iou"], row["a3_rec_iou"])
    other = max(row["a2_other_iou"], row["a3_other_iou"])
    if rec >= IOU:
        return "recomendacao"
    if rec > 0:
        return "recomendacao_parcial"
    if other > 0:
        return "outra_classe"
    return "ignorado"


def run(model: str = MODEL, out_dir: Path = OUT_DIR) -> pd.DataFrame:
    out_dir.mkdir(parents=True, exist_ok=True)
    release = release_docs()
    df = model_frame(model)
    if len(df) != len(release):
        raise ValueError(f"{len(df)} predições para {len(release)} documentos do release")
    refs = {name: annotator_token_spans(name, release) for name in (A2, A3)}

    fp_by_label: Counter = Counter()
    rows: list[dict] = []
    for idx, row in df.iterrows():
        gold = [(g["start"], g["end"], g["labels"][0]) for g in row.get("golden", [])]
        pred = [(p["start"], p["end"], p["labels"][0]) for p in row.get("pred_as_golden", [])]
        fps = spurious_false_positives(pred, gold)
        # A seleção tem de coincidir com a taxonomia publicada no Capítulo 5.
        expected = Counter(c["label"] for c in _classify_pair(pred, gold) if c["kind"] == "FP")
        if Counter(pred[pi][2] for pi in fps) != expected:
            raise RuntimeError(f"documento {idx}: seleção de FP diverge de _classify_pair")
        fp_by_label.update(pred[pi][2] for pi in fps)
        for pi in fps:
            start, end, label = pred[pi]
            if label != LABEL:
                continue
            text = span_text(release[idx], start, end)
            rec = {
                "doc_index": idx,
                "doc_id": release[idx]["id"],
                "tok_start": start,
                "tok_end": end,
                "excerpt": excerpt(text),
            }
            for tag, name in (("a2", A2), ("a3", A3)):
                spans = refs[name].get(idx, [])
                _, rec_iou = best_overlap((start, end), [s for s in spans if s[2] == LABEL])
                other_label, other_iou = best_overlap(
                    (start, end), [s for s in spans if s[2] != LABEL]
                )
                rec[f"{tag}_rec_iou"] = rec_iou
                rec[f"{tag}_other_label"] = other_label
                rec[f"{tag}_other_iou"] = other_iou
            rec["categoria"] = categorise(rec)
            rec["formula"] = formula_key(text)
            rows.append(rec)

    out = pd.DataFrame(rows).sort_values(["doc_index", "tok_start"]).reset_index(drop=True)
    out.to_csv(out_dir / OUT_CSV, index=False)
    logger.info("gravado %s", out_dir / OUT_CSV)
    _print_summary(out, fp_by_label, model)
    return out


def _print_summary(out: pd.DataFrame, fp_by_label: Counter, model: str) -> None:
    print(f"\n=== FP espúrios do {DISPLAY_NAMES.get(model, model)} por classe ===")
    print(dict(sorted(fp_by_label.items())))
    n = len(out)
    print(f"\n=== {n} FP espúrios de {LABEL} em {out.doc_index.nunique()} documentos ===")
    print("\nPor categoria:")
    print(out.categoria.value_counts().reindex(
        ["recomendacao", "recomendacao_parcial", "outra_classe", "ignorado"], fill_value=0
    ).to_string())
    for tag, name in (("a2", "Anotadora 2"), ("a3", "Anotadora 3")):
        rec, other = out[f"{tag}_rec_iou"], out[f"{tag}_other_iou"]
        print(
            f"\n{name}: Recomendação IoU >= {IOU}: {int((rec >= IOU).sum())}; "
            f"Recomendação parcial (0 < IoU < {IOU}): {int(((rec > 0) & (rec < IOU)).sum())}; "
            f"outra classe (IoU > 0): {int(((rec == 0) & (other > 0)).sum())}; "
            f"sem sobreposição: {int(((rec == 0) & (other == 0)).sum())}"
        )
    both = int(((out.a2_rec_iou >= IOU) & (out.a3_rec_iou >= IOU)).sum())
    either = int(((out.a2_rec_iou >= IOU) | (out.a3_rec_iou >= IOU)).sum())
    any_rec = int(((out.a2_rec_iou > 0) | (out.a3_rec_iou > 0)).sum())
    none = int(
        ((out.a2_rec_iou == 0) & (out.a3_rec_iou == 0)
         & (out.a2_other_iou == 0) & (out.a3_other_iou == 0)).sum()
    )
    print(f"\nMarcado como Recomendação (IoU >= {IOU}) por ambas: {both}; por ao menos uma: {either}")
    print(f"Qualquer sobreposição com Recomendação de A2 ou A3 (IoU > 0): {any_rec}")
    print(f"Ignorado pelas duas (nenhum span de qualquer classe): {none}")

    print("\n=== Fórmulas recorrentes (mesma abertura em dois ou mais FPs) ===")
    sizes = out.formula.value_counts()
    recurrent = sizes[sizes >= 2]
    for key, size in recurrent.items():
        sub = out[out.formula == key]
        cats = ", ".join(f"{c}={n}" for c, n in sub.categoria.value_counts().items())
        print(f"{size:3d}x \"{key}\" ({cats}): {excerpt(sub.excerpt.iloc[0])}")
    rest = out[~out.formula.isin(recurrent.index)]
    cats = ", ".join(f"{c}={n}" for c, n in rest.categoria.value_counts().items())
    print(f"{len(rest):3d}  FP com fórmula singular ({cats or 'nenhum'})")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default=MODEL)
    p.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run(args.model, args.out_dir)


if __name__ == "__main__":
    main()
