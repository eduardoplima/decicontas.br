"""Descriptive and linguistic analysis of the decicontas.br corpus (Chapter 4).

Produces the tables behind the "Análise descritiva e linguística do corpus"
section: entity counts per document, class co-occurrence, relative span
position (proxy for dispositivo vs. fundamentação), span-initial n-grams,
performative-verb markers, and a lexical comparison against LeNER-Br.

All inputs come from the corrected release bundle
(``dataset/release/decicontas/decicontas.json``), whose tokenisation and BIO
construction originate in :mod:`research.dataset_io` — no re-tokenisation
happens here. Outputs land in ``dataset/results/models_outputs/chapter4/``
as one CSV per table plus a self-contained ``REPORT.md``.

Run:
    uv run python -m research.release.corpus_analysis
    uv run python -m research.release.corpus_analysis --skip-lener  # offline
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
import unicodedata
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

import pandas as pd

from research.dataset_io import ENTITY_LABELS
from research.release import paths

OUTPUT_ROOT = paths.CHAPTER4_DIR
RELEASE_JSON = paths.RELEASE_DIR / "decicontas.json"

# Pinned LeNER-Br source. The canonical repo (``peluz/lener_br``) is a
# script-based dataset that modern ``datasets`` refuses to run, so we read the
# Hub's parquet auto-conversion, pinned to a fixed commit for reproducibility.
LENER_REPO = "peluz/lener_br"
LENER_REVISION = "91d05de7e811cbea249b5888cb02cd527c31a8e7"  # refs/convert/parquet
LENER_SPLITS = ("train", "validation", "test")

logger = logging.getLogger("research.release.corpus_analysis")

_TOKEN_RE = re.compile(r"\S+")

# Lexical markers of performative force in the dispositive section. Stems are
# matched as prefixes of normalised (lowercase, accent-stripped) tokens so a
# single stem covers the inflected forms ("determino", "determinar",
# "determinando", ...).
PERFORMATIVE_STEMS = (
    "determin",
    "julg",
    "aplic",
    "recomend",
    "conden",
    "imput",
    "mult",
    "ressarc",
    "restitu",
    "obrig",
    "fix",
)

# How many tokens from the span opening count as its "initial" segment when
# looking for performative markers.
SPAN_OPENING_WINDOW = 5


def _normalize_token(tok: str) -> str:
    tok = unicodedata.normalize("NFKD", tok.lower())
    tok = "".join(c for c in tok if not unicodedata.combining(c))
    return tok.strip(".,;:()[]{}\"'§ºª°–—-/\\")


def load_corpus(path: Path = RELEASE_JSON) -> list[dict]:
    """Load the corrected release documents (861 docs, fewshot already dropped)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ----- (a) entities per document ------------------------------------------


