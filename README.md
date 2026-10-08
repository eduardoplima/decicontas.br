# DeciContas.br

**A Named Entity Recognition dataset of Brazilian audit-court decisions, and a controlled comparison of 19 extraction models on it.**

[![License: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-blue.svg)](https://creativecommons.org/licenses/by/4.0/)
[![License: MIT](https://img.shields.io/badge/code-MIT-green.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](pyproject.toml)

Brazilian **Courts of Accounts** (*Tribunais de Contas*) audit public spending. Their
rulings impose fines, binding obligations, reimbursements to the treasury and
non-binding recommendations — and each of those must be transcribed by hand into an
institutional registry that tracks whether the ruling was complied with. This
repository releases the corpus built to automate that step, together with everything
needed to reproduce the reported results.

The decisions come from the **Court of Accounts of the State of Rio Grande do Norte**
(TCE/RN, *Tribunal de Contas do Estado do Rio Grande do Norte*). It is, to our
knowledge, the first NER dataset over decisions of a Brazilian Court of Accounts.

Companion artefact to the dissertation *"Reconhecimento de Entidades Nomeadas em
Decisões do TCE/RN"* (Named Entity Recognition in TCE/RN Decisions), UFRN.

---

## The four entity types

Labels are kept in Portuguese because they name legal institutes, each with its own
enforcement regime — translating them would misrepresent the corpus.

| Label | What it is | Count |
|---|---|---:|
| `MULTA` | A pecuniary **fine** for administrative or fiscal misconduct | 203 |
| `OBRIGACAO` | A binding **obligation** imposed on the audited body | 123 |
| `RESSARCIMENTO` | A mandated **reimbursement** to the public treasury | 63 |
| `RECOMENDACAO` | A formally documented, non-binding **recommendation** | 52 |

**861 documents, 441 entities.** Only 231 documents carry an entity; the remaining
630 are true negatives — filings and clean-account judgments with no registrable
command. They are kept deliberately: in production the system must also learn *not*
to extract. Spans are long (per-class medians of 186–357 characters), so evaluation
uses partial matching (IoU ≥ 0.5) rather than exact boundaries.

## Get the data

**Download** — grab a single file from the [latest release](https://github.com/eduardoplima/decicontas.br/releases/latest),
no clone required. **Or, in a clone**, the bundles are under [`data/`](data)
(a shortcut to `dataset/release/`).

```python
import json

docs = [json.loads(line) for line in open("data/decicontas/decicontas.jsonl")]
print(len(docs), sum(len(d["spans"]) for d in docs))   # 861 441
```

With HuggingFace `datasets`:

```python
from datasets import load_dataset

ds = load_dataset("json", data_files="data/decicontas/decicontas.jsonl")["train"]
```

One record, abridged:

```jsonc
{
  "id": "69",
  "text": "Vistos, relatados e discutidos estes autos, acatando o entendimento do ...",
  "tokens": ["Vistos,", "relatados", "e", "discutidos", "..."],
  "ner_tags": ["O", "O", "O", "O", "..."],          // BIO, one per token
  "token_offsets": [[0, 7], [8, 17], "..."],        // character span of each token
  "spans": [
    {"start_char": 266,  "end_char": 731,  "label": "MULTA"},
    {"start_char": 921,  "end_char": 1277, "label": "OBRIGACAO"}
  ]
}
```

Four formats ship per release: **JSON**, **JSONL** (HuggingFace-compatible),
**CoNLL-2003** BIO and **BRAT** standoff. See
[`dataset/release/README.md`](dataset/release/README.md) for the schema of each and
[`DATASHEET.md`](dataset/release/DATASHEET.md) for provenance, collection and intended
uses.

> **Schema note.** `decicontas.jsonl` uses `spans` with `start_char`/`end_char` and a
> string `id`; `decicontas.json` uses `entities` with `start`/`end` and an integer
> `id`. Same annotations, different field names — pick one and stay with it.

## Results

Nine instruction-tuned LLMs under few-shot prompting with structured outputs, against
ten supervised baselines (BiLSTM-CRF, BERTimbau base/large, and seven Portuguese
legal- or government-domain encoders). One protocol for all: span F1 with IoU ≥ 0.5
over whitespace-token indices, paired document-level bootstrap (10,000 resamples) and
Holm correction over a pre-selected family of seventeen contrasts.

**Headline.** The best LLM, the open-weights **DeepSeek-V4-Flash** (macro span F1
**0.742**), exceeds the strongest supervised baseline, the legal-domain
**LegalBert-pt** (**0.660**), by +0.083, 95% CI [+0.021, +0.146], *p* = 0.008 — but
the contrast does *not* survive Holm correction (*p*<sub>Holm</sub> = 0.066). Against
the generic encoders the gap is significant after correction (BERTimbau-base, 0.622:
+0.121, *p*<sub>Holm</sub> < 0.001). LegalBert-pt does not differ significantly from
BERTimbau-large (0.646) or BERTimbau-base, and the other six domain-adapted encoders
rank below both generic ones. The gap to GPT-4.1 (0.717) is +0.025, 95% CI
[−0.001, +0.052], *p* = 0.060 — *not* significant, and not evidence of equivalence
either. The advantage is larger on the minority classes: on `RECOMENDACAO` (52
instances) DeepSeek-V4-Flash and GPT-4.1 both reach span F1 0.667 against at most
0.400 for any supervised model. On micro span F1, LegalBert-pt (0.739) ranks second
overall, just above GPT-4.1 (0.737).

![Precision vs recall, all 19 models](dataset/results/models_outputs/figures/exp1_precision_recall.png)

Supervised models favour precision (0.760–0.901) over recall (0.361–0.678);
competitive LLMs do the opposite. That profile motivates evaluating LLMs as
pre-annotators in a human-in-the-loop pipeline, although the relative cost of
correcting insertions versus omissions was not measured.

<details>
<summary><b>Full ranking — 19 models</b> (sorted by macro span F1)</summary>

| Model | Type | Token F1 | Span P | Span R | Span F1 (micro) | Span F1 (macro) |
|---|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash | LLM | 0.834 | 0.739 | 0.803 | 0.770 | **0.742** |
| GPT-4.1 | LLM | 0.817 | 0.658 | 0.837 | 0.737 | 0.717 |
| GPT-5.1 | LLM | 0.782 | 0.621 | 0.814 | 0.705 | 0.691 |
| GPT-4.1-mini | LLM | 0.794 | 0.596 | 0.844 | 0.699 | 0.684 |
| LegalBert-pt | supervised | 0.782 | 0.848 | 0.655 | 0.739 | 0.660 |
| BERTimbau-large | supervised | 0.782 | 0.779 | 0.678 | 0.725 | 0.646 |
| BERTimbau-base | supervised | 0.773 | 0.790 | 0.664 | 0.722 | 0.622 |
| JurisBERT | supervised | 0.725 | 0.760 | 0.610 | 0.677 | 0.611 |
| BiLSTM-CRF | supervised | 0.745 | 0.777 | 0.594 | 0.674 | 0.601 |
| GPT-5.2 | LLM | 0.752 | 0.506 | 0.800 | 0.620 | 0.595 |
| Qwen2.5-72B | LLM | 0.718 | 0.549 | 0.723 | 0.624 | 0.585 |
| Legal-BERTimbau-base | supervised | 0.751 | 0.810 | 0.619 | 0.702 | 0.566 |
| GovBERT-BR | supervised | 0.705 | 0.901 | 0.578 | 0.704 | 0.555 |
| Legal-BERT-STF | supervised | 0.730 | 0.817 | 0.578 | 0.677 | 0.538 |
| GPT-5-mini | LLM | 0.569 | 0.278 | 0.828 | 0.416 | 0.531 |
| BERTimbauLaw | supervised | 0.726 | 0.855 | 0.574 | 0.687 | 0.506 |
| GPT-4.1-nano | LLM | 0.581 | 0.354 | 0.560 | 0.434 | 0.395 |
| Llama-3.3-70B | LLM | 0.409 | 0.607 | 0.252 | 0.356 | 0.286 |
| LegalBERTPT-br | supervised | 0.537 | 0.820 | 0.361 | 0.501 | 0.284 |

Source: [`model_evaluation/C_main_results.csv`](dataset/results/models_outputs/model_evaluation/C_main_results.csv).
</details>

**Caveats the numbers carry.** Every model sees every document in full: the
encoders read long documents through overlapping 512-subword windows (stride 320) and
the BiLSTM-CRF takes up to 1,100 tokens, so no document is truncated
(`research.release.check_alignment` verifies it). Supervised learning rate and warmup were selected once on
a global 80/20 split rather than inside each cross-validation fold, which can bias
supervised scores upward. The ranking is stable across IoU thresholds 0.3–0.7 and
across all three reference annotations, but changes substantially under exact
matching.

Every number cited in the paper is regenerated into
[`model_evaluation/REPORT.md`](dataset/results/models_outputs/model_evaluation/REPORT.md), one section
per block, each showing its table inline next to the CSV that produced it.

## Annotation quality

Quality is measured, not asserted.

- **Label-error audit.** A confident-learning pass ([cleanlab](https://github.com/cleanlab/cleanlab))
  flagged 794 suspicious token groups; the 567 above an ensemble confidence of 0.95
  were reviewed one by one, and only 23 (4.1%) were actually changed — the audit
  mostly *confirmed* the original annotation. Both versions ship, paired.
- **Inter-annotator agreement.** The whole corpus was independently re-annotated,
  blind, by two staff of the Court unit that feeds the registry. Token-level Fleiss
  κ = **0.865** (pairwise Cohen's κ 0.843–0.899); pairwise span F1 between
  **0.796** and **0.838**. Details in
  [`corpus_and_agreement/AGREEMENT.md`](dataset/results/models_outputs/corpus_and_agreement/AGREEMENT.md).

## Reproduce

```bash
uv sync                                                           # install (Python 3.12)
uv run python -m research.release.evaluation_numbers                # all evaluation CSVs + REPORT.md
uv run python -m research.release.regenerate_figures              # the result figures
uv run python -m research.release.bootstrap_significance --quiet  # bootstrap CIs (N=10,000)
uv run pytest tests/                                              # test suite
```

Those run offline from a clean clone — the model outputs they score are versioned.
Two things are **not** needed to reproduce the tables: API credentials (only for
re-running LLM inference) and a GPU.

Re-running the supervised sweep is the expensive part (~29–32 h on Apple Silicon MPS):

```bash
DECICONTAS_DATASET_PATH=dataset/release/decicontas/decicontas-labelstudio.json \
uv run python -m research.kfold.orchestrate
```

## Repository layout

```
decicontas.br/
├── data/                 # → shortcut to dataset/release/
├── dataset/
│   ├── raw/              # scraped corpora + Label Studio imports (provenance)
│   ├── labeled_data/     # original Label Studio export
│   ├── errors/           # cleanlab audit decisions
│   ├── release/          # publishable bundles + DATASHEET.md + MANIFEST.json
│   └── results/          # models_outputs/ (canonical) + old_experiments/ (archived)
├── notebooks/            # exploratory analysis, baselines, LLM evaluation
├── research/             # the package the notebooks and scripts import
│   ├── dataset_io.py     # canonical tokenisation + BIO construction
│   ├── ner_metrics.py    # token/span F1, IoU bipartite matcher
│   ├── release/          # dataset export, number regeneration, bootstrap
│   └── kfold/            # supervised 5-fold CV
├── scripts/              # analysis + release packaging
└── tests/                # pytest suite
```

## Dataset versions

- **`decicontas/`** — the canonical release: 861 documents with the reviewed
  cleanlab corrections applied.
- **`decicontas-before-correction/`** — the same 861 documents with the original gold
  annotations, so the effect of the audit can be measured.

The 861 come from an 866-document Label Studio export, minus five documents reused
during prompt curation. All five carry no entities.

## Citation

Cite via [`CITATION.cff`](CITATION.cff) — GitHub renders it under *"Cite this
repository"*. A DOI and the BibTeX for the accompanying paper will be added here on
publication.

## License

Dual-licensed, see [`LICENSE`](LICENSE):

- **Data** (`dataset/`) — [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  The underlying decisions are public acts of the TCE/RN; the license covers the
  annotations, tokenisation, release bundles and documentation produced by the authors.
- **Code** (`research/`, `scripts/`, `tests/`, `notebooks/`) — MIT.
