"""Inter-annotator agreement study for the decicontas.br corpus.

Three annotators labelled the same set of documents independently, using the
same Label Studio configuration and the annotation guidelines:

- **anotador1** — the original author annotation *after* the Cleanlab audit
  (span-identical to the corrected release ``dataset/release/decicontas``);
- **anotador2** / **anotador3** — independent blind annotations produced by
  staff of the decisions-monitoring unit of the TCE/RN.

The three JSONL files live in ``dataset/annotators/`` and cover all 861
documents of the release (the five documents with no entities in the gold
were annotated as empty by all three annotators).

Agreement is measured at three granularities:

1. token level — pairwise Cohen's kappa and three-way Fleiss' kappa over the
   five collapsed labels (``O`` + four entity classes), using the canonical
   whitespace tokenisation of :mod:`research.dataset_io`;
2. span level — pairwise F1 with the same IoU >= 0.5 bipartite-greedy matcher
   used by the dissertation's evaluation protocol
   (:func:`research.ner_metrics.bipartite_greedy_match`);
3. document level — Cohen's kappa on the presence of any entity (and of each
   class) in the document.

A divergence typology (class confusion / boundary / presence) and a
robustness check against the *pre*-correction gold are also produced.
Outputs land in ``dataset/results/models_outputs/corpus_and_agreement/`` as ``A42_*.csv``
plus a self-contained ``AGREEMENT.md``.

Run:
    uv run python -m research.release.annotator_agreement
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from itertools import combinations
from pathlib import Path

import pandas as pd

from research.dataset_io import ENTITY_LABELS, collapse_label, tokenize
from research.ner_metrics import bipartite_greedy_match, compute_iou_raw
from research.release import paths

OUTPUT_ROOT = paths.CORPUS_DIR
ANNOTATOR_IDS = ("anotador1", "anotador2", "anotador3")
IOU_THRESHOLD = 0.5

logger = logging.getLogger("research.release.annotator_agreement")

Span = tuple[int, int, str]


# ----- Loading and sanity checks -------------------------------------------


def load_annotator(path: Path) -> dict[int, dict]:
    """Load one annotator JSONL as ``{doc_id: {"text": str, "spans": [Span]}}``."""
    docs: dict[int, dict] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            spans = [
                (s["start"], s["end"], collapse_label(s["label"])) for s in rec["spans"]
            ]
            docs[rec["id"]] = {"text": rec["text"], "spans": sorted(spans)}
    return docs


def load_release_spans(release_json: Path) -> dict[int, dict]:
    """Load a release bundle in the same ``{doc_id: {text, spans}}`` shape."""
    docs: dict[int, dict] = {}
    for rec in json.loads(release_json.read_text(encoding="utf-8")):
        spans = [
            (e["start"], e["end"], collapse_label(e["label"])) for e in rec["entities"]
        ]
        docs[rec["id"]] = {"text": rec["text"], "spans": sorted(spans)}
    return docs


def load_study(
    annotators_dir: Path = paths.ANNOTATORS_DIR,
) -> tuple[dict[str, dict[int, dict]], list[int]]:
    """Load the three annotator files and validate their alignment.

    Ensures all annotators cover the same document ids with identical texts,
    and that ``anotador1`` is span-identical to the corrected release gold.
    Returns the annotations and the sorted list of common document ids.
    """
    data = {a: load_annotator(annotators_dir / f"{a}.jsonl") for a in ANNOTATOR_IDS}
    ids = sorted(data[ANNOTATOR_IDS[0]])
    for a in ANNOTATOR_IDS[1:]:
        if sorted(data[a]) != ids:
            raise ValueError(f"{a}: document ids differ from {ANNOTATOR_IDS[0]}")
        mismatched = [i for i in ids if data[a][i]["text"] != data[ANNOTATOR_IDS[0]][i]["text"]]
        if mismatched:
            raise ValueError(f"{a}: texts differ on documents {mismatched[:5]}")

    gold = load_release_spans(paths.CORRECTED_GOLD_JSON)
    missing = sorted(set(gold) - set(ids))
    if missing:
        logger.info("release docs absent from the study: %s", missing)
    diverging = [i for i in ids if gold[i]["spans"] != data["anotador1"][i]["spans"]]
    if diverging:
        raise ValueError(
            f"anotador1 differs from the corrected gold on documents {diverging[:5]}"
        )
    return data, ids


# ----- Agreement coefficients -----------------------------------------------


def cohen_kappa(y1: list, y2: list) -> float:
    """Cohen's kappa between two aligned label sequences."""
    if len(y1) != len(y2):
        raise ValueError("sequences must be aligned")
    n = len(y1)
    po = sum(a == b for a, b in zip(y1, y2)) / n
    c1, c2 = Counter(y1), Counter(y2)
    pe = sum(c1[k] * c2.get(k, 0) for k in c1) / (n * n)
    return 1.0 if pe == 1.0 else (po - pe) / (1 - pe)


