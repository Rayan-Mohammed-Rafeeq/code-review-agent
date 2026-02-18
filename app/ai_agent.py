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
        lang = (language or "python").strip().lower()

        # Step 1: Compress the code (python gets a specialized compressor; others use raw code).
        if lang == "python":
            compressed = compress_python_code(code).text
        else:
            compressed = code

        # Step 2: Run static analysis (flake8/bandit are python-only).
        if lang == "python" and (filename or "").lower().endswith(".py"):
            static_result = run_static_analysis(code=code, filename=filename)
            static_dict: dict[str, Any] = {"flake8": static_result.flake8, "bandit": static_result.bandit}
        else:
            static_dict = {"flake8": {"skipped": True}, "bandit": {"skipped": True}}

        # Step 3: Build the full review prompt
        review_prompt = self._build_review_prompt(compressed, static_dict, language=lang, strict=strict)

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
        lang = (language or "python").strip().lower()

        language_tuning: dict[str, str] = {
            "python": "Python: focus on typing, exceptions, context managers, async correctness, and idiomatic APIs (PEP8/PEP257 when relevant).",
            "javascript": "JavaScript: focus on async/await + Promise correctness, runtime edge cases, and browser/node compatibility.",
            "typescript": "TypeScript: focus on type-safety, correct generics, narrowing, and avoiding any/unsafe casts.",
            "java": "Java: focus on null-safety, resource handling (try-with-resources), collections/streams pitfalls, and concurrency correctness.",
            "csharp": "C#: focus on nullability, async/await, IDisposable usage, LINQ performance pitfalls, and common .NET best practices.",
            "go": "Go: focus on error handling, context usage, goroutine leaks, races, and API design conventions.",
            "rust": "Rust: focus on ownership/borrowing correctness, lifetimes when applicable, error handling (Result), and avoiding unnecessary clones.",
        }

        lang_hint = language_tuning.get(lang) or (
            "General: focus on correctness, security, performance, maintainability, and language best practices."
        )

        instructions = (
            "Act as a strict project-level CRA. Review code as production code. "
            "While reviewing, check for: unused variables/dead code; naming clarity; missing/weak documentation; "
            "magic numbers/hardcoded values; readability/maintainability; basic logical correctness; "
            "code style and language-specific best practices. "
            + lang_hint
            + " Do not approve code just because it runs or has no syntax errors. "
            "Return issues as structured JSON matching the schema (severity/category/description/suggestion/location). "
            "If there are no issues, return an empty list."
            if strict
            else (
                "Identify issues. Prefer high-signal items. "
                "If static analysis already reports an issue, you may reference it and expand with context. "
                + lang_hint
            )
        )

        payload = {
            "language": lang,
            "compressed_context": compressed_context,
            "static_analysis": static_analysis,
            "instructions": instructions,
        }
        return json.dumps(payload, indent=2)
