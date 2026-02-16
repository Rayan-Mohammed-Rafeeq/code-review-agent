from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Protocol

from app.analysis.models import Category, Issue, Severity


@dataclass(frozen=True)
class RuleContext:
    filename: str
    code: str
    tree: ast.AST
    strict: bool


class Rule(Protocol):
    """A custom rule that returns zero or more Issues."""

    rule_id: str
    description: str
    default_enabled: bool

    def run(self, ctx: RuleContext) -> list[Issue]: ...


def issue(
    *,
    filename: str,
    line: int,
    category: Category,
    severity: Severity,
    description: str,
    suggestion: str,
    rule_id: str,
) -> Issue:
    return Issue(
        file=filename,
        line=max(1, int(line or 1)),
        category=category,
        severity=severity,
        description=description,
        suggestion=suggestion,
        source="custom_rules",
        code=rule_id,
    )
