"""Runtime settings, loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root is two levels up from this file (backend/app/config.py → repo/).
# Look for .env there first, then in CWD as a fallback (so Docker, where the
# .env is injected via `env_file:`, still works without surprise).
_REPO_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_REPO_ROOT_ENV), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- core
    app_env: Literal["dev", "prod", "test"] = "dev"
    database_url: str = "sqlite+aiosqlite:///./data/agentx.db"
    cors_origins: list[str] = ["http://localhost:3000"]

    # --- LLM (OpenAI-compatible — works with OpenAI, Groq, Ollama via base_url)
    openai_api_key: str = ""
    openai_base_url: str | None = None
    default_model: str = "gpt-4o-mini"
    # Set true for endpoints that don't support OpenAI tool-calling
    # (e.g. a default vLLM deployment without --enable-auto-tool-choice).
    disable_tool_calling: bool = False

    # --- channels
    enabled_channels: list[str] = Field(default_factory=lambda: ["telegram"])
    telegram_bot_token: str = ""

    # --- guardrails defaults
    default_max_steps: int = 20
    default_max_cost_usd: float = 1.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
