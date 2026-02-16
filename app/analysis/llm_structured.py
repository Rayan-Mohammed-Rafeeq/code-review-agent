from __future__ import annotations

import json

from pydantic import BaseModel, Field, ValidationError

from app.analysis.models import Category, Issue, Severity


class LLMIssue(BaseModel):
    line: int = Field(ge=1)
    category: Category
    severity: Severity
    description: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)


class LLMResponse(BaseModel):
    issues: list[LLMIssue]


def build_llm_instructions(*, strict: bool) -> str:
    return (
        "Return JSON only. No markdown, no code fences, no extra keys. "
        'Schema: {"issues":[{"line":int,"category":"bug|performance|security|style",'
        '"severity":"critical|high|medium|low|info","description":str,"suggestion":str}]} '
        + ("Be strict and exhaustive." if strict else "Prioritize high-signal issues.")
    )


def parse_llm_json(*, text: str) -> LLMResponse:
    raw = (text or "").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON: {e.msg}") from e
    try:
        return LLMResponse.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"LLM JSON does not match schema: {e}") from e


def llm_response_to_issues(*, resp: LLMResponse, filename: str) -> list[Issue]:
    out: list[Issue] = []
    for it in resp.issues:
        out.append(
            Issue(
                file=filename,
                line=it.line,
                category=it.category,
                severity=it.severity,
                description=it.description,
                suggestion=it.suggestion,
                source="llm",
            )
        )
    return out
