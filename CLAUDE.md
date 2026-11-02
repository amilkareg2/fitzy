# Fitzy

Single-user strength-training tracker (FitNotes replacement) with exact analytics, an MCP server and an AI coach. It is also an AI-engineer portfolio project: the way it is built (specs, tests, evals, CI) is part of the deliverable.

Product spec and data model: https://claude.ai/artifact/LGsSwpJnHL3qv3uZHtrbKm
Backlog: Todoist project "FitNotes AI", one section per milestone (M0–M6).

## Layout

| Path | What |
| --- | --- |
| `backend/` | FastAPI + SQLAlchemy 2 + Alembic, Python, managed with `uv` |
| `frontend/` | React + Vite + TypeScript PWA, managed with `npm` |
| `infra/bootstrap/` | One-time GCP setup (state bucket, deployer SA, Workload Identity Federation) |
| `infra/main/` | Cloud Run, Secret Manager; database is Neon serverless Postgres (created by hand) |
| `data/` | Reference data committed to the repo (muscle taxonomy, exercise mapping). Never raw personal exports |
| `.github/workflows/` | CI (lint, tests, secret scan, terraform validate) and deploy |

## Commands

```bash
docker compose up -d db                       # local Postgres + pgvector
cd backend && uv sync && uv run alembic upgrade head && uv run pytest
cd backend && uv run uvicorn app.main:app --reload   # API on :8000
cd frontend && npm ci && npm run dev          # PWA on :5173, /api proxied to :8000
cd frontend && npm run lint && npm run typecheck && npm test -- --run
```

## Rules

- **Secrets.** The repo is public. Never commit `.env`, keys, tokens, or service-account JSON. Config comes from env vars locally and Secret Manager in GCP. CI reaches GCP through Workload Identity Federation only. gitleaks runs in pre-commit and CI.
- **Personal data.** Raw FitNotes exports stay out of git (`data/raw/` is ignored). Tests use synthetic data.
- **Units.** Store weights in kg (`weight_kg`) and keep `entered_unit` so values round-trip exactly. Convert only in `app/services/units.py`.
- **Analytics are code, not AI.** e1RM, volume, PRs and balance are deterministic Python/SQL with tests. The coach (M4) calls them as tools; it never computes numbers itself.
- **Goals are append-only.** Changing a goal closes the row (`valid_to`) and inserts a new one.
- **Derived tables are rebuildable.** `personal_record` can always be recomputed from sets.
- **Every change goes through a PR** with tests. Schema changes need an Alembic migration. AI behaviour changes need eval cases (from M5).
- **Small PRs**, one feature each, with a short "why" in the description.

## Conventions

- Python: ruff (lint + format), type hints everywhere, SQLAlchemy 2.0 `Mapped[]` style, Pydantic v2 schemas separate from ORM models.
- TypeScript: strict mode, no `any`, TanStack Query for server state, CSS variables in `tokens.css`, no UI library.
- Commits: imperative mood, explain why in the body.
