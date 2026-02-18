"""Unit tests for language-specific prompt tuning.

We validate that the agent embeds language-specific guidance in the prompt payload.
These tests don't make any LLM/network calls.
"""

from __future__ import annotations

import json

from app.ai_agent import CodeReviewAgent
from app.llm_client import LLMClient


class _DummyLLM(LLMClient):
    async def review(self, *, compressed_context: str, static_analysis: dict, review_prompt: str | None = None):  # type: ignore[override]
        return []


def test_prompt_contains_typescript_tuning():
    agent = CodeReviewAgent(_DummyLLM(api_key="", base_url="", model="", timeout_seconds=1))
    prompt = agent._build_review_prompt(
        "CTX", {"flake8": {"skipped": True}, "bandit": {"skipped": True}}, language="typescript", strict=False
    )
    payload = json.loads(prompt)
    assert payload["language"] == "typescript"
    assert "TypeScript" in payload["instructions"]
    assert "type-safety" in payload["instructions"].lower()


def test_prompt_unknown_language_falls_back_to_general():
    agent = CodeReviewAgent(_DummyLLM(api_key="", base_url="", model="", timeout_seconds=1))
    prompt = agent._build_review_prompt(
        "CTX", {"flake8": {"skipped": True}, "bandit": {"skipped": True}}, language="kotlin", strict=False
    )
    payload = json.loads(prompt)
    assert payload["language"] == "kotlin"
    assert "General:" in payload["instructions"]
