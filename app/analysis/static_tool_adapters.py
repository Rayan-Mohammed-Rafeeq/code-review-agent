from __future__ import annotations

import os
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


def issues_from_eslint(*, eslint: dict[str, Any], filename: str) -> list[Issue]:
    out: list[Issue] = []

    # Expected shape (see app.static_checks.run_eslint):
    # {
    #   tool: "eslint",
    #   exit_code: int,
    #   results: [ { filePath, messages: [ { ruleId, severity, message, line, column } ] } ],
    #   stderr: str
    # }
    results = eslint.get("results") or []
    if not isinstance(results, list):
        return out

    for res in results:
        if not isinstance(res, dict):
            continue
        for msg in (res.get("messages") or []) if isinstance(res.get("messages"), list) else []:
            if not isinstance(msg, dict):
                continue

            rule_id = (msg.get("ruleId") or "").strip() or None
            message = (msg.get("message") or "").strip() or "eslint issue"
            line = int(msg.get("line") or 1)
            col = int(msg.get("column") or 0)

            # ESLint severity: 2=error, 1=warn, 0=off
            sev_num = int(msg.get("severity") or 0)
            if sev_num >= 2:
                sev = Severity.medium
            elif sev_num == 1:
                sev = Severity.low
            else:
                sev = Severity.info

            # Heuristic classification:
            cat = Category.style
            rid_lower = (rule_id or "").lower()
            if any(k in rid_lower for k in ["security", "xss", "detect", "no-eval", "no-implied-eval"]):
                cat = Category.security

            out.append(
                Issue(
                    file=filename,
                    line=max(1, line),
                    category=cat,
                    severity=sev,
                    description=(f"{rule_id}: {message}" if rule_id else message),
                    suggestion="Fix the ESLint finding.",
                    source="eslint",
                    code=rule_id,
                    metadata={"col": col, "ruleId": rule_id},
                )
            )

    return out


def issues_from_javac(*, javac: dict[str, Any], filename: str) -> list[Issue]:
    """Parse javac stderr into Issues.

    We keep this intentionally simple: javac output isn't stable JSON.
    Typical lines look like:
      Foo.java:3: error: ';' expected
    """
    out: list[Issue] = []
    if not isinstance(javac, dict) or javac.get("skipped") is True:
        return out

    stderr = (javac.get("stderr") or "") if isinstance(javac.get("stderr"), str) else ""
    base = (javac.get("filename") or "") if isinstance(javac.get("filename"), str) else ""
    base = base or os.path.basename(filename)

    for line in stderr.splitlines():
        text = line.rstrip()
        if not text.strip():
            continue

        stripped = text.strip()
        # Filter noisy context lines javac prints (source excerpt, caret pointer, totals).
        if stripped == "^":
            continue
        if stripped.lower().endswith("error") and stripped.lower().startswith("1 "):
            continue
        if stripped.lower().endswith("errors") or stripped.lower().endswith("warnings"):
            continue
        if stripped.startswith("Note:") or stripped.startswith("warning:"):
            # keep warnings/errors with file:line prefix; drop standalone notes
            if ":" not in stripped:
                continue

        # Prefer to show messages as <SubmittedFile>:<line>: ... (hide temp dir)
        if base and base in stripped:
            idx = stripped.find(base)
            stripped = stripped[idx:]

        line_no = 1
        parts = stripped.split(":")
        if len(parts) >= 3:
            try:
                line_no = int(parts[1])
            except ValueError:
                line_no = 1

        sev = Severity.high if "error" in stripped.lower() else Severity.low
        out.append(
            Issue(
                file=filename,
                line=max(1, line_no),
                category=Category.bug,
                severity=sev,
                description=f"javac: {stripped.strip()}",
                suggestion="Fix the Java compilation warning/error.",
                source="javac",
                code=None,
                metadata={},
            )
        )

    return out


