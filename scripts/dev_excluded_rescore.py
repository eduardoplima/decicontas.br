"""Repontuação sem os documentos de desenvolvimento da seleção de hiperparâmetros.

A taxa de aprendizado e o *warmup* dos supervisionados foram escolhidos uma
única vez por modelo, numa partição 80/20 global
(:func:`research.kfold.data.grid_split`), e não dentro de cada partição de
treino da validação cruzada. Os 173 documentos de desenvolvimento reaparecem
nas partições de teste, o que pode inflar as notas dos supervisionados (viés
otimista de seleção).

Este script mede esse efeito sem retreinar: pontua as mesmas predições
*out-of-fold* — e as dos LLMs, para manter o pareamento — apenas nos 688
documentos que nunca participaram da seleção, e repete o bootstrap pareado do
F1 macro para os contrastes centrais.

Os índices de desenvolvimento vêm dos próprios artefatos da grade
(``test_indices`` em ``supervised_kfold/grid/*/*.json``), e não de um novo
sorteio: o que importa é o conjunto efetivamente usado. O script falha se dois
artefatos discordarem desse conjunto ou se a ordem das amostras do k-fold não
coincidir, texto a texto, com a ordem do release em que as predições são
pontuadas.

Carga, pareamento e bootstrap são os de
:mod:`research.release.bootstrap_significance` (B = 10.000, semente 42, IoU
>= 0,5); com o corpus inteiro o script reproduz os intervalos de
``J_bootstrap_paired_highlighted.csv``, o que é impresso como checagem.

Uso:
    uv run python scripts/dev_excluded_rescore.py
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from research.dataset import get_decicontas_df
from research.fewshot import FEWSHOT_RESULT_POSITIONS
from research.release import paths
from research.release.bootstrap_significance import (
    DEFAULT_INPUT_DIR,
    DISPLAY_NAMES,
    MODELS,
    compute_doc_level_counts_per_class,
    f1_from_sums,
    load_model_predictions,
    macro_f1_from_class_counts,
    paired_bootstrap_diff_macro,
)

logger = logging.getLogger("dev_excluded_rescore")

GRID_DIR = paths.KFOLD_CORRECTED / "grid"
KFOLD_DATASET = paths.RELEASE_DIR / "decicontas-labelstudio.json"
OUT_DIR = paths.RAW_EXPERIMENTS_DIR / "dev_excluded"

LEADER = "deepseek-v4-flash_few_shot"
CONTRASTS = [
    (LEADER, "raquelsilveira_legalbertpt_fp__supervised"),
    (LEADER, "neuralmind_bert-large-portuguese-cased__supervised"),
    (LEADER, "neuralmind_bert-base-portuguese-cased__supervised"),
    (LEADER, "gpt-4.1_few_shot"),
    ("raquelsilveira_legalbertpt_fp__supervised", "neuralmind_bert-base-portuguese-cased__supervised"),
    ("raquelsilveira_legalbertpt_fp__supervised", "neuralmind_bert-large-portuguese-cased__supervised"),
]


def read_dev_indices(grid_dir: Path) -> list[int]:
    """Índices de desenvolvimento usados pela grade, iguais em todos os artefatos.

    Levanta ``ValueError`` se não houver artefato ou se dois deles trouxerem
    conjuntos diferentes.
    """
    found: dict[tuple[int, ...], Path] = {}
    for path in sorted(grid_dir.glob("*/*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        found.setdefault(tuple(sorted(raw["test_indices"])), path)
    if not found:
        raise ValueError(f"nenhum artefato de grade em {grid_dir}")
    if len(found) > 1:
        examples = ", ".join(str(p) for p in found.values())
        raise ValueError(f"artefatos de grade discordam dos índices de dev: {examples}")
    return list(next(iter(found)))


def keep_positions(n_docs: int, dev: list[int]) -> np.ndarray:
    """Posições fora do conjunto de desenvolvimento, em ordem crescente."""
    if any(i < 0 or i >= n_docs for i in dev):
        raise ValueError("índice de dev fora do corpus")
    dev_set = set(dev)
    return np.array([i for i in range(n_docs) if i not in dev_set], dtype=np.int64)


def subset_counts(counts: dict, idx: np.ndarray) -> dict:
    """Recorta as contagens por documento e por classe às posições ``idx``."""
    return {lab: {k: arr[idx] for k, arr in c.items()} for lab, c in counts.items()}


def micro_f1(counts: dict, idx: np.ndarray | None = None) -> float:
    """F1 micro de span a partir das contagens por classe."""
    tp = fp = fn = 0
    for c in counts.values():
        sel = slice(None) if idx is None else idx
        tp += int(c["tp"][sel].sum())
        fp += int(c["fp"][sel].sum())
        fn += int(c["fn"][sel].sum())
    return f1_from_sums(tp, fp, fn)[2]


def check_kfold_alignment(dataset_path: Path = KFOLD_DATASET) -> int:
    """Confere que a amostra ``i`` do k-fold é o documento ``i`` do release.

    O k-fold indexa as amostras na ordem de ``get_decicontas_df`` sobre o JSON
    do Label Studio; o release em que as predições são pontuadas está ordenado
    por id. Devolve o número de documentos.
    """
    df = get_decicontas_df(path=str(dataset_path))
    kfold_texts = [row["data"]["text"] for _, row in df.iterrows()]
    release = sorted(
        json.loads(paths.CORRECTED_GOLD_JSON.read_text(encoding="utf-8")),
        key=lambda d: d["id"],
    )
    release_texts = [d["text"] for d in release]
    if len(kfold_texts) != len(release_texts):
        raise ValueError(f"k-fold tem {len(kfold_texts)} docs e o release {len(release_texts)}")
    mismatch = [i for i, (a, b) in enumerate(zip(kfold_texts, release_texts)) if a != b]
    if mismatch:
        raise ValueError(f"ordem do k-fold difere do release nas posições {mismatch[:10]}")
    return len(release_texts)


def load_counts() -> tuple[dict[str, dict], int]:
    """Contagens por documento e classe de cada modelo, sem os few-shot."""
    counts: dict[str, dict] = {}
    n_docs = None
    for model in MODELS:
        df = load_model_predictions(model, DEFAULT_INPUT_DIR)
        df = df.drop(index=FEWSHOT_RESULT_POSITIONS, errors="ignore").reset_index(drop=True)
        if n_docs is None:
            n_docs = len(df)
        elif len(df) != n_docs:
            raise RuntimeError(f"{model} cobre {len(df)} docs, esperado {n_docs}")
        counts[model] = compute_doc_level_counts_per_class(df)
    return counts, int(n_docs)


def run(out_dir: Path = OUT_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    out_dir.mkdir(parents=True, exist_ok=True)
    n_release = check_kfold_alignment()
    dev = read_dev_indices(GRID_DIR)
    counts, n_docs = load_counts()
    if n_docs != n_release:
        raise RuntimeError(f"predições cobrem {n_docs} docs e o release {n_release}")
    keep = keep_positions(n_docs, dev)
    logger.info("%d docs, %d de dev, %d mantidos", n_docs, len(dev), len(keep))

    any_counts = next(iter(counts.values()))
    gold_total = sum(c["tp"] + c["fn"] for c in any_counts.values())
    n_ent_keep = int(gold_total[keep].sum())
    n_ent_dev = int(gold_total.sum()) - n_ent_keep
    n_inf_keep = int((gold_total[keep] > 0).sum())

    rows = []
    for model, cc in counts.items():
        macro_full = macro_f1_from_class_counts(cc)
        macro_keep = macro_f1_from_class_counts(cc, keep)
        micro_full = micro_f1(cc)
        micro_keep = micro_f1(cc, keep)
        rows.append(
            {
                "model": model,
                "display": DISPLAY_NAMES.get(model, model),
                "is_supervised": model.endswith("__supervised"),
                "span_f1_macro_full": macro_full,
                "span_f1_macro_nodev": macro_keep,
                "delta_macro": macro_keep - macro_full,
                "span_f1_micro_full": micro_full,
                "span_f1_micro_nodev": micro_keep,
                "delta_micro": micro_keep - micro_full,
            }
        )
    scores = (
        pd.DataFrame(rows)
        .sort_values("span_f1_macro_nodev", ascending=False)
        .reset_index(drop=True)
    )
    scores.insert(0, "n_docs_nodev", len(keep))
    scores.to_csv(out_dir / "dev_excluded_scores.csv", index=False)

    contrast_rows = []
    for a, b in CONTRASTS:
        full = paired_bootstrap_diff_macro(counts[a], counts[b])
        sub = paired_bootstrap_diff_macro(subset_counts(counts[a], keep), subset_counts(counts[b], keep))
        contrast_rows.append(
            {
                "model_a": a,
                "model_b": b,
                "display_a": DISPLAY_NAMES.get(a, a),
                "display_b": DISPLAY_NAMES.get(b, b),
                "diff_full": macro_f1_from_class_counts(counts[a]) - macro_f1_from_class_counts(counts[b]),
                "ci_lower_full": full["ci_lower"],
                "ci_upper_full": full["ci_upper"],
                "p_full": full["p_value"],
                "diff_nodev": macro_f1_from_class_counts(counts[a], keep)
                - macro_f1_from_class_counts(counts[b], keep),
                "ci_lower_nodev": sub["ci_lower"],
                "ci_upper_nodev": sub["ci_upper"],
                "p_nodev": sub["p_value"],
            }
        )
    contrasts = pd.DataFrame(contrast_rows)
    contrasts.to_csv(out_dir / "dev_excluded_contrasts.csv", index=False)

    meta = {
        "n_docs": n_docs,
        "n_dev": len(dev),
        "n_docs_nodev": len(keep),
        "n_entities_nodev": n_ent_keep,
        "n_entities_dev": n_ent_dev,
        "n_informative_nodev": n_inf_keep,
    }
    (out_dir / "dev_excluded_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print("\n=== Corpus ===")
    print(json.dumps(meta, indent=2))
    print("\n=== F1 de span: corpus inteiro × sem dev ===")
    cols = ["display", "span_f1_macro_full", "span_f1_macro_nodev", "delta_macro",
            "span_f1_micro_full", "span_f1_micro_nodev", "delta_micro"]
    print(scores[cols].round(4).to_string(index=False))
    print("\n=== Contrastes (F1 macro; IC 95% bootstrap pareado) ===")
    print(contrasts.drop(columns=["model_a", "model_b"]).round(4).to_string(index=False))
    return scores, contrasts


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run(args.out_dir)


if __name__ == "__main__":
    main()
