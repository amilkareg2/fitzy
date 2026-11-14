---
name: add-migration
description: Use when changing the database schema in backend/ (new table, column, index or constraint).
---

1. Edit or add the SQLAlchemy model in `backend/app/models/`. Use `Mapped[]` types, explicit `nullable`, and check constraints for invariants (e.g. `reps >= 0`).
2. Generate the migration: `cd backend && uv run alembic revision --autogenerate -m "<what and why>"`.
3. Read the generated file. Autogenerate misses enum type changes, server defaults and extension-dependent columns; fix by hand.
4. Add data migrations in the same revision only when they are small; otherwise make a separate revision.
5. Check both directions locally: `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`.
6. Add or update a test in `backend/tests/` that exercises the new schema.
7. If the change affects the data model in the spec doc, say so in the PR description so the doc gets updated.
