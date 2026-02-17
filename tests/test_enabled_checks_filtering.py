from __future__ import annotations

import pytest

from app.analysis.models import Category
from app.analysis.pipeline import ReviewPipeline


class _NoLLM:
    async def raw_review_json(self, *, review_payload: str) -> str:  # noqa: ARG002
        return '{"issues": []}'


@pytest.mark.asyncio
async def test_enabled_checks_filters_style_and_security_and_performance():
    pipeline = ReviewPipeline(llm_client=_NoLLM())

    # This code intentionally triggers style-ish (deep nesting) in custom rules.
    code = """

def f(x):
    if x:
        if x > 0:
            if x > 1:
                if x > 2:
                    return 1
    return 0
""".lstrip()

    # Disable style/performance/security; keep default always-on categories.
    r = await pipeline.review_file(
        filename="x.py",
        code=code,
        strict=False,
        language="python",
        enabled_checks={"security": False, "style": False, "performance": False},
    )

    assert all(i.category not in {Category.security, Category.style, Category.performance} for i in r.issues)


@pytest.mark.asyncio
async def test_enabled_checks_keeps_style_when_enabled():
    pipeline = ReviewPipeline(llm_client=_NoLLM())

    # Unused import should reliably trigger a flake8 style-like finding.
    code = """
import os

def f():
    return 1
""".lstrip()

    r = await pipeline.review_file(
        filename="x.py",
        code=code,
        strict=False,
        language="python",
        enabled_checks={"style": True},
    )

    assert any(i.category == Category.style for i in r.issues)
