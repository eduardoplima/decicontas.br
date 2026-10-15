"""Onde as fronteiras dos LLMs divergem do gold, em caracteres.

A métrica principal pontua spans em índices de token ``\\S+``. Este script olha
os pares que ela casa (IoU >= 0,5, rótulo igual, pareamento guloso bipartido
de :func:`research.ner_metrics.bipartite_greedy_match`) e mede, em
caracteres, quanto o início e o fim de cada predição se afastam do span de
referência. Responde a duas perguntas do texto:

1. a correspondência exata em caracteres é muito mais baixa que em tokens? e
2. o que separa as duas — pontuação final omitida, prefixos de cabeçalho?

Os offsets em caracteres são os do alinhador da avaliação
(:func:`research.ner_metrics.convert_pred_to_golden_format`, exact-first),
sobre o mesmo texto e o mesmo gold que cada JSON de resultado carrega; nada
aqui re-executa modelo.

Uso:
    uv run python scripts/boundary_offsets.py
    uv run python scripts/boundary_offsets.py --models deepseek-v4-flash_few_shot gpt-4.1_few_shot
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from pathlib import Path

import pandas as pd

from research.dataset_io import char_span_to_token_span, collapse_label, token_offsets
from research.fewshot import FEWSHOT_RESULT_POSITIONS
from research.ner_metrics import bipartite_greedy_match, convert_pred_to_golden_format
from research.release import paths
from research.release.evaluation_numbers import DISPLAY_NAMES

logger = logging.getLogger("boundary_offsets")

OUT_DIR = paths.RAW_EXPERIMENTS_DIR / "boundary_offsets"
DEFAULT_MODELS = ["deepseek-v4-flash_few_shot", "gpt-4.1_few_shot"]
IOU = 0.5


def char_spans(spans: list[dict]) -> list[tuple[int, int, str]]:
    """``(start, end, rótulo colapsado)`` em caracteres."""
    return [(int(s["start"]), int(s["end"]), collapse_label(s["labels"][0])) for s in spans or []]


def to_tokens(
    spans: list[tuple[int, int, str]], offsets
) -> list[tuple[int, int, str] | None]:
    """Projeta cada span na grade de tokens, preservando a posição (``None`` se não cabe)."""
    out: list[tuple[int, int, str] | None] = []
    for s, e, lab in spans:
        tok = char_span_to_token_span(s, e, offsets)
        out.append(None if tok is None else (tok[0], tok[1], lab))
    return out


def exact_tp(pred: list[tuple], gold: list[tuple]) -> int:
    """Pares idênticos ``(início, fim, rótulo)``, um-para-um."""
    left = Counter(gold)
    tp = 0
    for p in pred:
        if left[p] > 0:
            left[p] -= 1
            tp += 1
    return tp


def describe_pair(text: str, pred: tuple[int, int, str], gold: tuple[int, int, str]) -> dict:
    """Deslocamentos de início e fim de uma predição casada, em caracteres."""
    ds = pred[0] - gold[0]
    de = pred[1] - gold[1]
    row = {"start_delta": ds, "end_delta": de, "label": gold[2]}
    # Fim adiantado: a predição para antes do gold; registra o que ficou de fora.
    row["end_omitted"] = text[pred[1] : gold[1]] if de < 0 else ""
    # Início adiantado: a predição começa antes; registra o prefixo a mais.
    row["start_prefix"] = text[pred[0] : gold[0]] if ds < 0 else ""
    return row


def analyse_model(model: str) -> tuple[dict, pd.DataFrame]:
    path = paths.OUTPUT_CORRECTED_DIR / f"models_results_decicontas_{model}.json"
    df = pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))
    df = df.drop(index=FEWSHOT_RESULT_POSITIONS, errors="ignore").reset_index(drop=True)

    pairs: list[dict] = []
    n_pred = n_gold = tp_char = tp_tok = 0
    for doc_pos, row in df.iterrows():
        text = row["text"] or ""
        offsets = token_offsets(text)
        gold_c = char_spans(row["golden"])
        pred_c = char_spans(convert_pred_to_golden_format(row))
        gold_t = to_tokens(gold_c, offsets)
        pred_t = to_tokens(pred_c, offsets)
        keep_g = [i for i, t in enumerate(gold_t) if t is not None]
        keep_p = [i for i, t in enumerate(pred_t) if t is not None]
        g_tok = [gold_t[i] for i in keep_g]
        p_tok = [pred_t[i] for i in keep_p]
        n_pred += len(p_tok)
        n_gold += len(g_tok)
        tp_tok += exact_tp(p_tok, g_tok)
        tp_char += exact_tp([pred_c[i] for i in keep_p], [gold_c[i] for i in keep_g])
        for pi, gi in bipartite_greedy_match(p_tok, g_tok, iou_threshold=IOU):
            pc, gc = pred_c[keep_p[pi]], gold_c[keep_g[gi]]
            pairs.append(
                {
                    "doc_pos": doc_pos,
                    **describe_pair(text, pc, gc),
                    "token_exact": p_tok[pi][:2] == g_tok[gi][:2],
                }
            )

    pdf = pd.DataFrame(pairs)
    pdf.insert(0, "model", model)
    end_early = pdf[pdf.end_delta < 0]
    one_char = end_early[end_early.end_delta == -1]
    start_early = pdf[pdf.start_delta < 0]
    summary = {
        "model": model,
        "display": DISPLAY_NAMES.get(model, model),
        "n_pred": n_pred,
        "n_gold": n_gold,
        "exact_f1_char": 2 * tp_char / (n_pred + n_gold) if n_pred + n_gold else 0.0,
        "exact_f1_token": 2 * tp_tok / (n_pred + n_gold) if n_pred + n_gold else 0.0,
        "n_matched": len(pdf),
        "matched_char_exact": int(((pdf.start_delta == 0) & (pdf.end_delta == 0)).sum()),
        "matched_token_exact": int(pdf.token_exact.sum()),
        "start_same": int((pdf.start_delta == 0).sum()),
        "start_early": len(start_early),
        "start_late": int((pdf.start_delta > 0).sum()),
        "end_same": int((pdf.end_delta == 0).sum()),
        "end_early": len(end_early),
        "end_late": int((pdf.end_delta > 0).sum()),
        "end_early_1char": len(one_char),
        "end_early_1char_semicolon": int((one_char.end_omitted == ";").sum()),
        "end_early_1char_period": int((one_char.end_omitted == ".").sum()),
        "end_early_1char_comma": int((one_char.end_omitted == ",").sum()),
        "top_start_deltas": json.dumps(Counter(start_early.start_delta).most_common(5)),
        "top_start_prefixes": json.dumps(
            Counter(start_early.start_prefix.str.strip()).most_common(5), ensure_ascii=False
        ),
        "top_end_deltas": json.dumps(Counter(end_early.end_delta).most_common(5)),
    }
    return summary, pdf


def run(models: list[str], out_dir: Path = OUT_DIR) -> pd.DataFrame:
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries, frames = [], []
    for model in models:
        s, pdf = analyse_model(model)
        summaries.append(s)
        frames.append(pdf)
    summary = pd.DataFrame(summaries)
    summary.to_csv(out_dir / "boundary_offsets_summary.csv", index=False)
    pd.concat(frames, ignore_index=True).to_csv(out_dir / "boundary_offsets_pairs.csv", index=False)
    with pd.option_context("display.max_colwidth", 200):
        print(summary.T.to_string(header=False))
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    p.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run(args.models, args.out_dir)


if __name__ == "__main__":
    main()
