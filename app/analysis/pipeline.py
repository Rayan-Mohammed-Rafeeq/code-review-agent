from __future__ import annotations

import json
from typing import Any

from app.analysis.aggregate import dedupe_issues
from app.analysis.llm_structured import build_llm_instructions, llm_response_to_issues, parse_llm_json
from app.analysis.logical_checks import run_logical_checks
from app.analysis.models import (
    Category,
    DiagnosticCode,
    ProjectReviewRequest,
    ProjectReviewResult,
    ReviewDiagnostic,
    ReviewResult,
)
from app.analysis.preprocess import preprocess_code
from app.analysis.static_tool_adapters import issues_from_bandit, issues_from_flake8
from app.rules.engine import run_custom_rules
from app.scoring.scorer import score_issues
from app.static_checks import run_static_analysis


class ReviewPipeline:
    def __init__(self, *, llm_client: Any | None):
        self._llm = llm_client

    async def review_file(
        self,
        *,
        filename: str,
        code: str,
        strict: bool,
        enabled_rules: dict[str, bool] | None = None,
        language: str = "python",
        enabled_checks: dict[str, bool] | None = None,
    ) -> ReviewResult:
        code = preprocess_code(code=code)
        lang = (language or "python").strip().lower()

        static_dict: dict[str, Any]
        if lang == "python" and (filename or "").lower().endswith(".py"):
            static = run_static_analysis(code=code, filename=filename)
            static_dict = {"flake8": static.flake8, "bandit": static.bandit}
        else:
            static_dict = {"flake8": {"skipped": True}, "bandit": {"skipped": True}}

        issues = []
        diagnostics: list[ReviewDiagnostic] = []

        if lang == "python":
            issues.extend(run_logical_checks(code=code, filename=filename, strict=strict))
            issues.extend(run_custom_rules(code=code, filename=filename, strict=strict, enabled_rules=enabled_rules))
            issues.extend(issues_from_flake8(flake8=static_dict.get("flake8") or {}, filename=filename))
            issues.extend(issues_from_bandit(bandit=static_dict.get("bandit") or {}, filename=filename))

        if self._llm is None:
            diagnostics.append(
                ReviewDiagnostic(
                    code=DiagnosticCode.llm_disabled,
                    message="LLM review is disabled (no LLM client configured)",
                    severity="info",
                    retryable=False,
                )
            )
        else:
            prompt_payload = {
                "filename": filename,
                "language": lang,
                "code": code,
                "instructions": build_llm_instructions(strict=strict),
            }
            try:
                raw = await self._llm.raw_review_json(review_payload=json.dumps(prompt_payload))
                resp = parse_llm_json(text=raw)
                issues.extend(llm_response_to_issues(resp=resp, filename=filename))
            except Exception as e:
                msg = str(e) or type(e).__name__
                lower = msg.lower()
                code_val = DiagnosticCode.llm_network_error
                status_code: int | None = None
                retryable: bool | None = None

                if "429" in lower or "rate" in lower and "limit" in lower:
                    code_val = DiagnosticCode.llm_rate_limited
                    retryable = True
                    status_code = 429
                elif "timeout" in lower:
                    code_val = DiagnosticCode.llm_timeout
                    retryable = True
                elif "http" in lower and any(s in lower for s in ["400", "401", "403", "404", "408", "429", "500", "502", "503", "504"]):
                    code_val = DiagnosticCode.llm_http_error
                    retryable = True if any(s in lower for s in ["408", "429", "500", "502", "503", "504"]) else False
                elif "json" in lower:
                    code_val = DiagnosticCode.llm_invalid_response
                    retryable = True

                diagnostics.append(
                    ReviewDiagnostic(
                        code=code_val,
                        message=f"LLM stage failed: {msg}",
                        severity="warning",
                        status_code=status_code,
                        retryable=retryable,
                        metadata={"detail": msg, "exception_type": type(e).__name__},
                    )
                )

        issues = dedupe_issues(issues)

        if enabled_checks:
            allow_security = bool(enabled_checks.get("security", True))
            allow_style = bool(enabled_checks.get("style", True))
            allow_perf = bool(enabled_checks.get("performance", True))

            def _allowed(cat: Category) -> bool:
                if cat == Category.security:
                    return allow_security
                if cat == Category.style:
                    return allow_style
                if cat == Category.performance:
                    return allow_perf
                # UI does not expose toggles for these; keep them always-on.
                return True

            issues = [i for i in issues if _allowed(i.category)]

        score = score_issues(issues=issues, strict=strict)
        return ReviewResult(issues=issues, score=score, static_analysis=static_dict, diagnostics=diagnostics)

    async def review_project(self, req: ProjectReviewRequest) -> ProjectReviewResult:
        per_file: dict[str, ReviewResult] = {}
        all_issues = []
        overall_static: dict[str, Any] = {"files": {}}
        diagnostics: list[ReviewDiagnostic] = []

        for f in req.files:
            r = await self.review_file(
                filename=f.filename,
                code=f.code,
                strict=req.strict,
                enabled_rules=req.enabled_rules,
                language=getattr(f, "language", "python"),
            )
            per_file[f.filename] = r
            all_issues.extend(r.issues)
            diagnostics.extend(r.diagnostics)
            overall_static["files"][f.filename] = r.static_analysis

        all_issues = dedupe_issues(all_issues)
        overall_score = score_issues(issues=all_issues, strict=req.strict)
        overall = ReviewResult(issues=all_issues, score=overall_score, static_analysis=overall_static, diagnostics=diagnostics)
        return ProjectReviewResult(files=per_file, overall=overall, diagnostics=diagnostics)
