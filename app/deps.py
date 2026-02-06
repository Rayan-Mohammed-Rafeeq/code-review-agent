from __future__ import annotations

from functools import lru_cache

from app.ai_agent import CodeReviewAgent
from app.llm_client import LLMClient
from app.settings import Settings, get_settings


def get_settings_dep() -> Settings:
    """FastAPI dependency for settings.

    Delegates to app.settings.get_settings (canonical constructor).
    """
    return get_settings()


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    s: Settings = get_settings_dep()

    # ScaleDown is NOT an LLM. We always return the real LLM client here.
    # If you want to run locally without any LLM calls, set LLM_PROVIDER=none.
    if (s.llm_provider or "").lower().strip() == "none":
        return LLMClient(api_key="", base_url="", model="", timeout_seconds=s.llm_timeout_seconds)

    return LLMClient(
        api_key=s.llm_api_key,
        base_url=s.llm_base_url,
        model=s.llm_model,
        timeout_seconds=s.llm_timeout_seconds,
    )


def get_agent() -> CodeReviewAgent:
    s: Settings = get_settings_dep()
    return CodeReviewAgent(get_llm_client())
