from __future__ import annotations

from collections import Counter, defaultdict

from app.analysis.models import Category, Issue, ScoreBreakdown, Severity

SEVERITY_PENALTY: dict[Severity, float] = {
    Severity.critical: 15.0,
    Severity.high: 8.0,
    Severity.medium: 4.0,
    Severity.low: 1.5,
    Severity.info: 0.5,
}

CATEGORY_MULTIPLIER: dict[Category, float] = {
    Category.security: 1.3,
    Category.bug: 1.1,
    Category.performance: 1.0,
    Category.style: 0.8,
}


def score_issues(*, issues: list[Issue], strict: bool) -> ScoreBreakdown:
    penalties_by_sev: dict[Severity, float] = defaultdict(float)
    counts_by_sev: Counter[Severity] = Counter()
    counts_by_cat: Counter[Category] = Counter()

    for i in issues:
        counts_by_sev[i.severity] += 1
        counts_by_cat[i.category] += 1

        base = SEVERITY_PENALTY[i.severity]
        mult = CATEGORY_MULTIPLIER[i.category]
        penalties_by_sev[i.severity] += base * mult

    total_penalty = sum(penalties_by_sev.values())
    if strict:
        total_penalty *= 1.15

    score = int(round(max(0.0, 100.0 - total_penalty)))

    return ScoreBreakdown(
        score=score,
        penalties_by_severity=dict(penalties_by_sev),
        counts_by_severity=dict(counts_by_sev),
        counts_by_category=dict(counts_by_cat),
    )
