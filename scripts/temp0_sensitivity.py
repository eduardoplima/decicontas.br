"""Teste de sensibilidade a temperature=0 — AMOSTRAL e PAREADO.

Em vez de re-rodar todo o corpus, usa o subconjunto INFORMATIVO (os docs com >=1
entidade no gold — onde o sinal de extração vive) e compara, NOS MESMOS DOCS:
  * temperature=0 (re-inferência agora) vs.
  * temperature=1.0 (predições do leaderboard já existentes, em output_corrected/),
sem precisar re-rodar o temp=1.0.

Modelos: os 3 do topo, todos NÃO-reasoning (DeepSeek-V4-Flash, GPT-4.1, GPT-4.1-mini).
Os reasoning (gpt-5.x) ignoram/fixam temperature; llama/qwen exigiriam créditos OpenRouter.

Reporta, por modelo:
  1. span-F1 temp0 vs temp1 (pareado, mesmos docs) e o Δ;
  2. CONCORDÂNCIA das predições (Jaccard de spans previstos, casamento IoU>=0,5 + mesmo
     rótulo) — a medida direta de "semelhança" entre as duas temperaturas;
  3. se o empate de liderança DeepSeek↔GPT-4.1 se mantém a temp=0.

Honestidade: o baseline temp=1.0 é UMA amostra (o Δ mistura efeito de temperatura +
ruído de amostragem); temp=0 não é 100% determinístico (MoE/backend). Aditivo: grava só
em results/models_outputs/experiments/temperature0/.

Uso:
    uv run python scripts/temp0_sensitivity.py            # subconjunto informativo (232)
    uv run python scripts/temp0_sensitivity.py --sample 80  # amostra menor (primeiros N informativos)
"""

from __future__ import annotations

import argparse
import json
import logging

import pandas as pd

from research.ner_metrics import compute_iou_raw
from research.release import paths
from research.release.chapter5_numbers import _load_llm_df, _per_entity_metrics_llm
from research.release.run_llm_inference import (
    MODEL_REGISTRY,
    _load_env,
    run_model_technique,
)

logger = logging.getLogger("scripts.temp0_sensitivity")

MODELS_T0 = ["deepseek-v4-flash", "gpt-4.1", "gpt-4.1-mini"]
OUT_DIR = paths.RESULTS_ROOT / "experiments" / "temperature0"


def _label(span: dict) -> str:
    labs = span.get("labels") or ([span["label"]] if span.get("label") else [])
    return labs[0] if labs else ""


def _pred_agreement(preds_a: list, preds_b: list) -> tuple[int, int]:
    """Casamento guloso IoU>=0,5 + mesmo rótulo entre dois conjuntos de spans
    previstos. Retorna (matched, union) para Jaccard agregado."""
    used: set[int] = set()
    matched = 0
    for sa in preds_a or []:
        for j, sb in enumerate(preds_b or []):
            if j in used:
                continue
            if _label(sa) == _label(sb) and compute_iou_raw(
                (sa["start"], sa["end"]), (sb["start"], sb["end"])
            ) >= 0.5:
                matched += 1
                used.add(j)
                break
    union = len(preds_a or []) + len(preds_b or []) - matched
    return matched, union


def _span_f1(df: pd.DataFrame) -> dict:
    return _per_entity_metrics_llm(df)["flat"]


def run(sample: int | None) -> None:
    _load_env()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    sf1_t0: dict[str, float] = {}
    sf1_t1: dict[str, float] = {}
    for key in MODELS_T0:
        cfg = MODEL_REGISTRY[key]
        t1_path = paths.OUTPUT_CORRECTED_DIR / f"models_results_decicontas_{key}_few_shot.json"
        t1_full = _load_llm_df(t1_path)
        info = t1_full[t1_full["golden"].apply(lambda g: isinstance(g, list) and len(g) > 0)]
        info = info.reset_index(drop=True)
        if sample:
            info = info.iloc[:sample].reset_index(drop=True)
        logger.info("temp=0 inferência: %s sobre %d docs informativos", key, len(info))

        recs = run_model_technique(
            key, cfg.get("openrouter"), "few_shot", info["text"].tolist(),
            structured=cfg["structured"], provider_order=cfg.get("provider_order"),
            azure_deployment=cfg.get("azure_foundry"), reasoning=cfg.get("reasoning", False),
            temperature=0.0, skip_fewshot=False,
        )
        for r, gold in zip(recs, info["golden"]):  # gold idêntico ao do temp=1.0 (pareado)
            r["golden"] = gold
        t0_path = OUT_DIR / f"models_results_decicontas_{key}_few_shot.json"
        t0_path.write_text(json.dumps(recs, ensure_ascii=False, indent=2), encoding="utf-8")
        t0_df = _load_llm_df(t0_path)

        m1 = _span_f1(info)
        m0 = _span_f1(t0_df)
        sf1_t0[key], sf1_t1[key] = m0["span_f1"], m1["span_f1"]

        tot_match = tot_union = 0
        for pa, pb in zip(t0_df["pred_as_golden"], info["pred_as_golden"]):
            mt, un = _pred_agreement(pa, pb)
            tot_match += mt
            tot_union += un
        jacc = tot_match / tot_union if tot_union else 1.0

        rows.append({
            "model": key,
            "n_docs": len(info),
            "span_f1_temp0": round(m0["span_f1"], 4),
            "span_f1_temp1": round(m1["span_f1"], 4),
            "delta_span_f1": round(m0["span_f1"] - m1["span_f1"], 4),
            "pred_agreement_jaccard": round(jacc, 4),
            "n_pred_temp0": int(t0_df["pred_as_golden"].apply(len).sum()),
            "n_pred_temp1": int(info["pred_as_golden"].apply(len).sum()),
        })

    df_out = pd.DataFrame(rows)
    csv_path = OUT_DIR / "temp0_vs_temp1_paired.csv"
    df_out.to_csv(csv_path, index=False)
    print("\n===== SENSIBILIDADE A temperature=0 — pareado, subconjunto informativo =====")
    print(df_out.to_string(index=False))
    if "deepseek-v4-flash" in sf1_t0 and "gpt-4.1" in sf1_t0:
        d0 = sf1_t0["deepseek-v4-flash"] - sf1_t0["gpt-4.1"]
        d1 = sf1_t1["deepseek-v4-flash"] - sf1_t1["gpt-4.1"]
        print(f"\n[topo, neste subconjunto] DeepSeek−GPT-4.1: temp0={d0:+.4f} | temp1={d1:+.4f}")
    print(f"\n[salvo] {csv_path}")
    print("RESSALVA: baseline temp=1.0 é 1 amostra (Δ mistura temperatura + ruído); "
          "temp=0 não é 100% determinístico (MoE/backend).")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", type=int, default=None,
                    help="usar só os primeiros N docs informativos (default: todos, ~232)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run(args.sample)


if __name__ == "__main__":
    main()
