from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Local dev: load from .env automatically.
    # In production: you typically inject real env vars instead.
    model_config = SettingsConfigDict(env_prefix="", extra="ignore", env_file=".env", env_file_encoding="utf-8")

    # Env vars:
    # - LLM_PROVIDER: "openai" (default) or another real LLM backend (or "none" to disable real LLM calls)
    # - LLM_API_KEY (required for the real LLM)
    # - LLM_BASE_URL (optional, for OpenAI-compatible APIs)
    # - LLM_MODEL (optional)
    # - LLM_TIMEOUT_SECONDS (optional)
    # - SCALEDOWN_API_KEY (optional; enables prompt compression via ScaleDown)
    llm_provider: str = Field(default="openai", validation_alias="LLM_PROVIDER")
    llm_api_key: str = Field(default="", validation_alias="LLM_API_KEY")
    # Intentionally default these to empty so the API can clearly detect
    # misconfiguration and return a helpful 400 until the user sets env vars.
    llm_base_url: str = Field(default="", validation_alias="LLM_BASE_URL")
    llm_model: str = Field(default="", validation_alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(default=30.0, validation_alias="LLM_TIMEOUT_SECONDS")
    scaledown_api_key: str = Field(default="", validation_alias="SCALEDOWN_API_KEY")

    def model_post_init(self, __context):  # type: ignore[override]
        # Back-compat guard: older configs used LLM_PROVIDER=scaledown, but ScaleDown is not an LLM.
        # Treat it as a misconfiguration and fall back to the real LLM provider path.
        if (self.llm_provider or "").lower().strip() == "scaledown":
            self.llm_provider = "openai"


def get_settings() -> Settings:
    """Load settings from environment.

    Keep this as the single canonical constructor for Settings(). FastAPI
    dependencies and tests can override/monkeypatch this function.
    """
    return Settings()
