from __future__ import annotations

from typing import Any

from fastapi import Depends

from app.ai_agent import CodeReviewAgent
from app.analysis.pipeline import ReviewPipeline
from app.llm_client import LLMClient
from app.settings import Settings, get_settings


def get_settings_dep() -> Settings:
    """FastAPI dependency for settings.

    Delegates to app.settings.get_settings (canonical constructor).
    """
    return get_settings()


class _OfflineLLMClient(LLMClient):
    async def review(
        self,
        *,
        compressed_context: str,
        static_analysis: dict[str, Any],
        review_prompt: str | None = None,
    ) -> list[Any]:
        return []


# NOTE: Do not cache across process lifetime. Tests toggle env vars and monkeypatch
# LLMClient methods; caching breaks determinism.


def get_llm_client() -> LLMClient:
    s = get_settings_dep()

    # ScaleDown is NOT an LLM. We always return the real LLM client here.
    # If you want to run locally without any LLM calls, set LLM_PROVIDER=none.
    if (s.llm_provider or "").lower().strip() == "none":
        return _OfflineLLMClient(api_key="", base_url="", model="", timeout_seconds=s.llm_timeout_seconds)

    return LLMClient(
        api_key=s.llm_api_key,
        base_url=s.llm_base_url,
        model=s.llm_model,
        timeout_seconds=s.llm_timeout_seconds,
    )


def get_agent() -> CodeReviewAgent:
    # Settings are used inside get_llm_client(); no need to bind them here.
    return CodeReviewAgent(get_llm_client())


def get_pipeline(settings: Settings = Depends(get_settings_dep)) -> ReviewPipeline:
    """Construct the modular review pipeline.

    In offline mode, the pipeline runs without an LLM stage.
    """
    provider = (settings.llm_provider or "openai").lower().strip()
    llm = None if provider == "none" else get_llm_client()
    return ReviewPipeline(llm_client=llm)
