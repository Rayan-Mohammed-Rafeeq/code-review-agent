from __future__ import annotations

import json

from pydantic import BaseModel, Field, ValidationError

from app.analysis.models import Category, Issue, Severity


class LLMIssue(BaseModel):
    line: int = Field(ge=1)
    category: Category
    severity: Severity
    description: str = Field(min_length=1)
    impact: str = Field(default="", description="Impact statement; may be omitted by some models")
    suggestion: str = Field(min_length=1)


class LLMResponse(BaseModel):
    issues: list[LLMIssue]


def build_llm_instructions(*, strict: bool) -> str:
    # Keep it short but unambiguous; models follow this better than long prose.
    schema = (
        '{"issues":[{'
        '"line":int,'
        '"category":"bug|security|performance|maintainability|style",'
        '"severity":"critical|high|medium|low|info",'
        '"description":string,'
        '"impact":string,'
        '"suggestion":string'
        "}]} "
    )
    return "Return STRICT JSON only (no markdown, no code fences, no extra keys). " "Format: " + schema + (
        "Be strict and exhaustive." if strict else "Prioritize high-signal issues."
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
        md = {"impact": it.impact} if (it.impact or "").strip() else {}
        out.append(
            Issue(
                file=filename,
                line=it.line,
                category=it.category,
                severity=it.severity,
                description=it.description,
                suggestion=it.suggestion,
                source="llm",
                metadata=md,
            )
        )
    return out
