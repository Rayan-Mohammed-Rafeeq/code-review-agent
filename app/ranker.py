from __future__ import annotations

from app.models import Category, Issue, Severity


# Priority contract:
# - Highest severity first: high > medium > low
# - Then by category: security > bug > performance > style
_SEVERITY_WEIGHT = {Severity.high: 0, Severity.medium: 1, Severity.low: 2}
_CATEGORY_WEIGHT = {Category.security: 0, Category.bug: 1, Category.performance: 2, Category.style: 3}


def rank_issues(issues: list[Issue]) -> list[Issue]:
    return sorted(
        issues,
        key=lambda i: (
            _SEVERITY_WEIGHT.get(i.severity, 999),
            _CATEGORY_WEIGHT.get(i.category, 999),
            i.location or "",
            i.description,
        ),
    )
