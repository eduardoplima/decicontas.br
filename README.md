# DeciContas.br

Structured extraction of fines, obligations, reimbursements, and recommendations from decisions of the Rio Grande do Norte State Court of Accounts (TCE/RN). Free-text `texto_acordao` goes in, structured audit records land in MSSQL, and a reviewer web app lets auditors approve, edit, or reject each extraction.

The repository is a uv + pnpm monorepo with three top-level areas.

## Areas

### `tools/` — research library

Framework-agnostic Python package: NER pipelines, Pydantic schemas, prompts, few-shot examples, SQLAlchemy ORMs, and ETL staging logic. Imported by `backend/` and by notebooks. Exposes `[llm]` (LangChain / OpenAI) and `[experiments]` (torch, transformers, spacy, Jupyter, …) optional dependency sets. See [`tools/CLAUDE.md`](./tools/CLAUDE.md).

### `backend/` — FastAPI review service

FastAPI app hosting the review API, authentication, Alembic migrations, and the ARQ worker that runs stage-2 extraction. Depends on `tools[llm]` through the uv workspace. See [`backend/CLAUDE.md`](./backend/CLAUDE.md).

### `frontend/` — Next.js 15 reviewer app

Next.js 15 App Router app with TypeScript, Tailwind, and ESLint. Reviewers approve, edit, or reject LLM-extracted obrigações and recomendações. Talks only to the backend over HTTP. See [`frontend/CLAUDE.md`](./frontend/CLAUDE.md).

## Getting started

Requires Python `>=3.12,<3.13`, [uv](https://docs.astral.sh/uv/), Node.js 20+, and [pnpm](https://pnpm.io/).

```bash
# Python (backend + tools via the uv workspace)
uv sync

# Notebooks — add the experiments extra for torch/transformers/spacy/etc.
uv sync --package tools --extra experiments

# Frontend
cd frontend && pnpm install
```

Runtime config lives in `.env` at the repo root (Python) and `frontend/.env.local` (frontend). Neither file is committed — see the per-area `CLAUDE.md` files for required variables and `frontend/.env.local.example` for the frontend template.

Common commands:

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8000   # API
cd backend && uv run arq app.worker.WorkerSettings                # worker
cd backend && uv run alembic upgrade head                         # migrations
cd frontend && pnpm dev                                           # web app
```

## Legal Context

This project is aligned with TCE/RN rules governing:

- execution of fines and reimbursements ([Resolução 013/2015](./docs/Resolução_0132015_Dispõe_sobre_a_execução_das_decisões_TCERN__multaressarcimento.pdf))

It can support future auditing and compliance workflows by generating structured datasets from free-form decisions.

## Credits

- Inspired by LexCare.BR and its cross-domain NER approach
- Developed for the DeciContas.br research project
- Data sources: Tribunal de Contas do Estado do Rio Grande do Norte
- Developed in Python with langchain, pydantic, and Azure OpenAI
