# DeciContas.br

Companion repository for the dissertation **"Reconhecimento de Entidades Nomeadas em Decisões do TCE/RN"**. Hosts the labelled corpus, evaluation pipelines, supervised baselines, and the auditing / release infrastructure used to produce the results reported in the thesis.

## What's here

```
decicontas.br/
├── dataset/              # 861-document corpus, gold + cleanlab-corrected releases, results
│   ├── raw/              # raw scraped corpora + Label Studio imports (provenance)
│   ├── labeled_data/     # original Label Studio export
│   ├── errors/           # cleanlab audit decisions (dataset-corrections.json)
│   ├── release/          # publishable bundles (JSON, JSONL, CoNLL, BRAT)
│   └── results/          # models_outputs/ (canonical, temp=0) + old_experiments/ (archived)
├── notebooks/            # exploratory analysis, supervised baselines, LLM evaluation
│   ├── eda_cleanlab.ipynb        # EDA of the cleanlab audit and label transitions
│   ├── aed_decicontas.ipynb      # EDA of the corpus
│   ├── ner_llm.ipynb / ner_experiments.ipynb / ner_results.ipynb
│   ├── ner_bilstm_bert_kfold.ipynb
│   ├── error_analysis.ipynb
│   └── statistical_significance.ipynb
├── research/             # Python package consumed by notebooks and scripts
│   ├── dataset_io.py     # canonical tokenisation + dataset loader
│   ├── dataset.py        # DataFrame helper (legacy notebooks)
│   ├── ner_metrics.py    # spaCy-based token/span F1, bipartite IoU matcher
│   ├── schema.py         # Pydantic NER models
│   ├── prompt.py / prompt_engineering.py / fewshot.py
│   ├── release/          # dataset export, chapter-5 number collection, bootstrap
│   └── kfold/            # supervised 5-fold CV (BiLSTM-CRF + BERTimbau variants)
└── tests/                # pytest suite for research code
```

## Quickstart

```bash
# 1. install
uv sync

# 2. regenerate every Chapter 5 number from the cleanlab-corrected gold
uv run python -m research.release.chapter5_numbers

# 3. regenerate the 12 result figures
uv run python -m research.release.regenerate_figures

# 4. rerun the bootstrap significance pipeline
uv run python -m research.release.bootstrap_significance --quiet

# 5. run the supervised k-fold pipeline (slow: ~13h on Apple Silicon MPS)
DECICONTAS_DATASET_PATH=dataset/release/decicontas/decicontas-labelstudio.json \
uv run python -m research.kfold.orchestrate

# 6. run tests
uv run pytest tests/
```

## Reproducing the dissertation

The single document `dataset/results/models_outputs/chapter5/REPORT.md` is the canonical, auto-contained reference for every number cited in Chapter 5. Each subsection corresponds to a block of the chapter and shows the table inline plus the source CSV. Re-running step 2 above regenerates it deterministically from the released dataset.

For the methodology behind the cleanlab audit, see `notebooks/eda_cleanlab.ipynb`.

## Dataset versions

- **decicontas-before-correction** (`dataset/release/decicontas-before-correction/`): the 861 documents that survived filtering the 5 few-shot leakage cases out of the master 866-document Label Studio export. Gold annotations are the originals.
- **decicontas** (`dataset/release/decicontas/`): same 861 documents with the 567 cleanlab-flagged groups (ensemble confidence ≥ 0.95) reviewed and applied. The remaining 227 below-threshold groups stay at gold. This is the canonical release.

Both ship in JSON (Label Studio + clean), JSONL (HuggingFace `datasets`-compatible), CoNLL-2003 BIO, and BRAT standoff formats.

## Citation

If you use this dataset or the results, please cite the dissertation. A BibTeX entry will be added here at publication.

## License

See [LICENSE](LICENSE).