def issues_from_dotnet_format(*, dotnet_format: dict[str, Any], filename: str) -> list[Issue]:
    out: list[Issue] = []
    if not isinstance(dotnet_format, dict) or dotnet_format.get("skipped") is True:
        return out

    stderr = (dotnet_format.get("stderr") or "") if isinstance(dotnet_format.get("stderr"), str) else ""
    stdout = (dotnet_format.get("stdout") or "") if isinstance(dotnet_format.get("stdout"), str) else ""
    combined = (stdout + "\n" + stderr).strip()
    if not combined:
        return out

    # dotnet format doesn't always provide file/line. Emit a single summary issue.
    sev = Severity.low if dotnet_format.get("exit_code") in (0, None) else Severity.medium
    out.append(
        Issue(
            file=filename,
            line=1,
            category=Category.style,
            severity=sev,
            description="dotnet format: formatting/style issues detected"
            if dotnet_format.get("exit_code")
            else "dotnet format output",
            suggestion="Run dotnet format (or fix the reported formatting/style issue).",
            source="dotnet_format",
            code=None,
            metadata={"output": combined[:2000]},
        )
    )
    return out


def issues_from_golangci_lint(*, golangci: dict[str, Any], filename: str) -> list[Issue]:
    out: list[Issue] = []
    if not isinstance(golangci, dict) or golangci.get("skipped") is True:
        return out

    result = golangci.get("result") or {}
    if not isinstance(result, dict):
        return out

    # golangci-lint json:
    # { "Issues": [ { "FromLinter", "Text", "Pos": {"Filename","Line","Column"} } ] }
    issues = result.get("Issues") or result.get("issues") or []
    if not isinstance(issues, list):
        return out

    for it in issues:
        if not isinstance(it, dict):
            continue
        text = (it.get("Text") or it.get("text") or "").strip() or "golangci-lint issue"
        linter = (it.get("FromLinter") or it.get("fromLinter") or it.get("linter") or "").strip() or None
        pos = it.get("Pos") or it.get("pos") or {}
        line = 1
        col = 0
        if isinstance(pos, dict):
            try:
                line = int(pos.get("Line") or pos.get("line") or 1)
            except ValueError:
                line = 1
            try:
                col = int(pos.get("Column") or pos.get("column") or 0)
            except ValueError:
                col = 0

        out.append(
            Issue(
                file=filename,
                line=max(1, line),
                category=Category.bug,
                severity=Severity.medium,
                description=f"{linter}: {text}" if linter else text,
                suggestion="Fix the linter finding.",
                source="golangci-lint",
                code=linter,
                metadata={"col": col, "linter": linter},
            )
        )

    return out


def issues_from_cargo_clippy(*, clippy: dict[str, Any], filename: str) -> list[Issue]:
    out: list[Issue] = []
    if not isinstance(clippy, dict) or clippy.get("skipped") is True:
        return out

    messages = clippy.get("messages") or []
    if not isinstance(messages, list):
        return out

    for msg in messages:
        if not isinstance(msg, dict):
            continue
        if msg.get("reason") != "compiler-message":
            continue
        m = msg.get("message") or {}
        if not isinstance(m, dict):
            continue
        rendered = (m.get("rendered") or "") if isinstance(m.get("rendered"), str) else ""
        code_obj = m.get("code") or {}
        code = None
        if isinstance(code_obj, dict):
            code = (code_obj.get("code") or "") or None

        spans = m.get("spans") or []
        line = 1
        col = 0
        if isinstance(spans, list) and spans:
            first = spans[0]
            if isinstance(first, dict):
                line = int(first.get("line_start") or 1)
                col = int(first.get("column_start") or 0)

        level = (m.get("level") or "").lower()
        sev = Severity.medium
        if level in {"error", "fatal"}:
            sev = Severity.high
        elif level in {"warning"}:
            sev = Severity.medium
        else:
            sev = Severity.low

        out.append(
            Issue(
                file=filename,
                line=max(1, line),
                category=Category.bug,
                severity=sev,
                description=(rendered.strip() or "clippy finding").splitlines()[0],
                suggestion="Fix the clippy finding.",
                source="clippy",
                code=code,
                metadata={"col": col, "level": level},
            )
        )

    return out