def entities_per_document(docs: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-document entity counts and the 0/1/2/3+ histogram (DS-p.42)."""
    rows = []
    for d in docs:
        labels = Counter(e["label"] for e in d["entities"])
        rows.append(
            {
                "doc_id": d["id"],
                "n_entities": sum(labels.values()),
                **{lab: labels.get(lab, 0) for lab in ENTITY_LABELS},
            }
        )
    per_doc = pd.DataFrame(rows)

    def _bucket(n: int) -> str:
        return str(n) if n < 3 else "3+"

    hist_rows = []
    buckets = per_doc["n_entities"].map(_bucket)
    n_informative = int((per_doc["n_entities"] > 0).sum())
    for b in ("0", "1", "2", "3+"):
        count = int((buckets == b).sum())
        hist_rows.append(
            {
                "n_entities": b,
                "n_docs": count,
                "pct_all_docs": round(count / len(per_doc), 4) if len(per_doc) else 0.0,
                "pct_informative_docs": (
                    round(count / n_informative, 4) if b != "0" and n_informative else None
                ),
            }
        )
    hist = pd.DataFrame(hist_rows)
    return per_doc, hist


# ----- (b) class co-occurrence --------------------------------------------


def class_cooccurrence(docs: list[dict]) -> pd.DataFrame:
    """Document-level co-occurrence matrix of the four classes.

    Diagonal: number of documents containing the class. Off-diagonal:
    documents containing both classes.
    """
    matrix = pd.DataFrame(0, index=list(ENTITY_LABELS), columns=list(ENTITY_LABELS))
    for d in docs:
        present = sorted({e["label"] for e in d["entities"]})
        for lab in present:
            matrix.loc[lab, lab] += 1
        for a, b in combinations(present, 2):
            matrix.loc[a, b] += 1
            matrix.loc[b, a] += 1
    matrix.index.name = "label"
    return matrix


# ----- (c) span position in the document ----------------------------------


def span_positions(docs: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Relative character position of every span within its document.

    Without structural segmentation of the acórdão, the relative position is
    the declared approximation for dispositivo vs. fundamentação: dispositive
    commands cluster near the end of the decision text.
    """
    rows = []
    for d in docs:
        n = len(d["text"])
        if not n:
            continue
        for e in d["entities"]:
            rows.append(
                {
                    "doc_id": d["id"],
                    "label": e["label"],
                    "start_rel": e["start"] / n,
                    "end_rel": e["end"] / n,
                    "center_rel": (e["start"] + e["end"]) / (2 * n),
                    "span_chars": e["end"] - e["start"],
                }
            )
    long_df = pd.DataFrame(rows)
    summary = (
        long_df.groupby("label")["center_rel"]
        .agg(["count", "mean", "median", lambda s: s.quantile(0.25), lambda s: s.quantile(0.75)])
        .rename(columns={"<lambda_0>": "q25", "<lambda_1>": "q75"})
        .reindex(list(ENTITY_LABELS))
        .reset_index()
    )
    summary["frac_in_final_third"] = summary["label"].map(
        lambda lab: round(
            float((long_df[long_df["label"] == lab]["center_rel"] > 2 / 3).mean()), 4
        )
    )
    return long_df, summary


# ----- (d) span-initial n-grams and performative verbs --------------------


def span_initial_ngrams(docs: list[dict], n_max: int = 3, top_k: int = 15) -> pd.DataFrame:
    """Most frequent lowercase n-grams opening the spans of each class."""
    counters: dict[tuple[str, int], Counter] = {
        (lab, n): Counter() for lab in ENTITY_LABELS for n in range(1, n_max + 1)
    }
    for d in docs:
        for e in d["entities"]:
            span_text = d["text"][e["start"] : e["end"]]
            toks = [t.group().lower() for t in _TOKEN_RE.finditer(span_text)]
            for n in range(1, n_max + 1):
                if len(toks) >= n:
                    counters[(e["label"], n)][" ".join(toks[:n])] += 1
    rows = []
    for (lab, n), counter in counters.items():
        total = sum(counter.values())
        for ngram, count in counter.most_common(top_k):
            rows.append(
                {
                    "label": lab,
                    "n": n,
                    "ngram": ngram,
                    "count": count,
                    "pct_of_spans": round(count / total, 4) if total else 0.0,
                }
            )
    return pd.DataFrame(rows)


def performative_verbs(docs: list[dict]) -> pd.DataFrame:
    """Frequency of performative stems at the span opening vs. anywhere else.

    ``span_initial``: spans whose first ``SPAN_OPENING_WINDOW`` tokens contain
    the stem. ``doc_rate``: fraction of documents whose full text contains the
    stem — the baseline showing the marker is not simply ubiquitous.
    """
    span_hits: dict[tuple[str, str], int] = Counter()
    span_totals: Counter = Counter()
    docs_with_stem: Counter = Counter()
    for d in docs:
        doc_norm = {_normalize_token(t.group()) for t in _TOKEN_RE.finditer(d["text"])}
        for stem in PERFORMATIVE_STEMS:
            if any(tok.startswith(stem) for tok in doc_norm):
                docs_with_stem[stem] += 1
        for e in d["entities"]:
            span_totals[e["label"]] += 1
            toks = [
                _normalize_token(t.group())
                for t in _TOKEN_RE.finditer(d["text"][e["start"] : e["end"]])
            ][:SPAN_OPENING_WINDOW]
            for stem in PERFORMATIVE_STEMS:
                if any(tok.startswith(stem) for tok in toks):
                    span_hits[(e["label"], stem)] += 1
    rows = []
    for stem in PERFORMATIVE_STEMS:
        row: dict[str, Any] = {
            "stem": stem,
            "docs_with_stem": docs_with_stem.get(stem, 0),
            "doc_rate": round(docs_with_stem.get(stem, 0) / len(docs), 4) if docs else 0.0,
        }
        for lab in ENTITY_LABELS:
            hits = span_hits.get((lab, stem), 0)
            total = span_totals.get(lab, 0)
            row[f"{lab}_spans"] = hits
            row[f"{lab}_rate"] = round(hits / total, 4) if total else 0.0
        rows.append(row)
    return pd.DataFrame(rows)


# ----- (e) lexical comparison with LeNER-Br -------------------------------


def _vocab_counter(token_lists: list[list[str]]) -> Counter:
    counter: Counter = Counter()
    for toks in token_lists:
        for tok in toks:
            norm = _normalize_token(tok)
            if len(norm) >= 2 and any(c.isalpha() for c in norm):
                counter[norm] += 1
    return counter


def _log_odds(counter_a: Counter, counter_b: Counter, min_count: int = 10) -> pd.DataFrame:
    """Log-odds ratio with informative Dirichlet prior (Monroe et al., 2008)."""
    prior = counter_a + counter_b
    n_a = sum(counter_a.values())
    n_b = sum(counter_b.values())
    n_prior = sum(prior.values())
    rows = []
    for word, p in prior.items():
        if counter_a.get(word, 0) + counter_b.get(word, 0) < min_count:
            continue
        a = counter_a.get(word, 0)
        b = counter_b.get(word, 0)
        alpha = p / n_prior * 1000  # scaled prior
        delta = math.log((a + alpha) / (n_a + 1000 - a - alpha)) - math.log(
            (b + alpha) / (n_b + 1000 - b - alpha)
        )
        sigma2 = 1 / (a + alpha) + 1 / (b + alpha)
        rows.append({"word": word, "log_odds_z": delta / math.sqrt(sigma2)})
    return pd.DataFrame(rows).sort_values("log_odds_z", ascending=False).reset_index(drop=True)


def lener_comparison(
    docs: list[dict], top_n: int = 5000, top_terms: int = 25
) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Vocabulary overlap and distinctive terms vs. LeNER-Br.

    LeNER-Br carries different entity classes (legislation, jurisprudence,
    person, ...), so the comparison is strictly lexical: Jaccard of the top-N
    vocabularies, OOV rates in both directions, and the tokens most distinctive
    of each corpus by z-scored log-odds.
    """
    try:
        from huggingface_hub import hf_hub_download  # noqa: PLC0415 — network-bound
    except ImportError:
        logger.warning("`huggingface_hub` not installed; skipping LeNER-Br comparison")
        return None
    lener_tokens: list[list[str]] = []
    try:
        for split in LENER_SPLITS:
            local = hf_hub_download(
                LENER_REPO,
                f"lener_br/{split}/0000.parquet",
                repo_type="dataset",
                revision=LENER_REVISION,
            )
            lener_tokens.extend(pd.read_parquet(local)["tokens"].tolist())
    except Exception as exc:  # noqa: BLE001 — network failures alike
        logger.warning("could not load %s (%s); skipping comparison", LENER_REPO, exc)
        return None
    deci_tokens = [d["tokens"] for d in docs]

    deci_vocab = _vocab_counter(deci_tokens)
    lener_vocab = _vocab_counter(lener_tokens)

    deci_top = {w for w, _ in deci_vocab.most_common(top_n)}
    lener_top = {w for w, _ in lener_vocab.most_common(top_n)}
    inter = deci_top & lener_top
    union = deci_top | lener_top

    overlap = pd.DataFrame(
        [
            {"metric": "decicontas_types", "value": len(deci_vocab)},
            {"metric": "lener_types", "value": len(lener_vocab)},
            {"metric": f"jaccard_top{top_n}", "value": round(len(inter) / len(union), 4)},
            {
                "metric": f"decicontas_top{top_n}_oov_in_lener",
                "value": round(len(deci_top - set(lener_vocab)) / len(deci_top), 4),
            },
            {
                "metric": f"lener_top{top_n}_oov_in_decicontas",
                "value": round(len(lener_top - set(deci_vocab)) / len(lener_top), 4),
            },
            {"metric": "lener_docs", "value": len(lener_tokens)},
            {"metric": "decicontas_docs", "value": len(deci_tokens)},
        ]
    )

    lo = _log_odds(deci_vocab, lener_vocab)
    distinctive = pd.concat(
        [
            lo.head(top_terms).assign(corpus="decicontas"),
            lo.tail(top_terms).iloc[::-1].assign(corpus="lener_br"),
        ]
    ).reset_index(drop=True)
    return overlap, distinctive


# ----- orchestration + REPORT.md ------------------------------------------


def _md(df: pd.DataFrame, float_fmt: str = ".4f") -> str:
    return df.to_markdown(index=False, floatfmt=float_fmt) + "\n"


def run(skip_lener: bool = False) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    docs = load_corpus()
    logger.info("loaded %d documents from %s", len(docs), RELEASE_JSON)

    per_doc, hist = entities_per_document(docs)
    per_doc.to_csv(OUTPUT_ROOT / "A41_entities_per_doc.csv", index=False)
    hist.to_csv(OUTPUT_ROOT / "A41_entities_per_doc_hist.csv", index=False)

    cooc = class_cooccurrence(docs)
    cooc.to_csv(OUTPUT_ROOT / "A41_cooccurrence.csv")

    pos_long, pos_summary = span_positions(docs)
    pos_long.to_csv(OUTPUT_ROOT / "A41_span_positions.csv", index=False)
    pos_summary.to_csv(OUTPUT_ROOT / "A41_span_position_summary.csv", index=False)

    ngrams = span_initial_ngrams(docs)
    ngrams.to_csv(OUTPUT_ROOT / "A41_span_initial_ngrams.csv", index=False)

    verbs = performative_verbs(docs)
    verbs.to_csv(OUTPUT_ROOT / "A41_performative_verbs.csv", index=False)

    lener = None if skip_lener else lener_comparison(docs)
    if lener is not None:
        overlap, distinctive = lener
        overlap.to_csv(OUTPUT_ROOT / "A41_lener_vocab_overlap.csv", index=False)
        distinctive.to_csv(OUTPUT_ROOT / "A41_lener_distinctive_terms.csv", index=False)

    parts = ["# Capítulo 4 — Análise descritiva e linguística do corpus\n"]
    parts.append(
        "Gerado por `research.release.corpus_analysis` a partir de "
        "`dataset/release/decicontas/decicontas.json` (release corrigida, 861 docs). "
        "Os CSVs ao lado são as fontes canônicas.\n"
    )
    parts.append("## (a) Entidades por documento (DS-p.42)\n")
    parts.append(_md(hist))
    parts.append("## (b) Coocorrência de classes no mesmo documento\n")
    parts.append(cooc.reset_index().to_markdown(index=False) + "\n")
    parts.append("## (c) Posição relativa dos spans no documento\n")
    parts.append(
        "Aproximação declarada para dispositivo × fundamentação: sem segmentação "
        "estrutural, usa-se a posição relativa do centro do span "
        "(`center_rel` ∈ [0, 1]); `frac_in_final_third` é a fração de spans no "
        "terço final do texto.\n"
    )
    parts.append(_md(pos_summary))
    parts.append("## (d) N-gramas iniciais dos spans por classe\n")
    parts.append(_md(ngrams[ngrams["n"] <= 2], float_fmt=".4f"))
    parts.append("## (d') Verbos/marcadores performativos\n")
    parts.append(
        f"Radicais buscados nos {SPAN_OPENING_WINDOW} primeiros tokens do span "
        "(colunas `*_rate` = fração dos spans da classe) e no documento inteiro "
        "(`doc_rate`).\n"
    )
    parts.append(_md(verbs))
    if lener is not None:
        parts.append("## (e) Comparação lexical com o LeNER-Br\n")
        parts.append(_md(lener[0]))
        parts.append("**Termos mais distintivos (log-odds com prior de Dirichlet, z):**\n")
        parts.append(_md(lener[1]))
    else:
        parts.append("## (e) Comparação lexical com o LeNER-Br\n")
        parts.append("_Pulada nesta execução (`--skip-lener` ou download indisponível)._\n")
    (OUTPUT_ROOT / "REPORT.md").write_text("\n".join(parts), encoding="utf-8")
    logger.info("wrote %s", OUTPUT_ROOT / "REPORT.md")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-lener", action="store_true", help="skip the LeNER-Br download")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run(skip_lener=args.skip_lener)


if __name__ == "__main__":
    main()
