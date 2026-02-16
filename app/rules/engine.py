from __future__ import annotations

import ast

from app.analysis.models import Issue
from app.rules.base import RuleContext
from app.rules.builtin import BUILTIN_RULES


def run_custom_rules(
    *,
    code: str,
    filename: str,
    strict: bool,
    enabled_rules: dict[str, bool] | None = None,
) -> list[Issue]:
    try:
        tree = ast.parse(code, filename=filename)
    except SyntaxError:
        # Syntax errors are handled by flake8 builtin fallback; rules depend on AST.
        return []

    ctx = RuleContext(filename=filename, code=code, tree=tree, strict=strict)

    issues: list[Issue] = []
    for r in BUILTIN_RULES:
        enabled = r.default_enabled
        if enabled_rules and r.rule_id in enabled_rules:
            enabled = bool(enabled_rules[r.rule_id])
        if not enabled:
            continue
        issues.extend(r.run(ctx))

    return issues
