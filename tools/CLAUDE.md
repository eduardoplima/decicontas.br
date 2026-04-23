# tools/ — research library

This is the framework-agnostic research code: NER pipelines, Pydantic schemas, prompts, SQLAlchemy ORMs. Imported by `backend/app/` and by notebooks under `notebooks/`. Does not depend on FastAPI, Next.js, or any web framework.

## Environment

- Python `>=3.12,<3.13`. Dependencies declared in `tools/pyproject.toml`, a uv workspace member. `uv sync` at the repo root installs the package in editable mode; add `--extra llm` for the LangChain/OpenAI stack, `--extra experiments` for the full supervised/evaluation stack.
- Runtime config from `.env` at repo root (loaded via `dotenv` in `tools/utils.py`). Required:
  - `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `OPENAI_API_VERSION` — required by notebook cells that construct Azure OpenAI extractors. Importing `tools.utils` does not need them.
  - `SQL_SERVER_HOST`, `SQL_SERVER_USER`, `SQL_SERVER_PASS`, `SQL_SERVER_PORT` — MSSQL instance (`mssql+pymssql`).
  - `SQL_SERVER_DB_PROCESSOS` (default `processo`), `SQL_SERVER_DB_DECISOES` (default `BdDIP`), `SQL_SERVER_DB_SIAI` (default `BdSIAI`) — read into `DB_PROCESSOS` / `DB_DECISOES` / `DB_SIAI` in `tools/utils.py`. Staging tables live in `DB_DECISOES`.

## Running notebooks

- Kernel install (once): `uv sync --package tools --extra experiments && uv run python -m ipykernel install --user --name=decicontas-br`.
- Notebooks import from `tools/` using the repo root as CWD. Always launch from the repo root so `dataset/...`, `sql/...` resolve.
- Key notebooks by purpose:
  - `ner.ipynb`, `ner_experiments.ipynb`, `ner_llm.ipynb` — NER extraction across models / prompting strategies.
  - `ner_bilstm_bert*.ipynb` — supervised NER baselines.
  - `error_analysis.ipynb`, `statistical_significance.ipynb`, `ner_results.ipynb` — evaluation on outputs under `dataset/experiments/`.
  - `services.ipynb`, `merge_labelstudio.ipynb` — data ingestion and Label Studio round-trip.
  - `etl_scratch.ipynb` — only for debugging `tools.etl.*`; does not orchestrate production runs. The former `etl.ipynb` has been removed.

## Architecture

Pipeline that converts free-text TCE/RN decisions (`texto_acordao`) into structured audit data stored in MSSQL, with LLM extraction in between. Five building blocks:

**`tools/schema.py` — three layers of Pydantic models:**
- `NERMulta` / `NERObrigacao` / `NERRessarcimento` / `NERRecomendacao` + `NERDecisao` — raw span-level extractions (only a `descricao_*` string). First LLM pass.
- `Multa` / `Obrigacao` / `Ressarcimento` / `Recomendacao` + `Decisao` — fully structured records. Second LLM pass enriches each NER span into one of these.
- `CitationChoice` / `ResponsibleChoice` — structured outputs for helper LLMs.

**`tools/models.py` — SQLAlchemy ORMs mirroring the schema split:**
- `NERDecisaoORM` (+ `NERMultaORM`, `NERObrigacaoORM`, `NERRessarcimentoORM`, `NERRecomendacaoORM`) — raw NER output keyed by `(IdProcesso, IdComposicaoPauta, IdVotoPauta)`.
- `ObrigacaoORM`, `RecomendacaoORM`, `BeneficioORM` — final structured tables.
- `Processed*ORM` (`DecisaoProcessada`, `MultaProcessada`, `RessarcimentoProcessado`, `ObrigacaoProcessada`, `RecomendacaoProcessada`) — idempotency bridge tables. Always check before inserting.

**`tools/prompt.py` + `tools/fewshot.py` + `tools/prompt_engineering.py`** — prompt construction and alternative strategies (CoT, negative examples, role, definitions, two-stage, self-refinement, dynamic few-shot, self-consistency).

**`tools/utils.py` — pipelines and DB glue:**
- `get_connection(db)` / `get_session(db)` — fresh MSSQL engine per DB. Pipelines are cross-database: metadata from `DB_PROCESSOS`, NER/final/staging tables in `DB_DECISOES`, unit lookups in `DB_SIAI`.
- `run_ner_pipeline_for_dataframe()` — stage 1. `overwrite=False` skips rows with an existing `NERDecisaoORM` for the `(process, composition, vote)` triple.
- `run_obrigacao_pipeline()` / `run_recomendacao_pipeline()` — stage 2. Resolve unit (fuzzy match against `sql/units.sql`), pick deadline (`get_deadline_from_citations`), prompt the extractor, and **write to the staging tables** (not directly to `Obrigacao` / `Recomendacao`). The approval transaction in `backend/app/review/service.py` is the only writer to the final tables.
- SQL under `sql/` is read from disk and `.format(...)`-ed with query parameters. Inputs come from trusted internal lists — keep it that way.

## SQL files

- `sql/decisions_full_text.sql` — fetches full decision context (including `texto_acordao`, responsável, órgão, sessão) from `processo.dbo.vw_ia_votos_acordaos_decisoes` joined with `Processos`, `Orgaos`, `Pro_ProcessosResponsavelDespesa`, `GenPessoa`. **Canonical source of `texto_acordao`** for both stage-2 extraction and the review UI — do not reconstruct the text from any other view.
- `sql/obligations_nonprocessed.sql` / `sql/recommendations_nonprocessed.sql` — driver queries for the stage-2 pipelines. Their `NOT EXISTS` clauses must exclude rows already in `ObrigacaoStaging` / `RecomendacaoStaging` with status in (`pending`, `approved`), otherwise the pipeline re-queues mid-review rows.
- Other SQL files (`decisions_base.sql`, `citations_by_process*.sql`, `responsible_unit.sql`, `units.sql`, `augmented_decisions.sql`) are unchanged.

## Experiments and outputs

- `dataset/experiments/` holds per-model JSON results by technique (`few_shot_and_supervised/`, `function_calling_json_schema/`, `prompt_engineering/`). Naming: `models_results_decicontas_<model>_<technique>.json`.
- `dataset/results/` holds checkpoints and aggregated outputs consumed by evaluation notebooks.
- Supervised models are stored as `.pkl` alongside JSON metrics.

## Conventions

- Decision identity: the triple `(IdProcesso, IdComposicaoPauta, IdVotoPauta)`. Always carry all three.
- A row may have `id_ner_obrigacao` / `id_ner_recomendacao` under several casings; `insert_obrigacao` handles variants via `row.get(...)` fallbacks — follow the same pattern.
- `safe_int()` exists because pandas mixes `NaN`/`float`/`str` in ID columns. Prefer it over `int(...)` when reading from dataframes.

## Rules for Claude Code in `tools/`

- **No web framework imports.** No FastAPI, no Pydantic DTOs specific to HTTP, no route decorators. If you need something from the web layer, the abstraction is wrong — stop and ask.
- **No LLM clients or DB engines instantiated at import time.** Factory functions only, so tests and the backend can import without side effects.
- **Before editing a notebook**, prefer extracting the logic to `tools/` and calling it from the notebook.
- **After refactoring a module used by a notebook**, re-execute it (`jupyter nbconvert --execute --to notebook --inplace`). If a cell calls the LLM or the DB and is expensive, skip and flag it.
- **Don't reintroduce `etl.ipynb`.** Scratch work goes in `notebooks/etl_scratch.ipynb`.

## Testing (`tools/`)

- Put tests in `backend/tests/tools/`, mirroring the `tools/` layout.
- Target pure functions first: `translate_golden`, `safe_int`, Pydantic schema validation, prompt builders with deterministic input, `find_span_in_text`.
- Mock `AzureChatOpenAI` and SQLAlchemy sessions. Never hit the real API or DB from unit tests.
- Run with `cd backend && uv run pytest tests/tools`. Integration tests (real MSSQL / Redis / Azure) are marked `@pytest.mark.integration` and skipped by default — run them with `uv run pytest -m integration`.
- Shared fixtures in `backend/tests/conftest.py`: `tmp_env` (autouse, sets dummy env vars), `in_memory_engine`, `db_session`, `mock_llm`, `frozen_time`. Tools-specific fixtures in `backend/tests/tools/conftest.py`: `sample_texto_acordao`, `sample_ner_decisao`.