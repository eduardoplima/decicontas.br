# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- Python `>=3.12,<3.13`, dependencies pinned in `pyproject.toml` (Poetry) and mirrored in `requirements.txt`.
- Install: `poetry install` (preferred) or `pip install -r requirements.txt`.
- Runtime config comes from `.env` (loaded via `dotenv` in `tools/utils.py`). Required variables:
  - `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `OPENAI_API_VERSION` — langchain `AzureChatOpenAI` is instantiated at import time in `tools/utils.py`, so these must be set before importing anything from `tools`.
  - `SQL_SERVER_HOST`, `SQL_SERVER_USER`, `SQL_SERVER_PASS`, `SQL_SERVER_PORT` — MSSQL instance (uses `mssql+pymssql`).
  - `SQL_SERVER_DB_PROCESSOS` (typically `processo`) and `SQL_SERVER_DB_DECISOES` (typically `BdDIP`) — pipeline helpers read these to pick the target database.
- `.env` is gitignored — never commit it.

## Running the code

Most work happens in Jupyter notebooks at the repo root; there is no application entry point, CLI, or test suite.
- Launch kernel: `poetry run python -m ipykernel install --user --name=decicontas-br` (once), then open notebooks in VS Code / Jupyter.
- Notebooks import from `tools/` using the repo root as CWD. Always run notebooks from the repo root so relative paths (`dataset/...`, `sql/...`) resolve.
- Key notebooks by purpose:
  - `ner.ipynb`, `ner_experiments.ipynb`, `ner_openrouter_multi_model.ipynb` — running NER extraction across models / prompting strategies.
  - `ner_bilstm_bert*.ipynb` — supervised NER baselines (BiLSTM-CRF, BERTimbau, Legal-BERTimbau).
  - `document_tagging.ipynb` — multi-label document classification.
  - `error_analysis.ipynb`, `statistical_significance.ipynb`, `ner_results.ipynb` — evaluation and reporting on the JSON/pickle outputs under `dataset/experiments/`.
  - `services.ipynb`, `merge_labelstudio.ipynb`, `etl.ipynb` — data ingestion, Label Studio round-trip, and DB-facing glue.

## Architecture

The project is a pipeline that converts free-text TCE/RN decisions (`texto_acordao`) into structured audit data stored in MSSQL, with LLM extraction in between. Four building blocks in `tools/`:

**`tools/schema.py` — three layers of Pydantic models, intentionally distinct:**
- `NERMulta` / `NERObrigacao` / `NERRessarcimento` / `NERRecomendacao` + `NERDecisao` — raw span-level extractions (each has only a `descricao_*` string). This is what the first LLM pass produces.
- `Multa` / `Obrigacao` / `Ressarcimento` / `Recomendacao` + `Decisao` — fully structured records with values, dates, responsáveis, multa cominatória fields, etc. A second LLM pass enriches each NER span into one of these.
- `CitationChoice` / `ResponsibleChoice` — structured outputs for the helper LLMs that pick deadlines and resolve responsáveis.

**`tools/models.py` — SQLAlchemy ORMs mirroring the schema split:**
- `NERDecisaoORM` (+ `NERMultaORM`, `NERObrigacaoORM`, `NERRessarcimentoORM`, `NERRecomendacaoORM`) — persists raw NER output keyed by `(IdProcesso, IdComposicaoPauta, IdVotoPauta)`.
- `ObrigacaoORM`, `RecomendacaoORM`, `BeneficioORM` — final structured tables.
- `Processed*ORM` (`DecisaoProcessada`, `MultaProcessada`, `RessarcimentoProcessado`, `ObrigacaoProcessada`, `RecomendacaoProcessada`) — idempotency bridge tables linking `IdNer*` → final `Id*`. Always check these before inserting; the pipelines rely on them to resume safely.

**`tools/prompt.py` + `tools/fewshot.py` — prompt construction:**
- `FEW_SHOT_NER_PROMPT` system prompt + `TOOL_USE_EXAMPLES` few-shot pairs (hand-curated `(text, NERDecisao)` tuples in `fewshot.py`) power `generate_few_shot_ner_prompts()`.
- `FEW_SHOT_DOC_PROMPT` + `FEWSHOTS_DOC_TAGS` handle the document-tagging task (4 labels: MULTA / OBRIGACAO / RESSARCIMENTO / RECOMENDACAO).
- `prompt_engineering_techniques.py` (top level) holds alternative strategies — CoT, self-consistency, two-stage, dynamic few-shot — used by `ner_experiments.ipynb`.

**`tools/utils.py` — pipelines and DB glue:**
- `get_connection(db)` / `get_session(db)` — each call opens a fresh MSSQL engine bound to a specific database (`processo`, `BdDIP`, `BdSIAI`). The pipelines are cross-database: decision metadata from `processo`, NER/final tables in `BdDIP`, unit lookups in `BdSIAI`. Never hardcode a DB name — pass it in.
- `run_ner_pipeline_for_dataframe()` — stage 1 (NERDecisao). Calls `process_decision_row()` per row; `overwrite=False` skips rows that already have a `NERDecisaoORM` for the `(process, composition, vote)` triple.
- `run_obrigacao_pipeline()` / `run_recomendacao_pipeline()` — stage 2. Read `sql/obligations_nonprocessed.sql` / `sql/recommendations_nonprocessed.sql`, aggregate responsáveis per row, then for each NER span: resolve the unit (`find_unit` → fuzzy match against `sql/units.sql`), pick a deadline (`get_deadline_from_citations` uses `sql/citations_by_process_after.sql` + `CitationChoice` LLM), prompt the extractor with the enriched context, and insert into `Obrigacao`/`Recomendacao` + the matching `Processed*` row in a single transaction.
- SQL under `sql/` is read from disk and `.format(...)`-ed with query parameters — this is plain string interpolation, not parameter binding. Inputs come from trusted internal lists; keep it that way.

**`tools/dataset.py`** reads annotated JSON from `dataset/labeled_data/` (Label Studio exports). `translate_golden()` collapses legacy label variants (`MULTA_FIXA`, `MULTA_PERCENTUAL` → `MULTA`; `OBRIGACAO_MULTA` → `OBRIGACAO`) — apply it before comparing against model output.

## Experiments and outputs

- `dataset/experiments/` holds per-model JSON results, organized by technique (`few_shot_and_supervised/`, `function_calling_json_schema/`, `prompt_engineering/`). File naming: `models_results_decicontas_<model>_<technique>.json`.
- `dataset/results/` holds checkpoints and aggregated outputs consumed by the evaluation notebooks.
- Supervised models (BiLSTM-CRF, BERTimbau, Legal-BERTimbau) are stored as `.pkl` alongside their JSON metrics.

## Conventions worth knowing

- Decision identity across the system is the triple `(IdProcesso, IdComposicaoPauta, IdVotoPauta)` — always carry all three when joining or inserting.
- A row may have `id_ner_obrigacao` / `id_ner_recomendacao` under several casings (`IdNerObrigacao`, `idnerobrigacao`); `insert_obrigacao` already handles the variants via `row.get(...)` fallbacks — follow the same pattern rather than assuming a single key.
- `safe_int()` exists because pandas mixes `NaN`/`float`/`str` representations of ID columns; prefer it over `int(...)` when reading from dataframes.

## Rules for Claude Code in this repo

- **Show diffs before applying** changes that touch more than one file, and wait for confirmation.
- **Prefer small, atomic commits** in Conventional Commits format (feat, fix, refactor, docs, test, chore).
- **Use `git mv`** when relocating files — never recreate + delete.
- **Never commit** `.env`, files under `dataset/labeled_data/` with PII, or DB credentials. Check `git status` before committing.
- **Before deleting code**, grep the whole repo (including notebooks) for references.
- **Before editing a notebook**, prefer extracting the logic to `tools/` and calling it from the notebook, rather than editing long cells in place.
- **After refactoring a module used by a notebook**, re-execute the notebook (`jupyter nbconvert --execute --to notebook --inplace`) to confirm nothing broke. If a cell calls the LLM or the DB and would be expensive, skip it and tell me which.
- **Don't rewrite `.tex` content** without explicit confirmation — that's citable academic text.
- **When adding a new module**, default to placing it under `tools/` with a clear name. If the fit is ambiguous, ask.
- **Don't instantiate LLM clients or open DB connections at import time** in new code — use factory functions so tests can import without side effects. (Note: `tools/utils.py` currently does this; fixing it is on the backlog.)

## Language policy

- Code, comments, docstrings, identifiers, commit messages, branch names, PR titles, and issue descriptions: **English**.
- Prompts sent to LLMs and few-shot examples: **Portuguese** (the source documents — TCE/RN decisions — are in Portuguese, and the prompts are tuned for that).
- Dataset labels (`MULTA`, `OBRIGACAO`, `RESSARCIMENTO`, `RECOMENDACAO`): **Portuguese**, because they are domain terms from Brazilian audit law and map to database tables.
- The dissertation itself (under `docs/dissertacao/`): **Portuguese**.
- When in doubt: English for anything a non-Portuguese-speaking collaborator would need to read to use or modify the code.

## Testing

There is no test suite yet. When adding tests:
- Put them in `tests/`, mirroring the `tools/` layout.
- Target pure functions first: `translate_golden`, `safe_int`, Pydantic schema validation, prompt builders with deterministic input.
- Mock `AzureChatOpenAI` and SQLAlchemy sessions — never hit the real API or DB from tests.
- Run with `poetry run pytest`.

## Formatting and linting

- Formatter: `ruff format` (line length 100).
- Linter: `ruff check`.
- Run both before committing.

## Known technical debt

- `AzureChatOpenAI` is instantiated at module import time in `tools/utils.py` — blocks testability and forces env vars to be set even for offline work.
- SQL files under `sql/` are interpolated with `str.format()` rather than parameter binding. Inputs are currently trusted; revisit if that ever changes.
- `prompt_engineering_techniques.py` lives at the repo root but conceptually belongs inside `tools/prompts/` (or similar) alongside `prompt.py` and `fewshot.py`.
- Many notebooks live at the repo root; they should move to `notebooks/` once their relative paths are audited.