def fleiss_kappa(sequences: list[list]) -> float:
    """Fleiss' kappa for ``m`` aligned label sequences (one per annotator)."""
    m = len(sequences)
    n = len(sequences[0])
    if any(len(s) != n for s in sequences):
        raise ValueError("sequences must be aligned")
    categories = sorted({lab for seq in sequences for lab in seq})
    # P_i: extent of agreement on item i; p_j: overall proportion per category.
    p_j = Counter()
    sum_pi = 0.0
    for i in range(n):
        counts = Counter(seq[i] for seq in sequences)
        p_j.update(counts)
        sum_pi += sum(c * (c - 1) for c in counts.values()) / (m * (m - 1))
    p_bar = sum_pi / n
    pe = sum((p_j[c] / (n * m)) ** 2 for c in categories)
    return 1.0 if pe == 1.0 else (p_bar - pe) / (1 - pe)


# ----- Granularity projections ----------------------------------------------


def token_labels(text: str, spans: list[Span]) -> list[str]:
    """Project character spans onto the canonical tokenisation (5-class labels)."""
    tokens = tokenize(text)
    labels = ["O"] * len(tokens)
    for start, end, label in spans:
        for idx, tok in enumerate(tokens):
            if tok.char_start < end and tok.char_end > start:
                labels[idx] = label
    return labels


def pairwise_span_prf(
    docs_a: dict[int, dict], docs_b: dict[int, dict], ids: list[int], label: str | None = None
) -> tuple[float, float, float]:
    """Micro precision/recall/F1 of annotator A against B (IoU >= 0.5).

    F1 is symmetric in (A, B); precision/recall swap roles. ``label``
    restricts the computation to a single entity class.
    """
    tp = n_a = n_b = 0
    for i in ids:
        sa = [s for s in docs_a[i]["spans"] if label is None or s[2] == label]
        sb = [s for s in docs_b[i]["spans"] if label is None or s[2] == label]
        tp += len(bipartite_greedy_match(sa, sb, iou_threshold=IOU_THRESHOLD))
        n_a += len(sa)
        n_b += len(sb)
    precision = tp / n_a if n_a else 0.0
    recall = tp / n_b if n_b else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def divergence_typology(
    docs_a: dict[int, dict], docs_b: dict[int, dict], ids: list[int]
) -> tuple[dict[str, int], Counter]:
    """Classify every span-level divergence between two annotators.

    Spans are first matched label-agnostically (IoU >= 0.5). Matched pairs
    with identical labels count as agreement; with different labels, as class
    confusion. Unmatched spans that overlap a same-label unmatched span on the
    other side (0 < IoU < 0.5) are boundary divergences; the remainder are
    presence divergences (a command one annotator registered and the other
    did not). Returns the counts and the class-confusion counter
    ``(label_a, label_b) -> n``.
    """
    counts = {
        "agreement": 0,
        "class_confusion": 0,
        "boundary": 0,
        "presence_only_a": 0,
        "presence_only_b": 0,
    }
    confusion: Counter = Counter()
    for i in ids:
        sa, sb = docs_a[i]["spans"], docs_b[i]["spans"]
        matched = bipartite_greedy_match(
            sa, sb, iou_threshold=IOU_THRESHOLD, require_label_match=False
        )
        used_a = {pi for pi, _ in matched}
        used_b = {gi for _, gi in matched}
        for pi, gi in matched:
            if sa[pi][2] == sb[gi][2]:
                counts["agreement"] += 1
            else:
                counts["class_confusion"] += 1
                confusion[(sa[pi][2], sb[gi][2])] += 1
        rest_a = [s for idx, s in enumerate(sa) if idx not in used_a]
        rest_b = [s for idx, s in enumerate(sb) if idx not in used_b]
        paired_b: set[int] = set()
        for span_a in rest_a:
            partner = None
            for idx_b, span_b in enumerate(rest_b):
                if idx_b in paired_b or span_b[2] != span_a[2]:
                    continue
                if compute_iou_raw(span_a[:2], span_b[:2]) > 0:
                    partner = idx_b
                    break
            if partner is not None:
                paired_b.add(partner)
                counts["boundary"] += 1
            else:
                counts["presence_only_a"] += 1
        counts["presence_only_b"] += len(rest_b) - len(paired_b)
    return counts, confusion


