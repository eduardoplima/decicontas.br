# DeciContas.br Named Entity Recognition Pipeline

This repository contains the Python code and configuration for extracting named entities from decisions of the Rio Grande do Norte State Court of Accounts (TCE/RN), focused on auditing information such as fines, obligations, reimbursements, and recommendations. The project is part of the DeciContas.br dataset initiative.

The goal is to convert unstructured text in these decisions into structured data that can be monitored and analyzed systematically. The solution leverages Large Language Models (LLMs) deployed through Azure OpenAI and OpenRouter, combining few-shot prompting, function calling / JSON-schema structured output, and a suite of prompt engineering techniques (chain-of-thought, negative examples, role prompting, explicit definitions, two-stage classify-then-extract, self-refinement, dynamic few-shot, self-consistency). Supervised baselines (BiLSTM-CRF, BERTimbau, Legal-BERTimbau) are included for comparison.

## Project Structure

```
tools/                          # Python package — import as `tools.*`
├── schema.py                   # Pydantic models: raw NER (NERDecisao) and enriched (Decisao) layers
├── models.py                   # SQLAlchemy ORMs: NERDecisao/NER*, Obrigacao, Recomendacao, Beneficio, Processed* bridges
├── prompt.py                   # FEW_SHOT_NER_PROMPT, prompt builders
├── fewshot.py                  # 12 hand-curated (text, NERDecisao) examples and message formatters
├── prompt_engineering.py       # CoT, negative examples, role, definitions, two-stage, self-refinement,
│                               # dynamic few-shot, self-consistency
├── dataset.py                  # Loaders for Label Studio exports under dataset/labeled_data/
└── utils.py                    # DB engines (DB_PROCESSOS / DB_DECISOES / DB_SIAI), SQL loaders,
                                # extract/insert helpers, PipelineSpec-driven pipeline runners

sql/                            # Parameterised .sql files read at runtime
├── decisions_base.sql                # shared SELECT for the three decisions_by_* lookups
├── obligations_nonprocessed.sql      # driver query for the obrigação pipeline
├── recommendations_nonprocessed.sql  # driver query for the recomendação pipeline
├── citations_by_process.sql
├── citations_by_process_after.sql
├── responsible_unit.sql
├── units.sql
└── augmented_decisions.sql

notebooks/                      # Jupyter notebooks (each prepends a CWD-guard cell)
├── ner.ipynb                        # NER extraction across Azure OpenAI models
├── ner_llm.ipynb                    # Multi-model runs via OpenRouter + 8 prompt-engineering techniques
├── ner_experiments.ipynb            # Aggregates dataset/experiments/ outputs
├── ner_bilstm_bert.ipynb            # Supervised baseline: BiLSTM-CRF, BERTimbau, Legal-BERTimbau
├── ner_bilstm_bert_kfold.ipynb      # K-fold variant of the supervised baselines
├── etl.ipynb                        # DB-backed obrigação/recomendação pipelines
├── services.ipynb                   # DB-facing helpers (units, responsibles, citations)
├── merge_labelstudio.ipynb          # Label Studio round-trip
├── error_analysis.ipynb             # Error taxonomy, confusion matrix
├── statistical_significance.ipynb   # Comparative evaluation
├── ner_results.ipynb                # Result aggregation
├── sampling_gpt54_function_calling.ipynb
├── aed-decicontas.ipynb             # Exploratory data analysis
├── eda.ipynb
└── lab.ipynb

dataset/
├── labeled_data/               # Label Studio gold annotations (may contain PII — do not commit)
├── experiments/                # Per-model/technique JSON outputs
│   ├── few_shot_and_supervised/
│   ├── function_calling_json_schema/
│   └── prompt_engineering/
└── results/                    # Consolidated checkpoints, JSON outputs, and markdown summaries
```

## Getting started

Requires Python `>=3.12,<3.13`.

```bash
poetry install
poetry run python -m ipykernel install --user --name=decicontas-br
```

Notebooks can be launched from either the repo root or `notebooks/`: a guard cell normalises the working directory so relative paths (`dataset/...`, `sql/...`) resolve either way.

## Pipelines

1. **NER extraction (stage 1).** `run_ner_pipeline_for_dataframe` reads decisions, asks the LLM for a `NERDecisao` (raw span-level lists per type: multa, obrigação, ressarcimento, recomendação), and persists the result into `NERDecisao` + `NER*` tables keyed by the triple `(IdProcesso, IdComposicaoPauta, IdVotoPauta)`.

2. **Structured extraction (stage 2).** `run_obrigacao_pipeline` / `run_recomendacao_pipeline` iterate NER spans, resolve the responsible person (`get_responsible_unit` + fuzzy unit match), look up the deadline via citations (`get_deadline_from_citations`), and prompt the LLM for a fully populated `Obrigacao` / `Recomendacao`. Inserts are idempotent through `Processed*ORM` bridge tables. Both pipelines share a single `PipelineSpec`-driven generic under the hood.

## Legal Context

This project is aligned with TCE/RN rules governing:

- execution of fines and reimbursements ([Resolução 013/2015](./docs/Resolução_0132015_Dispõe_sobre_a_execução_das_decisões_TCERN__multaressarcimento.pdf))

It can support future auditing and compliance workflows by generating structured datasets from free-form decisions.

## Credits

- Inspired by LexCare.BR and its cross-domain NER approach
- Developed for the DeciContas.br research project
- Data sources: Tribunal de Contas do Estado do Rio Grande do Norte
- Developed in Python with langchain, pydantic, and Azure OpenAI
