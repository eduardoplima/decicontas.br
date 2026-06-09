"""Bootstrap pareado sobre o MACRO span-F1 (média dos F1 por classe).

O bootstrap canônico (``research.release.bootstrap_significance``) reamostra o
\\emph{micro} span-F1 (soma de TP/FP/FN agregados por documento). A pedido da banca,
este script reamostra o \\emph{macro} span-F1 --- média aritmética dos F1 das quatro
classes (\\textsc{Multa}, \\textsc{Obrigação}, \\textsc{Recomendação}, \\textsc{Ressarcimento})
---, para que o desempenho nas classes minoritárias não fique mascarado.

Reusa a mesma lógica de casamento (``bipartite_greedy_match``, IoU>=0,5, mesmo rótulo),
a mesma semente (42), N=10000 e a mesma família ``HIGHLIGHTED_PAIRS`` com correção de Holm.
Lê os modelos de ``dataset/results/models_outputs/output_corrected/``.

Saída: ``models_outputs/significance/macro_bootstrap_paired.csv`` (todos os pares) e
``macro_bootstrap_highlighted.csv`` (família destacada, com Holm) + ``macro_bootstrap_ci.csv``.

Uso:
    uv run python scripts/macro_bootstrap.py
"""

from __future__ import annotations

import csv
from itertools import combinations

import numpy as np

from research.ner_metrics import bipartite_greedy_match
from research.release import paths
from research.release.bootstrap_significance import (
    ALPHA,
    DISPLAY_NAMES,
    HIGHLIGHTED_PAIRS,
    N_BOOTSTRAP,
    SEED,
)
from research.release.chapter5_numbers import load_all_models

LABELS = ["MULTA", "OBRIGACAO", "RECOMENDACAO", "RESSARCIMENTO"]


def per_class_counts(df) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Por classe: arrays (tp, fp, fn) por documento, sob o matcher canônico."""
    n = len(df)
    cc = {L: (np.zeros(n, np.int32), np.zeros(n, np.int32), np.zeros(n, np.int32)) for L in LABELS}
    for i, row in enumerate(df.itertuples(index=False)):
        gold = [(g["start"], g["end"], g["labels"][0]) for g in row.golden]
        pred = [(p["start"], p["end"], p["labels"][0]) for p in row.pred_as_golden]
        matched = bipartite_greedy_match(pred, gold, iou_threshold=0.5)
        matched_labels = [pred[pi][2] for pi, _ in matched]  # rótulo casa (require_label_match)
        for L in LABELS:
            tp = sum(1 for lab in matched_labels if lab == L)
            pred_L = sum(1 for p in pred if p[2] == L)
            gold_L = sum(1 for g in gold if g[2] == L)
            cc[L][0][i] = tp
            cc[L][1][i] = pred_L - tp
            cc[L][2][i] = gold_L - tp
    return cc


def _macro_f1(cc, idx) -> float:
    f1s = []
    for L in LABELS:
        tp = int(cc[L][0][idx].sum())
        fp = int(cc[L][1][idx].sum())
        fn = int(cc[L][2][idx].sum())
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * p * r / (p + r) if p + r else 0.0)
    return sum(f1s) / len(LABELS)


def _holm(pairs: list[dict]) -> None:
    order = sorted(range(len(pairs)), key=lambda i: pairs[i]["p_value"])
    m = len(pairs)
    running = 0.0
    for rank, i in enumerate(order):
        adj = min((m - rank) * pairs[i]["p_value"], 1.0)
        running = max(running, adj)
        pairs[i]["p_holm"] = running
        pairs[i]["sig_holm"] = running < 0.05


def run() -> None:
    out_dir = paths.SIGNIFICANCE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    model_dfs = load_all_models(paths.OUTPUT_CORRECTED_DIR)
    cc = {m: per_class_counts(df) for m, df in model_dfs.items()}
    n_docs = len(next(iter(model_dfs.values())))
    all_idx = np.arange(n_docs)
    point = {m: _macro_f1(cc[m], all_idx) for m in cc}

    rng = np.random.default_rng(SEED)
    idx_matrix = rng.integers(0, n_docs, size=(N_BOOTSTRAP, n_docs))

    # CI por modelo
    ci_rows = []
    for m in cc:
        f1s = np.array([_macro_f1(cc[m], idx_matrix[b]) for b in range(N_BOOTSTRAP)])
        ci_rows.append({
            "model": m, "display": DISPLAY_NAMES.get(m, m),
            "macro_f1_point": round(point[m], 4),
            "ci_lower": round(float(np.percentile(f1s, 100 * ALPHA / 2)), 4),
            "ci_upper": round(float(np.percentile(f1s, 100 * (1 - ALPHA / 2))), 4),
        })

    # Pares
    def paired(a, b):
        diffs = np.array([_macro_f1(cc[a], idx_matrix[k]) - _macro_f1(cc[b], idx_matrix[k])
                          for k in range(N_BOOTSTRAP)])
        lo = float(np.percentile(diffs, 100 * ALPHA / 2))
        hi = float(np.percentile(diffs, 100 * (1 - ALPHA / 2)))
        p = float(min(2 * min((diffs <= 0).mean(), (diffs >= 0).mean()), 1.0))
        return point[a] - point[b], lo, hi, p

    all_pairs = []
    for a, b in combinations(list(cc.keys()), 2):
        d, lo, hi, p = paired(a, b)
        all_pairs.append({"model_a": a, "model_b": b, "display_a": DISPLAY_NAMES.get(a, a),
                          "display_b": DISPLAY_NAMES.get(b, b), "diff_macro": round(d, 4),
                          "ci_lower": round(lo, 4), "ci_upper": round(hi, 4),
                          "p_value": round(p, 4), "significant_95": (lo > 0) or (hi < 0)})

    hp = {frozenset(p) for p in HIGHLIGHTED_PAIRS}
    highlighted = [r for r in all_pairs if frozenset((r["model_a"], r["model_b"])) in hp]
    _holm(highlighted)

    def _write(path, rows, cols):
        with (out_dir / path).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    _write("macro_bootstrap_ci.csv", sorted(ci_rows, key=lambda r: -r["macro_f1_point"]),
           ["model", "display", "macro_f1_point", "ci_lower", "ci_upper"])
    _write("macro_bootstrap_paired.csv", sorted(all_pairs, key=lambda r: -abs(r["diff_macro"])),
           ["model_a", "model_b", "display_a", "display_b", "diff_macro", "ci_lower", "ci_upper", "p_value", "significant_95"])
    _write("macro_bootstrap_highlighted.csv", sorted(highlighted, key=lambda r: -abs(r["diff_macro"])),
           ["display_a", "display_b", "diff_macro", "ci_lower", "ci_upper", "p_value", "p_holm", "sig_holm"])

    print(f"[ok] {len(cc)} modelos, {n_docs} docs. Saída em {out_dir}")
    print("\n== MACRO highlighted (com Holm) ==")
    for r in sorted(highlighted, key=lambda r: -abs(r["diff_macro"])):
        print(f"  {r['display_a'][:16]:16} vs {r['display_b'][:16]:16} Δ={r['diff_macro']:+.4f} "
              f"IC=[{r['ci_lower']:+.3f};{r['ci_upper']:+.3f}] p={r['p_value']:.4f} pHolm={r['p_holm']:.4f} holm={r['sig_holm']}")


if __name__ == "__main__":
    run()
