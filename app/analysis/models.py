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
    performance = "performance"
    security = "security"
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


class ReviewResult(BaseModel):
    issues: list[Issue]
    score: ScoreBreakdown
    static_analysis: dict[str, Any] = Field(default_factory=dict)


class ProjectReviewResult(BaseModel):
    files: dict[str, ReviewResult]
    overall: ReviewResult
