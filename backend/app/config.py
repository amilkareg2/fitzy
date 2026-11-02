"""Application settings, read from the environment (and a local .env file)."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_AUTH_SECRET = "change-me"  # noqa: S105 - placeholder, rejected outside local/test


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://fitzy:fitzy@localhost:5432/fitzy"
    app_env: Literal["local", "test", "dev", "prod"] = "local"
    auth_secret: SecretStr = SecretStr(DEFAULT_AUTH_SECRET)
    owner_email: str = "you@example.com"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg3_driver(cls, value: str) -> str:
        """Accept plain postgres URLs (as given by most hosts) and pin the psycopg 3 driver."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value.removeprefix(prefix)
        return value

    @model_validator(mode="after")
    def _require_real_secret_when_deployed(self) -> "Settings":
        if self.app_env in ("dev", "prod") and (
            self.auth_secret.get_secret_value() == DEFAULT_AUTH_SECRET
            or len(self.auth_secret.get_secret_value()) < 32
        ):
            raise ValueError("AUTH_SECRET must be set to a random value of 32+ chars outside local")
        return self

    @property
    def is_deployed(self) -> bool:
        return self.app_env in ("dev", "prod")


@lru_cache
def get_settings() -> Settings:
    return Settings()
