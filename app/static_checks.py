from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class StaticAnalysisResult:
    flake8: dict[str, Any]
    bandit: dict[str, Any]


def run_static_analysis(*, code: str, filename: str = "input.py") -> StaticAnalysisResult:
    """Run flake8 and bandit on code by writing it to a temp file.

    Note: We also run a tiny built-in sanity check to catch obvious problems
    (syntax errors and undefined names) even when external tools aren't
    available or return empty output.
    """
    with tempfile.TemporaryDirectory(prefix="code_review_agent_") as tmp:
        path = os.path.join(tmp, filename)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)

        flake8 = _run_flake8(path)
        bandit = _run_bandit(path)

    flake8 = _augment_with_builtin_checks(code=code, filename=filename, flake8=flake8)
    return StaticAnalysisResult(flake8=flake8, bandit=bandit)


def run_static_analysis_on_file(path: str) -> dict[str, Any]:
    """Run flake8 and bandit on an existing file and return a single JSON-serializable dict.

    Contract:
    - Input: filesystem path to a readable Python source file
    - Output: structured JSON: {metadata, flake8, bandit}
    - Errors:
      - raises FileNotFoundError / IsADirectoryError for invalid paths
      - raises ValueError for non-.py inputs (to avoid accidental scanning of arbitrary files)
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    if os.path.isdir(path):
        raise IsADirectoryError(path)
    if not path.lower().endswith(".py"):
        raise ValueError("Only .py files are supported")

    flake8 = _run_flake8(path)
    bandit = _run_bandit(path)

    now = datetime.now(timezone.utc).isoformat()
    return {
        "metadata": {"path": os.path.abspath(path), "scanned_at": now},
        "flake8": flake8,
        "bandit": bandit,
    }


def _run_flake8(path: str) -> dict[str, Any]:
    # Use a delimiter that won't conflict with Windows drive letters ("C:\\...").
    # ':' is ambiguous on Windows and can lead to empty issue lists even when flake8
    # reports findings.
    delimiter = "|"
    cmd = [
        sys.executable,
        "-m",
        "flake8",
        f"--format=%(path)s{delimiter}%(row)d{delimiter}%(col)d{delimiter}%(code)s{delimiter}%(text)s",
        path,
    ]

    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as e:
        # Python executable not found for some reason
        return {
            "exit_code": 127,
            "issues": [],
            "stderr": str(e),
            "tool": "flake8",
            "tool_error": True,
        }

    issues: list[dict[str, Any]] = []
    parse_error = False

    out = (p.stdout or "").strip()
    for line in out.splitlines():
        parts = line.split(delimiter, 4)
        if len(parts) != 5:
            # Don't drop the whole run silently if output is present but unparsable.
            parse_error = True
            continue
        fpath, row, col, code, text = parts
        try:
            row_i = int(row)
            col_i = int(col)
        except ValueError:
            parse_error = True
            continue
        issues.append(
            {
                "path": fpath,
                "row": row_i,
                "col": col_i,
                "code": code,
                "message": text.strip(),
            }
        )

    stderr = (p.stderr or "").strip()

    # If flake8 says "something is wrong" (nonzero) but we parsed no issues, surface
    # that as a tool error instead of incorrectly implying a clean result.
    tool_error = bool(p.returncode not in (0, 1))
    if p.returncode != 0 and not issues and (stderr or parse_error):
        tool_error = True

    raw_output = ""
    if (tool_error or parse_error) and not issues:
        # Keep this small to avoid bloating responses.
        combined = (out + "\n" + stderr).strip()
        raw_output = combined[:2000]

    result: dict[str, Any] = {
        "exit_code": p.returncode,
        "issues": issues,
        "stderr": stderr,
        "tool": "flake8",
    }
    if parse_error:
        result["parse_error"] = True
    if tool_error:
        result["tool_error"] = True
    if raw_output:
        result["raw_output"] = raw_output

    return result


def _run_bandit(path: str) -> dict[str, Any]:
    cmd = [sys.executable, "-m", "bandit", "-q", "-f", "json", path]

    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as e:
        return {"exit_code": 127, "result": {}, "stderr": str(e), "tool": "bandit"}

    stdout = (p.stdout or "").strip()
    result: dict[str, Any]
    if stdout:
        try:
            result = json.loads(stdout)
        except json.JSONDecodeError:
            result = {"raw": stdout}
    else:
        result = {}

    return {
        "exit_code": p.returncode,
        "result": result,
        "stderr": (p.stderr or "").strip(),
        "tool": "bandit",
    }


def _augment_with_builtin_checks(*, code: str, filename: str, flake8: dict[str, Any]) -> dict[str, Any]:
    """Augment flake8-like output with a minimal built-in analyzer.

    This is intentionally small and conservative. It's a safety net for:
    - Syntax errors (compile/parse failures)
    - Obvious typos of undefined names at module scope (e.g., `prin(...)`)

    We only add findings if flake8 didn't already report any issues.
    """
    issues = list(flake8.get("issues") or [])
    if issues:
        return flake8

    builtin_issues: list[dict[str, Any]] = []

    # 1) Syntax errors
    try:
        tree = ast.parse(code, filename=filename)
    except SyntaxError as e:
        builtin_issues.append(
            {
                "path": filename,
                "row": int(getattr(e, "lineno", 1) or 1),
                "col": int(getattr(e, "offset", 0) or 0),
                "code": "E999",
                "message": f"SyntaxError: {e.msg}",
            }
        )
        out = dict(flake8)
        out["issues"] = builtin_issues
        out["tool"] = out.get("tool") or "flake8"
        out["builtin_fallback"] = True
        out["exit_code"] = int(out.get("exit_code") or 1)
        return out

    # 2) Undefined names at module scope (very small approximation).
    # Track simple assignments and function/class definitions; then report
    # any Name nodes in Load context that aren't builtins or previously defined.
    builtins = set(dir(__builtins__))  # type: ignore[arg-type]
    defined: set[str] = set()

    class _Collector(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
            defined.add(node.name)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
            defined.add(node.name)

        def visit_ClassDef(self, node: ast.ClassDef) -> Any:
            defined.add(node.name)

        def visit_Import(self, node: ast.Import) -> Any:
            for alias in node.names:
                defined.add(alias.asname or alias.name.split(".")[0])

        def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
            for alias in node.names:
                if alias.name == "*":
                    continue
                defined.add(alias.asname or alias.name)

        def visit_Assign(self, node: ast.Assign) -> Any:
            for t in node.targets:
                self._add_target(t)
            self.generic_visit(node.value)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
            self._add_target(node.target)
            if node.value is not None:
                self.generic_visit(node.value)

        def visit_AugAssign(self, node: ast.AugAssign) -> Any:
            self._add_target(node.target)
            self.generic_visit(node.value)

        def _add_target(self, t: ast.AST) -> None:
            if isinstance(t, ast.Name):
                defined.add(t.id)
            elif isinstance(t, (ast.Tuple, ast.List)):
                for elt in t.elts:
                    self._add_target(elt)

    class _UndefinedFinder(ast.NodeVisitor):
        def __init__(self) -> None:
            self.undefined: list[ast.Name] = []

        def visit_Name(self, node: ast.Name) -> Any:
            if isinstance(node.ctx, ast.Load):
                if node.id not in defined and node.id not in builtins:
                    self.undefined.append(node)
            return self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
            # Don't recurse into function bodies; this fallback is primarily
            # for obvious top-level mistakes.
            return None

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
            return None

        def visit_ClassDef(self, node: ast.ClassDef) -> Any:
            return None

    _Collector().visit(tree)
    finder = _UndefinedFinder()
    finder.visit(tree)

    for n in finder.undefined:
        builtin_issues.append(
            {
                "path": filename,
                "row": int(getattr(n, "lineno", 1) or 1),
                "col": int(getattr(n, "col_offset", 0) or 0) + 1,
                "code": "F821",
                "message": f"undefined name '{n.id}' (builtin fallback)",
            }
        )

    if not builtin_issues:
        return flake8

    out = dict(flake8)
    out["issues"] = builtin_issues
    out["tool"] = out.get("tool") or "flake8"
    out["builtin_fallback"] = True
    out["exit_code"] = int(out.get("exit_code") or 1)
    return out
