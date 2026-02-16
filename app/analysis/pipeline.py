from __future__ import annotations

import json
from typing import Any

from app.analysis.aggregate import dedupe_issues
from app.analysis.llm_structured import build_llm_instructions, llm_response_to_issues, parse_llm_json
from app.analysis.logical_checks import run_logical_checks
from app.analysis.models import ProjectReviewRequest, ProjectReviewResult, ReviewResult
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
    ) -> ReviewResult:
        code = preprocess_code(code=code)

        static = run_static_analysis(code=code, filename=filename)
        static_dict: dict[str, Any] = {"flake8": static.flake8, "bandit": static.bandit}

        issues = []
        issues.extend(run_logical_checks(code=code, filename=filename, strict=strict))
        issues.extend(run_custom_rules(code=code, filename=filename, strict=strict, enabled_rules=enabled_rules))
        issues.extend(issues_from_flake8(flake8=static.flake8, filename=filename))
        issues.extend(issues_from_bandit(bandit=static.bandit, filename=filename))

        if self._llm is not None:
            prompt_payload = {
                "filename": filename,
                "code": code,
                "instructions": build_llm_instructions(strict=strict),
            }
            raw = await self._llm.raw_review_json(review_payload=json.dumps(prompt_payload))
            resp = parse_llm_json(text=raw)
            issues.extend(llm_response_to_issues(resp=resp, filename=filename))

        issues = dedupe_issues(issues)
        score = score_issues(issues=issues, strict=strict)
        return ReviewResult(issues=issues, score=score, static_analysis=static_dict)

    async def review_project(self, req: ProjectReviewRequest) -> ProjectReviewResult:
        per_file: dict[str, ReviewResult] = {}
        all_issues = []
        overall_static: dict[str, Any] = {"files": {}}

        for f in req.files:
            r = await self.review_file(
                filename=f.filename,
                code=f.code,
                strict=req.strict,
                enabled_rules=req.enabled_rules,
            )
            per_file[f.filename] = r
            all_issues.extend(r.issues)
            overall_static["files"][f.filename] = r.static_analysis

        all_issues = dedupe_issues(all_issues)
        overall_score = score_issues(issues=all_issues, strict=req.strict)
        overall = ReviewResult(issues=all_issues, score=overall_score, static_analysis=overall_static)
        return ProjectReviewResult(files=per_file, overall=overall)
