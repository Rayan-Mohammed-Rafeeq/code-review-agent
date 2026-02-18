from __future__ import annotations

import pytest

from app.analysis.pipeline import ReviewPipeline


class _FailingLLM:
    async def raw_review_json(self, *, review_payload: str) -> str:  # noqa: ARG002
        raise RuntimeError("LLM request failed: HTTP 429")


@pytest.mark.asyncio
async def test_v2_pipeline_records_llm_429_as_diagnostic_not_issue():
    pipeline = ReviewPipeline(llm_client=_FailingLLM())

    r = await pipeline.review_file(filename="x.py", code="print('hi')\n", strict=False, language="python")

    # Infra failure should not be injected into issues.
    assert all("LLM request failed" not in i.description for i in r.issues)

    # But it should be visible as a diagnostic.
    assert r.diagnostics
    assert any(d.code.value == "llm_rate_limited" for d in r.diagnostics)

    # Score should still be computed from real issues only.
    assert 0 <= r.score.score <= 100
