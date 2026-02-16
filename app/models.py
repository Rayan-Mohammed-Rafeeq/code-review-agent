from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Category(str, Enum):
    security = "security"
    bug = "bug"
    performance = "performance"
    style = "style"


class Issue(BaseModel):
    severity: Severity
    category: Category
    description: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)
    location: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Source code to review")
    language: str = Field(default="python", description="Language of the submitted code")
    filename: Optional[str] = Field(default="input.py", description="Optional filename for diagnostics")
    strict: bool = Field(
        default=False,
        description=("When true, the API also returns a strict, human-readable findings string in a fixed format."),
    )


class ReviewResponse(BaseModel):
    compressed_context: str
    static_analysis: dict[str, Any]
    issues: list[Issue]
    strict_findings: Optional[str] = None


# JSON Schema used to instruct the LLM to return a strict structure.
LLM_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                    "category": {"type": "string", "enum": ["security", "bug", "performance", "style"]},
                    "description": {"type": "string"},
                    "suggestion": {"type": "string"},
                    "location": {"type": ["string", "null"]},
                },
                "required": ["severity", "category", "description", "suggestion"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["issues"],
    "additionalProperties": False,
}
