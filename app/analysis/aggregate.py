from __future__ import annotations

import hashlib

from app.analysis.models import Issue, Severity


def normalize_severity(s: str | None) -> Severity:
    v = (s or "").strip().lower()
    mapping = {
        "critical": Severity.critical,
        "high": Severity.high,
        "medium": Severity.medium,
        "low": Severity.low,
        "info": Severity.info,
        "minor": Severity.low,
        "major": Severity.high,
    }
    return mapping.get(v, Severity.medium)


def fingerprint_issue(i: Issue) -> str:
    key = f"{i.file}|{i.line}|{i.category}|{i.severity}|{i.description.strip()}|{i.source}|{i.code or ''}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def dedupe_issues(issues: list[Issue]) -> list[Issue]:
    seen: set[str] = set()
    out: list[Issue] = []
    for i in issues:
        fp = i.fingerprint or fingerprint_issue(i)
        if fp in seen:
            continue
        seen.add(fp)
        i.fingerprint = fp
        out.append(i)
    return out
