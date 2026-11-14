from fastapi import FastAPI

from app.api import exercises, health
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Fitzy API",
        version="0.1.0",
        # Interactive docs only outside production.
        docs_url=None if settings.app_env == "prod" else "/docs",
        redoc_url=None,
        openapi_url=None if settings.app_env == "prod" else "/openapi.json",
    )
    app.include_router(health.router)
    app.include_router(exercises.router)
    return app


app = create_app()
