from app.models import Category, Issue, Severity
from app.ranker import rank_issues


def test_rank_orders_by_severity_then_category():
    issues = [
        Issue(severity=Severity.low, category=Category.security, description="a", suggestion="x"),
        Issue(severity=Severity.high, category=Category.style, description="b", suggestion="x"),
        Issue(severity=Severity.high, category=Category.security, description="c", suggestion="x"),
    ]

    ranked = rank_issues(issues)
    assert ranked[0].severity == Severity.high and ranked[0].category == Category.security
    assert ranked[1].severity == Severity.high and ranked[1].category == Category.style


def test_rank_category_priority_within_same_severity():
    issues = [
        Issue(severity=Severity.medium, category=Category.style, description="s", suggestion="x"),
        Issue(severity=Severity.medium, category=Category.performance, description="p", suggestion="x"),
        Issue(severity=Severity.medium, category=Category.bug, description="b", suggestion="x"),
        Issue(severity=Severity.medium, category=Category.security, description="sec", suggestion="x"),
    ]

    ranked = rank_issues(issues)
    assert [i.category for i in ranked] == [
        Category.security,
        Category.bug,
        Category.performance,
        Category.style,
    ]


def test_rank_severity_always_beats_category():
    issues = [
        Issue(severity=Severity.medium, category=Category.style, description="m-style", suggestion="x"),
        Issue(severity=Severity.low, category=Category.security, description="l-sec", suggestion="x"),
    ]

    ranked = rank_issues(issues)
    assert ranked[0].severity == Severity.medium
    assert ranked[1].severity == Severity.low
