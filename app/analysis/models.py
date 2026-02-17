from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class Category(str, Enum):
    bug = "bug"
    security = "security"
    performance = "performance"
    maintainability = "maintainability"
    style = "style"


IssueSource = Literal["custom_rules", "flake8", "bandit", "llm"]


class Issue(BaseModel):
    file: str = Field(default="input.py", description="Filename the issue belongs to")
    line: int = Field(default=1, ge=1)
    category: Category
    severity: Severity
    description: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)
    source: IssueSource

    # Original tool/rule identifiers and any extra metadata.
    code: str | None = None
    fingerprint: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FileReviewRequest(BaseModel):
    filename: str = Field(default="input.py")
    code: str = Field(min_length=1)
    language: str = Field(default="python", description="Language of the submitted code")
    enabled_checks: dict[str, bool] | None = Field(
        default=None,
        description=(
            "Optional check toggles from the frontend. Keys: security|style|performance. "
            "When provided, only enabled categories are returned/scored."
        ),
    )


class ProjectReviewRequest(BaseModel):
    files: list[FileReviewRequest] = Field(min_length=1)
    strict: bool = False
    enabled_rules: dict[str, bool] | None = Field(
        default=None,
        description="Optional per-rule enable/disable map applied on top of defaults",
    )


class ScoreBreakdown(BaseModel):
    score: int = Field(ge=0, le=100)
    penalties_by_severity: dict[Severity, float]
    counts_by_severity: dict[Severity, int]
    counts_by_category: dict[Category, int]


class DiagnosticCode(str, Enum):
    llm_rate_limited = "llm_rate_limited"
    llm_http_error = "llm_http_error"
    llm_timeout = "llm_timeout"
    llm_network_error = "llm_network_error"
    llm_invalid_response = "llm_invalid_response"
    llm_disabled = "llm_disabled"


class ReviewDiagnostic(BaseModel):
    code: DiagnosticCode
    message: str = Field(min_length=1)
    severity: Literal["info", "warning", "error"] = "warning"
    provider: str | None = None
    status_code: int | None = None
    retryable: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewResult(BaseModel):
    issues: list[Issue]
    score: ScoreBreakdown
    static_analysis: dict[str, Any] = Field(default_factory=dict)
    diagnostics: list[ReviewDiagnostic] = Field(default_factory=list)


class ProjectReviewResult(BaseModel):
    files: dict[str, ReviewResult]
    overall: ReviewResult
    diagnostics: list[ReviewDiagnostic] = Field(default_factory=list)
