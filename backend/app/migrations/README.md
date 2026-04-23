# Alembic migrations

Authoritative rules are in [`backend/CLAUDE.md`](../../CLAUDE.md) under "Alembic baseline". This file is a short operational cheat sheet.

## Baseline

The existing production schema in `DB_DECISOES` is the baseline. The first revision (`b2f4c89d0e1a_baseline.py`) is intentionally empty — applying it performs no DDL.

To mark a live database as being at the baseline without executing any DDL:

```bash
cd backend
uv run alembic stamp head
```

Run this exactly once per database, and only when that database's schema already matches the ORMs in `tools/models.py`.

## Authoring new migrations

1. **Prefer hand-written revisions** when the change touches legacy tables. Alembic does not know about indexes, constraints, or defaults created outside its history and will happily try to drop them.
2. **`alembic revision --autogenerate` is a diff aid, not a source of truth.** Read every generated script end to end before committing. Delete any operation that would touch an existing production table unless that edit is the explicit purpose of the migration.
3. Autogenerate requires a live connection to `DB_DECISOES` — it reflects the current schema and diffs against `tools.models.Base.metadata`. Point `env.py` at a non-production instance while iterating.

## First real migrations (not in this PR)

Per `backend/CLAUDE.md`, the next revisions should create:

- `ObrigacaoStaging`, `RecomendacaoStaging`
- `Users`, and `RefreshTokens` if the refresh-token rotation strategy persists tokens
