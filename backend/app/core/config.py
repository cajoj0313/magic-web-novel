"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global app settings with environment variable overrides."""

    app_secret_key: str = Field(
        default="",
        description="AES-GCM key for encrypting API keys. Empty = plaintext mode (dev only).",
    )
    log_level: str = Field(default="INFO")
    host: str = "0.0.0.0"
    port: int = 8000
    # Plugin scripts directory
    claude_plugin_root: str = Field(
        default="",
        description="Path to CLAUDE_PLUGIN_ROOT/scripts/ for internalized Python modules.",
    )
    # Application data directory for project_registry.json, llm_configs.json
    app_data_dir: str = str(Path.home() / ".webnovel-app")

    model_config = {"env_prefix": "WEBNOVEL_", "extra": "ignore"}


settings = Settings()


def ensure_app_data_dir() -> Path:
    """Ensure the application data directory exists and return it."""
    data_dir = Path(settings.app_data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir
