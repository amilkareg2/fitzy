# syntax=docker/dockerfile:1
# Fitzy API image for Cloud Run. Build from backend/: docker build -t fitzy-api .

FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
# Dependencies first for layer caching. Uses uv.lock when present (--locked keeps it honest).
COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -f uv.lock ]; then uv sync --locked --no-dev; else uv sync --no-dev; fi
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

FROM python:3.13-slim
RUN groupadd --system --gid 10001 fitzy \
    && useradd --system --uid 10001 --gid fitzy --no-create-home fitzy
WORKDIR /app
COPY --from=build --chown=fitzy:fitzy /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080
USER fitzy
EXPOSE 8080
# Cloud Run injects $PORT. Migrations run separately (e.g. a Cloud Run job: `alembic upgrade head`).
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
