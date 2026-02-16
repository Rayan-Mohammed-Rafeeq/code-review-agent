from __future__ import annotations

import pytest

from app.analysis.models import FileReviewRequest, ProjectReviewRequest
from app.analysis.pipeline import ReviewPipeline


class DummyLLM:
    async def raw_review_json(self, *, review_payload: str) -> str:  # noqa: ARG002
        return '{"issues": [{"line": 1, "category": "style", "severity": "info", "description": "x", "suggestion": "y"}]}'


@pytest.mark.asyncio
async def test_rules_detect_dangerous_and_mutable_default():
    code = """
import os

def f(x, acc=[]):
    print('debug')
    os.system('ls')
    return eval(x)
"""
    p = ReviewPipeline(llm_client=None)
    r = await p.review_file(filename="a.py", code=code, strict=False)

    descs = "\n".join(i.description for i in r.issues)
    assert "Mutable default" in descs
    assert "os.system" in descs
    assert "eval" in descs


@pytest.mark.asyncio
async def test_scoring_in_range_and_strict_penalizes_more():
    code = """

def f(x, acc=[]):
    return x
"""
    p = ReviewPipeline(llm_client=None)
    r1 = await p.review_file(filename="a.py", code=code, strict=False)
    r2 = await p.review_file(filename="a.py", code=code, strict=True)

    assert 0 <= r1.score.score <= 100
    assert 0 <= r2.score.score <= 100
    assert r2.score.score <= r1.score.score


@pytest.mark.asyncio
async def test_project_review_aggregates_and_dedupes_and_llm_json_is_validated():
    p = ReviewPipeline(llm_client=DummyLLM())
    req = ProjectReviewRequest(
        files=[
            FileReviewRequest(filename="a.py", code="print('x')\n"),
            FileReviewRequest(filename="b.py", code="print('x')\n"),
        ],
        strict=False,
        enabled_rules={"R100-debug-print": True},
    )
    out = await p.review_project(req)
    assert set(out.files.keys()) == {"a.py", "b.py"}
    assert out.overall.score.score <= 100
    # should include the dummy LLM issue
    assert any(i.source == "llm" for i in out.overall.issues)


@pytest.mark.asyncio
async def test_logical_checks_flags_is_literal_and_unreachable():
    code = """

def f(x):
    if x is 5:
        return 1
        x = 3
    return 0
"""
    p = ReviewPipeline(llm_client=None)
    r = await p.review_file(filename="a.py", code=code, strict=True)

    descs = "\n".join(i.description for i in r.issues)
    assert "Using 'is' to compare to a literal" in descs
    assert "Unreachable code" in descs


@pytest.mark.asyncio
async def test_logical_checks_flags_inverted_is_even_predicate():
    code = """

def is_even(n):
    if n % 2 == 1:
        return True
    else:
        return False
"""
    p = ReviewPipeline(llm_client=None)
    r = await p.review_file(filename="a.py", code=code, strict=False)

    assert any(i.code == "L800-inverted-predicate" for i in r.issues)

