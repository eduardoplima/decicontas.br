# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

Monorepo with three top-level code areas, each with its own `CLAUDE.md`:

- `tools/` — research library (NER pipelines, Pydantic schemas, prompts, fewshot, SQLAlchemy ORMs). Imported by `backend/` and by the notebooks. See `tools/CLAUDE.md`.
- `backend/` — FastAPI service hosting the review API, authentication, and ETL orchestration. See `backend/CLAUDE.md`.
- `frontend/` — Next.js 15 App Router app for reviewers. See `frontend/CLAUDE.md`.
- `notebooks/`, `dataset/`, `sql/` — unchanged from the research setup; see `tools/CLAUDE.md`.

Dependency rule: `backend/` and `notebooks/` may import from `tools/`. `tools/` never imports from `backend/`. `frontend/` only talks to `backend/` over HTTP.

Python layout: uv workspace, members `tools` and `backend`, lock committed at `uv.lock`. Backend declares `tools[llm]` as a workspace dependency; notebooks need `tools[experiments]` for the full supervised/evaluation stack.

## Environment

Runtime config via `.env` at repo root (shared between `tools/` and `backend/`). Existing variables (see `tools/CLAUDE.md`) plus:

- `JWT_SECRET_KEY`, `JWT_ALGORITHM` (default `HS256`), `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default `60`), `JWT_REFRESH_TOKEN_EXPIRE_DAYS` (default `7`).
- `CORS_ALLOWED_ORIGINS` — comma-separated, must include the frontend URL.
- `REDIS_URL` — required when the ARQ worker is enabled.

Frontend config in `frontend/.env.local`:
- `NEXT_PUBLIC_API_URL` — backend base URL.

`.env` and `.env.local` are gitignored — never commit them.

## Running the code

- Install: `uv sync` at the repo root. Add `--extra experiments` when working on notebooks.
- Research notebooks: see `tools/CLAUDE.md`.
- Backend dev server: `cd backend && uv run uvicorn app.main:app --reload --port 8000`.
- Background worker: `cd backend && uv run arq app.worker.WorkerSettings`.
- Frontend dev server: `cd frontend && pnpm dev`.
- Alembic migrations: `cd backend && uv run alembic upgrade head`.

## Rules for Claude Code — repo-wide

- **Show diffs before applying** changes that touch more than one top-level area (`tools/` + `backend/`, `backend/` + `frontend/`, etc.), and wait for confirmation.
- **Conventional Commits with scope**: `feat(backend): ...`, `fix(frontend): ...`, `chore(tools): ...`, `docs: ...`. Small atomic commits.
- **`git mv`** when relocating files — never recreate + delete.
- **Never commit** `.env`, `.env.local`, anything under `dataset/labeled_data/`, or DB credentials. Check `git status` before committing.
- **Don't rewrite `.tex` content** without explicit confirmation — that's citable academic text.
- **Before deleting code**, grep the whole repo (including notebooks, backend, frontend) for references.
- **When the fit is ambiguous** (module could go in `tools/` or `backend/app/`), ask. Default: if it has no web framework imports and would be useful from a notebook, it goes in `tools/`.

## Language policy

- Code, comments, docstrings, identifiers, commit messages, branch names, PR titles, issue descriptions: **English**.
- Prompts sent to LLMs, few-shot examples, and dataset labels (`MULTA`, `OBRIGACAO`, `RESSARCIMENTO`, `RECOMENDACAO`): **Portuguese** — source documents are Portuguese and prompts are tuned for that.
- Dissertation (`.tex` under `docs/dissertacao/`): **Portuguese**.
- Frontend UI strings shown to reviewers (labels, buttons, toasts, error messages): **Portuguese**. Component names, props, zod schema keys, route segments: **English**.
- OpenAPI descriptions and error `detail` strings returned by the API: **English** (developer-facing). Human-readable validation messages bubbled up to reviewers: **Portuguese**, localized on the frontend from error codes.
- When in doubt: English for anything a non-Portuguese-speaking collaborator would need to read to use or modify the code.

## Formatting and linting

- Python: `ruff format` (line length 100) + `ruff check`. Run both in `tools/` and `backend/` before committing.
- TypeScript: `pnpm lint` + `pnpm format` (Prettier). Run in `frontend/` before committing.