# ----- Study ----------------------------------------------------------------


def _pair_row(
    name_a: str,
    name_b: str,
    docs_a: dict[int, dict],
    docs_b: dict[int, dict],
    ids: list[int],
) -> dict:
    tokens_a = [lab for i in ids for lab in token_labels(docs_a[i]["text"], docs_a[i]["spans"])]
    tokens_b = [lab for i in ids for lab in token_labels(docs_b[i]["text"], docs_b[i]["spans"])]
    precision, recall, f1_micro = pairwise_span_prf(docs_a, docs_b, ids)
    per_class_f1 = [pairwise_span_prf(docs_a, docs_b, ids, label=lab)[2] for lab in ENTITY_LABELS]
    presence_a = [int(bool(docs_a[i]["spans"])) for i in ids]
    presence_b = [int(bool(docs_b[i]["spans"])) for i in ids]
    return {
        "pair": f"{name_a} x {name_b}",
        "kappa_token": cohen_kappa(tokens_a, tokens_b),
        "obs_agreement_token": sum(a == b for a, b in zip(tokens_a, tokens_b)) / len(tokens_a),
        "span_precision": precision,
        "span_recall": recall,
        "span_f1_micro": f1_micro,
        "span_f1_macro": sum(per_class_f1) / len(per_class_f1),
        "kappa_doc_presence": cohen_kappa(presence_a, presence_b),
    }


def run() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    data, ids = load_study()
    logger.info("loaded %d common documents for %d annotators", len(ids), len(data))

    # --- pairwise agreement (main study) ---
    pair_rows = [
        _pair_row(a, b, data[a], data[b], ids) for a, b in combinations(ANNOTATOR_IDS, 2)
    ]
    pairwise = pd.DataFrame(pair_rows)
    pairwise.to_csv(OUTPUT_ROOT / "A42_agreement_pairwise.csv", index=False)

    # --- global (three-way) agreement ---
    token_seqs = [
        [lab for i in ids for lab in token_labels(data[a][i]["text"], data[a][i]["spans"])]
        for a in ANNOTATOR_IDS
    ]
    global_stats = pd.DataFrame(
        [
            {"metric": "fleiss_kappa_token", "value": fleiss_kappa(token_seqs)},
            {"metric": "mean_pairwise_kappa_token", "value": pairwise["kappa_token"].mean()},
            {"metric": "mean_pairwise_span_f1_micro", "value": pairwise["span_f1_micro"].mean()},
            {"metric": "n_documents", "value": len(ids)},
        ]
    )
    global_stats.to_csv(OUTPUT_ROOT / "A42_agreement_global.csv", index=False)

    # --- per-class agreement ---
    class_rows = []
    for a, b in combinations(ANNOTATOR_IDS, 2):
        for lab in ENTITY_LABELS:
            _, _, f1 = pairwise_span_prf(data[a], data[b], ids, label=lab)
            pres_a = [int(any(s[2] == lab for s in data[a][i]["spans"])) for i in ids]
            pres_b = [int(any(s[2] == lab for s in data[b][i]["spans"])) for i in ids]
            class_rows.append(
                {
                    "pair": f"{a} x {b}",
                    "label": lab,
                    "span_f1": f1,
                    "kappa_doc_presence": cohen_kappa(pres_a, pres_b),
                    "n_spans_a": sum(len([s for s in data[a][i]["spans"] if s[2] == lab]) for i in ids),
                    "n_spans_b": sum(len([s for s in data[b][i]["spans"] if s[2] == lab]) for i in ids),
                }
            )
    per_class = pd.DataFrame(class_rows)
    per_class.to_csv(OUTPUT_ROOT / "A42_agreement_per_class.csv", index=False)

    # --- divergence typology + class confusion ---
    div_rows = []
    confusion_total: Counter = Counter()
    for a, b in combinations(ANNOTATOR_IDS, 2):
        counts, confusion = divergence_typology(data[a], data[b], ids)
        div_rows.append({"pair": f"{a} x {b}", **counts})
        confusion_total.update(confusion)
    divergences = pd.DataFrame(div_rows)
    divergences.to_csv(OUTPUT_ROOT / "A42_divergences.csv", index=False)

    confusion_df = pd.DataFrame(
        [
            {"label_a": la, "label_b": lb, "n": n}
            for (la, lb), n in sorted(confusion_total.items(), key=lambda kv: -kv[1])
        ]
    )
    confusion_df.to_csv(OUTPUT_ROOT / "A42_class_confusion.csv", index=False)

    # --- robustness: annotators vs the pre-correction gold ---
    pre = load_release_spans(paths.RELEASE_PRE_DIR / "decicontas.json")
    pre = {i: pre[i] for i in ids}
    robust_rows = [
        _pair_row("gold-pre-correcao", a, pre, data[a], ids) for a in ANNOTATOR_IDS
    ]
    robustness = pd.DataFrame(robust_rows)
    robustness.to_csv(OUTPUT_ROOT / "A42_agreement_precorrection.csv", index=False)

    _write_report(pairwise, global_stats, per_class, divergences, confusion_df, robustness, ids)


