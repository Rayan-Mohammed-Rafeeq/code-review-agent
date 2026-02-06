from __future__ import annotations

import json
import logging
from typing import Any

from app.compressor import compress_python_code
from app.llm_client import LLMClient
from app.models import Issue
from app.ranker import rank_issues
from app.scaledown_compression import compress_with_scaledown
from app.static_checks import run_static_analysis

logger = logging.getLogger("code_review_agent")


class CodeReviewAgent:
    def __init__(self, llm: LLMClient):
        self._llm = llm

    async def review(
        self,
        *,
        code: str,
        filename: str,
        language: str = "python",
        strict: bool = False,
    ) -> tuple[str, dict[str, Any], list[Issue]]:
        # Step 1: Compress the code
        compressed = compress_python_code(code).text

        # Step 2: Run static analysis
        static_result = run_static_analysis(code=code, filename=filename)
        static_dict: dict[str, Any] = {"flake8": static_result.flake8, "bandit": static_result.bandit}

        # Step 3: Build the full review prompt
        review_prompt = self._build_review_prompt(compressed, static_dict, language=language, strict=strict)

        # Step 4: Optionally compress the prompt with ScaleDown (compression only)
        compressed_prompt, used_scaledown = compress_with_scaledown(review_prompt)
        logger.debug("ScaleDown used: %s", used_scaledown)

        # Step 5: Send the compressed prompt to the REAL LLM
        try:
            issues = await self._llm.review(
                compressed_context=compressed,
                static_analysis=static_dict,
                review_prompt=compressed_prompt,
            )
        except Exception as e:
            # Fail gracefully: surface a controlled error to the API layer.
            raise RuntimeError(f"LLM review failed: {type(e).__name__}: {e}") from e

        # Step 6: Rank and return issues
        issues = rank_issues(issues)
        return compressed, static_dict, issues

    def _build_review_prompt(
        self,
        compressed_context: str,
        static_analysis: dict[str, Any],
        *,
        language: str,
        strict: bool,
    ) -> str:
        """Build the full review prompt from context and analysis.

        This prompt may be optionally compressed by ScaleDown before being sent to the LLM.
        """
        instructions = (
            "Act as a strict project-level Code Review Agent. Review code as production code. "
            "While reviewing, check for: unused variables/dead code; naming clarity; missing/weak documentation; "
            "magic numbers/hardcoded values; readability/maintainability; basic logical correctness; "
            "code style and language-specific best practices. "
            "Do not approve code just because it runs or has no syntax errors. "
            "Return issues as structured JSON matching the schema (severity/category/description/suggestion/location). "
            "If there are no issues, return an empty list."
            if strict
            else (
                "Identify issues. Prefer high-signal items. "
                "If static analysis already reports an issue, you may reference it and expand with context."
            )
        )

        payload = {
            "language": (language or "python").strip().lower(),
            "compressed_context": compressed_context,
            "static_analysis": static_analysis,
            "instructions": instructions,
        }
        return json.dumps(payload, indent=2)
