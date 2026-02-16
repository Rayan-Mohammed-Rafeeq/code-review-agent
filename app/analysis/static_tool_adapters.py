from __future__ import annotations

from typing import Any

from app.analysis.aggregate import normalize_severity
from app.analysis.models import Category, Issue, Severity


def issues_from_flake8(*, flake8: dict[str, Any], filename: str) -> list[Issue]:
    out: list[Issue] = []
    for it in flake8.get("issues") or []:
        code = (it.get("code") or "").strip()
        msg = (it.get("message") or "").strip() or "flake8 issue"
        row = int(it.get("row") or 1)

        sev: Severity
        if code.startswith("E9"):
            sev = Severity.critical
        elif code.startswith("F"):
            sev = Severity.high
        elif code.startswith("E"):
            sev = Severity.medium
        else:
            sev = Severity.low

        out.append(
            Issue(
                file=filename,
                line=max(1, row),
                category=Category.style,
                severity=sev,
                description=f"{code}: {msg}" if code else msg,
                suggestion="Fix the reported lint issue.",
                source="flake8",
                code=code or None,
                metadata={"col": it.get("col")},
            )
        )
    return out


def issues_from_bandit(*, bandit: dict[str, Any], filename: str) -> list[Issue]:
    out: list[Issue] = []
    result = bandit.get("result") or {}
    for it in (result.get("results") or []) if isinstance(result, dict) else []:
        line = int(it.get("line_number") or 1)
        test_id = (it.get("test_id") or "").strip() or None
        issue_text = (it.get("issue_text") or "").strip() or "bandit issue"
        severity = normalize_severity(it.get("issue_severity"))

        out.append(
            Issue(
                file=filename,
                line=max(1, line),
                category=Category.security,
                severity=severity,
                description=f"{test_id}: {issue_text}" if test_id else issue_text,
                suggestion="Address the Bandit finding; prefer safe APIs and input validation.",
                source="bandit",
                code=test_id,
                metadata={
                    "confidence": it.get("issue_confidence"),
                    "more_info": it.get("more_info"),
                },
            )
        )
    return out
