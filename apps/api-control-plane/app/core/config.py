from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = Field(default="gooberberg-api-control-plane")
    environment: str = Field(default="development")
    app_version: str = Field(default="0.1.0")
    api_prefix: str = Field(default="/api/v1")

    postgres_dsn: str | None = Field(default=None)
    redis_dsn: str | None = Field(default=None)

    heartbeat_interval_seconds: float = Field(default=15.0)
    ws_replay_window: int = Field(default=512, ge=32, le=20000)
    ws_replay_enabled: bool = Field(default=True)
    worker_heartbeat_stale_after_seconds: float = Field(default=60.0)
    api_auth_token: str | None = Field(default=None)
    api_auth_scope: str = Field(default="control-plane:full")
    artifact_intermediate_retention_days: int = Field(default=14, ge=1, le=3650)

    model_config = SettingsConfigDict(env_prefix="GB_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
