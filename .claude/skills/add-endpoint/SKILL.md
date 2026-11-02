---
name: add-endpoint
description: Use when adding or changing a REST endpoint in backend/app/api/.
---

1. Put request/response Pydantic schemas in `backend/app/schemas/`, never return ORM objects directly.
2. Keep the router thin: business logic goes in `backend/app/services/`, so the MCP server (M3) and the coach (M4) can call the same functions.
3. Every endpoint except `/health` requires the authenticated owner.
4. Weights in and out carry their unit; convert through `app/services/units.py`.
5. Write tests first in `backend/tests/api/`: happy path, validation error, and auth failure.
6. Update the frontend API client types in `frontend/src/api/` in the same PR if the frontend uses the endpoint.
7. Run `uv run ruff check . && uv run ruff format --check . && uv run pytest` before opening the PR.
