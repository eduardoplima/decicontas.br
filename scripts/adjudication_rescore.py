"""Repontua as predições existentes contra o gold adjudicado.

Nada aqui re-executa modelo: as predições out-of-fold dos supervisionados e as
dos LLMs (``output_corrected/``) são comparadas, documento a documento, com dois
golds — o release canônico (``dataset/release/decicontas``) e o release exportado
com o arquivo de adjudicação (``--adjudication`` do ``export_dataset``). O
pareamento, o filtro de escopo e as métricas são os de
``scripts/reference_sensitivity.py``.

Saída (``--out-dir``, padrão ``experiments/adjudication/``):
``adjudication_rescore.csv`` (F1 de span micro/macro por modelo e referência,
com os deltas) e ``adjudication_rescore_per_class.csv`` (P/R/F1/suporte por classe).

``--retrained DIR`` acrescenta os encoders retreinados no gold adjudicado (o
``output_<sufixo>/`` escrito por ``research.kfold.export_oof_to_significance``),
identificados como ``<modelo>@retrained``.

Uso:
    uv run python scripts/adjudication_rescore.py
    uv run python scripts/adjudication_rescore.py --retrained dataset/results/models_outputs/output_adjudicated
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reference_sensitivity import (  # noqa: E402
    ENTITY_LABELS,
    per_class_counts,
    predictions_by_doc,
    score_against,
)
from research.annotation_scope import clause_regions, inside  # noqa: E402
from research.dataset_io import char_span_to_token_span, collapse_label  # noqa: E402
from research.release import paths  # noqa: E402
from research.release.evaluation_numbers import DISPLAY_NAMES, _is_supervised_model, load_scored  # noqa: E402

logger = logging.getLogger("adjudication_rescore")

OUT_DIR = paths.RAW_EXPERIMENTS_DIR / "adjudication"
ADJUDICATED_DIR = paths.DATASET / "release" / "decicontas-adjudicated"


def release_token_spans(release_json: Path) -> dict[int, list[tuple[int, int, str]]]:
    """``{release_index: [(tok_start, tok_end, label)]}`` de um bundle JSON, dentro do escopo."""
    release = sorted(json.loads(release_json.read_text(encoding="utf-8")), key=lambda d: d["id"])
    out = {}
    for idx, doc in enumerate(release):
        offsets = [tuple(o) for o in doc["token_offsets"]]
        regions = clause_regions(doc["text"], offsets)
        spans = []
        for e in doc["entities"]:
            tok = char_span_to_token_span(e["start"], e["end"], offsets)
            if tok is not None and not inside(tok, regions):
                spans.append((tok[0], tok[1], collapse_label(e["label"])))
        out[idx] = sorted(spans)
    return out


def retrained_predictions(retrained_dir: Path) -> dict[str, dict[int, list[tuple[int, int, str]]]]:
    """Predições OOF de encoders retreinados, com a chave ``<modelo>@retrained``."""
    out = {}
    for path in sorted(Path(retrained_dir).glob("models_results_decicontas_*__supervised.json")):
        model = path.name[len("models_results_decicontas_"):-len(".json")]
        df = load_scored(path, supervised=True)
        out[f"{model}@retrained"] = {
            i: [(a["start"], a["end"], a["labels"][0]) for a in (row or [])]
            for i, row in enumerate(df["pred_as_golden"])
        }
    return out


def _display(model: str) -> str:
    base = model.removesuffix("@retrained")
    name = DISPLAY_NAMES.get(base, base)
    return f"{name} (retreinado)" if model.endswith("@retrained") else name


def run(adjudicated_dir: Path = ADJUDICATED_DIR, out_dir: Path = OUT_DIR, retrained_dir: Path | None = None) -> pd.DataFrame:
    out_dir.mkdir(parents=True, exist_ok=True)
    refs = {
        "gold": release_token_spans(paths.CANONICAL_GOLD_JSON),
        "adjudicated": release_token_spans(adjudicated_dir / "decicontas" / "decicontas.json"),
    }
    if sorted(refs["gold"]) != sorted(refs["adjudicated"]):
        raise ValueError("os dois releases não cobrem os mesmos documentos")
    preds = predictions_by_doc()
    if retrained_dir is not None:
        preds.update(retrained_predictions(retrained_dir))
    logger.info("%d modelos; gold %d spans, adjudicado %d spans", len(preds),
                sum(map(len, refs["gold"].values())), sum(map(len, refs["adjudicated"].values())))

    rows, per_class = [], []
    for model, pred in preds.items():
        row = {
            "model": model,
            "display": _display(model),
            "is_supervised": model.endswith("@retrained") or _is_supervised_model(model),
        }
        for ref_name, gold in refs.items():
            sc = score_against(pred, gold)
            row[f"span_f1_{ref_name}"] = sc["span_f1"]
            row[f"span_f1_macro_{ref_name}"] = sc["span_f1_macro"]
            counts = per_class_counts(pred, gold)
            for lab in ENTITY_LABELS:
                tp, fp, fn = (int(counts[lab][k]) for k in ("tp", "fp", "fn"))
                per_class.append({
                    "model": model, "display": row["display"], "reference": ref_name, "label": lab,
                    "precision": tp / (tp + fp) if tp + fp else 0.0,
                    "recall": tp / (tp + fn) if tp + fn else 0.0,
                    "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
                    "support": tp + fn,
                })
        row["delta_span_f1"] = row["span_f1_adjudicated"] - row["span_f1_gold"]
        row["delta_span_f1_macro"] = row["span_f1_macro_adjudicated"] - row["span_f1_macro_gold"]
        rows.append(row)
    df = pd.DataFrame(rows).sort_values("span_f1_macro_gold", ascending=False)
    df.to_csv(out_dir / "adjudication_rescore.csv", index=False)
    pc = pd.DataFrame(per_class)
    pc.to_csv(out_dir / "adjudication_rescore_per_class.csv", index=False)

    print("\n=== F1 de span macro / micro: gold v1.2.0 × adjudicado ===")
    cols = ["display", "span_f1_macro_gold", "span_f1_macro_adjudicated", "delta_span_f1_macro",
            "span_f1_gold", "span_f1_adjudicated", "delta_span_f1"]
    print(df[cols].round(4).to_string(index=False))
    for ref_name in refs:
        sub = df.set_index("model")
        best_llm = sub[~sub.is_supervised][f"span_f1_macro_{ref_name}"].idxmax()
        best_sup = sub[sub.is_supervised][f"span_f1_macro_{ref_name}"].idxmax()
        gap = sub.loc[best_llm, f"span_f1_macro_{ref_name}"] - sub.loc[best_sup, f"span_f1_macro_{ref_name}"]
        print(f"\n[{ref_name}] melhor LLM {_display(best_llm)} "
              f"{sub.loc[best_llm, f'span_f1_macro_{ref_name}']:.4f} × melhor encoder "
              f"{_display(best_sup)} {sub.loc[best_sup, f'span_f1_macro_{ref_name}']:.4f} "
              f"(gap {gap:+.4f})")
    wide = pc.pivot_table(index=["display", "label"], columns="reference", values="f1").reset_index()
    wide["delta"] = wide["adjudicated"] - wide["gold"]
    print("\n=== F1 por classe (delta adjudicado − gold), maiores movimentos ===")
    print(wide.reindex(wide["delta"].abs().sort_values(ascending=False).index).head(12).round(4).to_string(index=False))
    return df


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--release", type=Path, default=ADJUDICATED_DIR, help="diretório do release adjudicado")
    p.add_argument("--out-dir", type=Path, default=OUT_DIR)
    p.add_argument("--retrained", type=Path, help="output_<sufixo>/ com os encoders retreinados no gold adjudicado")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run(args.release, args.out_dir, args.retrained)


if __name__ == "__main__":
    main()
