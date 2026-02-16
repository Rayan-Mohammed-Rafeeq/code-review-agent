from __future__ import annotations

from typing import Iterable

from app.models import Issue


def format_strict_findings(issues: Iterable[Issue]) -> str:
    """Format issues in the strict, human-readable review format.

    Contract:
    - Input: iterable of Issue models
    - Output: a single string containing one block per issue, separated by a blank line.
    - If there are no issues, returns an empty string.

    Format per issue:
      Issue <n>
      Severity: low|medium|high
      Category: <category>
      Problem: <description>
      Suggestion: <suggestion>
    """
    issue_list = list(issues)
    if not issue_list:
        return ""

    blocks: list[str] = []
    for idx, issue in enumerate(issue_list, start=1):
        blocks.append(
            "\n".join(
                [
                    f"Issue {idx}",
                    f"Severity: {issue.severity}",
                    f"Category: {issue.category}",
                    f"Problem: {issue.description}",
                    f"Suggestion: {issue.suggestion}",
                ]
            )
        )

    return "\n\n".join(blocks) + "\n"