def _write_report(
    pairwise: pd.DataFrame,
    global_stats: pd.DataFrame,
    per_class: pd.DataFrame,
    divergences: pd.DataFrame,
    confusion: pd.DataFrame,
    robustness: pd.DataFrame,
    ids: list[int],
) -> None:
    def _md(df: pd.DataFrame) -> str:
        return df.to_markdown(index=False, floatfmt=".3f") + "\n"

    parts = ["# Concordância entre anotadores\n"]
    parts.append(
        "Gerado por `research.release.annotator_agreement` a partir de "
        f"`dataset/annotators/` ({len(ids)} documentos comuns aos três anotadores). "
        "O anotador 1 é a anotação original pós-auditoria Cleanlab (idêntica à "
        "release corrigida); os anotadores 2 e 3 anotaram de forma independente "
        "e cega. Os CSVs ao lado são as fontes canônicas.\n"
    )
    parts.append("## (a) Concordância par-a-par\n")
    parts.append(
        "κ de Cohen no nível de token (O + 4 classes, tokenização canônica), "
        "F1 de span (IoU ≥ 0,5, matching guloso bipartido — a métrica do "
        "protocolo de avaliação) e κ de presença de entidade no documento.\n"
    )
    parts.append(_md(pairwise))
    parts.append("## (b) Concordância global (3 anotadores)\n")
    parts.append(_md(global_stats))
    parts.append("## (c) Concordância por classe\n")
    parts.append(_md(per_class))
    parts.append("## (d) Tipologia das divergências de span\n")
    parts.append(
        "`agreement`: spans casados (IoU ≥ 0,5) com mesmo rótulo; "
        "`class_confusion`: casados com rótulos distintos; `boundary`: mesmo "
        "rótulo com sobreposição parcial (0 < IoU < 0,5); `presence_only_*`: "
        "span sem contraparte no outro anotador.\n"
    )
    parts.append(_md(divergences))
    if not confusion.empty:
        parts.append("### Confusões de classe\n")
        parts.append(_md(confusion))
    parts.append("## (e) Robustez: anotadores vs. gold pré-correção\n")
    parts.append(
        "Mesmas medidas tomando como referência a anotação original *antes* "
        "da auditoria Cleanlab (`decicontas-before-correction`).\n"
    )
    parts.append(_md(robustness))
    (OUTPUT_ROOT / "AGREEMENT.md").write_text("\n".join(parts), encoding="utf-8")
    logger.info("wrote %s", OUTPUT_ROOT / "AGREEMENT.md")


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
