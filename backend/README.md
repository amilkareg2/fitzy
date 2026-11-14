# Fitzy backend

FastAPI + SQLAlchemy 2 + Alembic on Postgres 16 (+ pgvector), managed with [uv](https://docs.astral.sh/uv/).

## Run locally

```bash
docker compose up -d db              # from the repo root: Postgres 16 + pgvector on :5432
cd backend
cp ../.env.example .env              # DATABASE_URL, APP_ENV, AUTH_SECRET, OWNER_EMAIL
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload # http://localhost:8000/health, /docs
```

Settings (`app/config.py`) come from env vars or `.env`. `postgres://` / `postgresql://` URLs are
rewritten to the psycopg 3 driver. Outside `local`/`test`, `AUTH_SECRET` must be 32+ random chars.

## Tests and lint

```bash
uv run ruff check . && uv run ruff format --check .
TEST_DATABASE_URL=postgresql+psycopg://fitzy:fitzy@localhost:5432/fitzy_test uv run pytest
```

- Unit tests (units, e1RM, health without DB) always run.
- DB tests run when `TEST_DATABASE_URL` (preferred) or `DATABASE_URL` is set, otherwise they are
  skipped. They migrate the database to head and run each test in a rolled-back transaction.
- `test_migrations.py` fails if the models and the migrations drift apart.

## Layout

| Path | What |
| --- | --- |
| `app/main.py` | App factory; `GET /health` (always 200, reports `db: ok/unavailable`) |
| `app/api/` | Thin routers. `GET /exercises` (needs `Authorization: Bearer $AUTH_SECRET`, a placeholder for M0 auth) |
| `app/schemas/` | Pydantic response/request models; routers never return ORM objects |
| `app/services/` | Business logic shared with the MCP server and coach: `units.py` (kg/lb), `e1rm.py` (Epley) |
| `app/models/` | SQLAlchemy models, one file per area |
| `migrations/` | Alembic. `0001` core schema, `0002` knowledge-base tables (M4, pgvector) |

## Schema notes

- UUID v4 primary keys everywhere (`gen_random_uuid()` server default plus a Python default).
- Weights are stored in kg (`numeric(9,4)`) with `entered_unit`, so 225 lb round-trips as 225 lb.
  Convert only through `app/services/units.py`.
- Closed value sets (`load_type`, `set_type`, `source`, ...) are `varchar` + named `CHECK`
  constraints rather than native enums: adding a value is a one-line migration.
- Reserved words: the user table is `app_user`, sets are `workout_set`, `muscle.group` is stored in
  column `muscle_group`, `kb_chunk.metadata` is the ORM attribute `meta`.
- `goal` is append-only: close a row with `valid_to` + `replaced_by_id`, then insert the new version.
- `personal_record` is derived and rebuildable from `workout_set`.
- `0002_kb_pgvector` runs `CREATE EXTENSION IF NOT EXISTS vector`. On a server without pgvector it
  is skipped with a warning when `APP_ENV` is `local`/`test`, and fails in `dev`/`prod`. To add the
  tables later: `uv run alembic downgrade 0001_initial_schema && uv run alembic upgrade head`.

## Docker

```bash
docker build -t fitzy-api backend/
docker run -p 8080:8080 -e DATABASE_URL=... -e AUTH_SECRET=... fitzy-api
```

Slim, non-root, listens on `$PORT` (Cloud Run). Migrations are not run on start-up; run
`alembic upgrade head` as a separate job/step before deploying.
