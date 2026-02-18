from __future__ import annotations

import ast
import json
import os
import shutil
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

    # Python implicitly defines a handful of module globals.
    # If we don't include them, the fallback can false-positive on
    # `if __name__ == "__main__":` and similar patterns.
    implicit_module_globals = {"__name__", "__file__", "__package__", "__spec__", "__cached__", "__loader__"}

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
                if node.id not in defined and node.id not in builtins and node.id not in implicit_module_globals:
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


def run_eslint(*, code: str, filename: str) -> dict[str, Any]:
    """Run ESLint on JavaScript/TypeScript code.

    Best-effort:
    - If ESLint isn't installed, returns {skipped: True}.
    - If ESLint errors, returns a tool_error payload but still JSON serializable.

    Note: This uses the repo's frontend eslint installation when available.
    """
    name = (filename or "").lower()
    if not (name.endswith(".js") or name.endswith(".jsx") or name.endswith(".ts") or name.endswith(".tsx")):
        return {"tool": "eslint", "skipped": True}

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    eslint_bin = os.path.join(repo_root, "frontend", "node_modules", ".bin", "eslint.cmd")
    if not os.path.exists(eslint_bin):
        return {"tool": "eslint", "skipped": True, "reason": "frontend/node_modules/.bin/eslint.cmd not found"}

    with tempfile.TemporaryDirectory(prefix="code_review_agent_eslint_") as tmp:
        path = os.path.join(tmp, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)

        cmd = [
            eslint_bin,
            "--format",
            "json",
            "--no-eslintrc",
            "--rule",
            "no-undef:2",
            "--rule",
            "no-unused-vars:2",
            path,
        ]

        try:
            p = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_root)
        except FileNotFoundError as e:
            return {"tool": "eslint", "skipped": True, "reason": str(e)}

        stdout = (p.stdout or "").strip()
        stderr = (p.stderr or "").strip()
        results: Any = []
        if stdout:
            try:
                results = json.loads(stdout)
            except json.JSONDecodeError:
                results = []

        return {
            "tool": "eslint",
            "exit_code": p.returncode,
            "results": results,
            "stderr": stderr,
            "tool_error": bool(p.returncode not in (0, 1) and not results),
        }


def _skipped(tool: str, *, reason: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"tool": tool, "skipped": True}
    if reason:
        out["reason"] = reason
    return out


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def run_static_analysis_for_language(*, code: str, filename: str, language: str) -> dict[str, Any]:
    """Best-effort static analysis across supported languages.

    Returns a JSON-serializable dict with stable keys. Tools are invoked only when:
    - the language matches, and
    - an appropriate CLI tool is available.

    Missing tools should return a `{skipped: True}` payload instead of raising.
    """
    lang = (language or "").strip().lower()
    name = (filename or "").lower()

    # Python
    if lang == "python" and name.endswith(".py"):
        static = run_static_analysis(code=code, filename=filename)
        return {"flake8": static.flake8, "bandit": static.bandit, "eslint": _skipped("eslint")}

    # JS/TS
    if lang in {"javascript", "typescript"} and (
        name.endswith(".js") or name.endswith(".jsx") or name.endswith(".ts") or name.endswith(".tsx")
    ):
        return {
            "flake8": _skipped("flake8"),
            "bandit": _skipped("bandit"),
            "eslint": run_eslint(code=code, filename=filename),
        }

    # Java
    if lang == "java" and name.endswith(".java"):
        return {
            "flake8": _skipped("flake8"),
            "bandit": _skipped("bandit"),
            "eslint": _skipped("eslint"),
            "javac": run_javac(code=code, filename=filename),
        }

    # C#
    if lang in {"c#", "csharp"} and name.endswith(".cs"):
        return {
            "flake8": _skipped("flake8"),
            "bandit": _skipped("bandit"),
            "eslint": _skipped("eslint"),
            "dotnet_format": run_dotnet_format(code=code, filename=filename),
        }

    # Go
    if lang == "go" and name.endswith(".go"):
        return {
            "flake8": _skipped("flake8"),
            "bandit": _skipped("bandit"),
            "eslint": _skipped("eslint"),
            "golangci_lint": run_golangci_lint(code=code, filename=filename),
        }

    # Rust
    if lang == "rust" and name.endswith(".rs"):
        return {
            "flake8": _skipped("flake8"),
            "bandit": _skipped("bandit"),
            "eslint": _skipped("eslint"),
            "cargo_clippy": run_cargo_clippy(code=code, filename=filename),
        }

    # Default: explicitly skip everything we know about.
    return {
        "flake8": _skipped("flake8"),
        "bandit": _skipped("bandit"),
        "eslint": _skipped("eslint"),
        "javac": _skipped("javac"),
        "dotnet_format": _skipped("dotnet_format"),
        "golangci_lint": _skipped("golangci_lint"),
        "cargo_clippy": _skipped("cargo_clippy"),
    }


def run_javac(*, code: str, filename: str) -> dict[str, Any]:
    tool = "javac"
    if not (filename or "").lower().endswith(".java"):
        return _skipped(tool)
    if not _which("javac"):
        return _skipped(
            tool, reason="javac not found"
        )  # javac requires that a public top-level class matches the filename.
    # Always compile from a temp file that preserves the original basename.
    base = os.path.basename(filename) or "Main.java"

    with tempfile.TemporaryDirectory(prefix="code_review_agent_javac_") as tmp:
        path = os.path.join(tmp, base)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)

        # Best-effort warnings as errors; some JDKs may not support all -Xlint keys.
        cmd = [
            "javac",
            "-Xlint:all",
            "-Werror",
            "-Xdiags:verbose",
            path,
        ]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError as e:
            return _skipped(tool, reason=str(e))

        return {
            "tool": tool,
            "exit_code": p.returncode,
            "stdout": (p.stdout or "").strip(),
            "stderr": (p.stderr or "").strip(),
            "tool_error": bool(p.returncode != 0),
            "filename": base,
        }


def run_dotnet_format(*, code: str, filename: str) -> dict[str, Any]:
    tool = "dotnet_format"
    if not (filename or "").lower().endswith(".cs"):
        return _skipped(tool)
    if not _which("dotnet"):
        return _skipped(tool, reason="dotnet not found")

    # dotnet-format works on a project/solution. We'll run `dotnet format --verify-no-changes`
    # against a minimal temp project containing the provided file.
    with tempfile.TemporaryDirectory(prefix="code_review_agent_dotnet_") as tmp:
        proj_dir = os.path.join(tmp, "proj")
        os.makedirs(proj_dir, exist_ok=True)
        csproj = os.path.join(proj_dir, "proj.csproj")
        with open(csproj, "w", encoding="utf-8", newline="\n") as f:
            f.write(
                '<Project Sdk="Microsoft.NET.Sdk">\n'
                "  <PropertyGroup>\n"
                "    <TargetFramework>net8.0</TargetFramework>\n"
                "  </PropertyGroup>\n"
                "</Project>\n"
            )

        code_path = os.path.join(proj_dir, os.path.basename(filename) or "Program.cs")
        with open(code_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)

        cmd = ["dotnet", "format", csproj, "--verify-no-changes", "--severity", "warn"]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, cwd=proj_dir)
        except FileNotFoundError as e:
            return _skipped(tool, reason=str(e))

        return {
            "tool": tool,
            "exit_code": p.returncode,
            "stdout": (p.stdout or "").strip()[:4000],
            "stderr": (p.stderr or "").strip()[:4000],
            "tool_error": bool(p.returncode != 0),
        }


def run_golangci_lint(*, code: str, filename: str) -> dict[str, Any]:
    tool = "golangci_lint"
    if not (filename or "").lower().endswith(".go"):
        return _skipped(tool)
    if not _which("golangci-lint"):
        return _skipped(tool, reason="golangci-lint not found")

    with tempfile.TemporaryDirectory(prefix="code_review_agent_go_") as tmp:
        mod_dir = os.path.join(tmp, "mod")
        os.makedirs(mod_dir, exist_ok=True)
        # minimal module so golangci-lint doesn't complain
        with open(os.path.join(mod_dir, "go.mod"), "w", encoding="utf-8", newline="\n") as f:
            f.write("module example.com/tmp\n\ngo 1.21\n")

        src_path = os.path.join(mod_dir, os.path.basename(filename) or "main.go")
        with open(src_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)

        cmd = [
            "golangci-lint",
            "run",
            "--out-format",
            "json",
            "--disable-all",
            "--enable",
            "govet",
            "--enable",
            "staticcheck",
            "--enable",
            "errcheck",
            "--enable",
            "ineffassign",
        ]

        try:
            p = subprocess.run(cmd, capture_output=True, text=True, cwd=mod_dir)
        except FileNotFoundError as e:
            return _skipped(tool, reason=str(e))

        stdout = (p.stdout or "").strip()
        data: Any = {}
        if stdout:
            try:
                data = json.loads(stdout)
            except json.JSONDecodeError:
                data = {"raw": stdout[:4000]}

        return {
            "tool": tool,
            "exit_code": p.returncode,
            "result": data,
            "stderr": (p.stderr or "").strip()[:4000],
            # golangci-lint returns 1 when issues found
            "tool_error": bool(p.returncode not in (0, 1)),
        }


def run_cargo_clippy(*, code: str, filename: str) -> dict[str, Any]:
    tool = "cargo_clippy"
    if not (filename or "").lower().endswith(".rs"):
        return _skipped(tool)
    if not _which("cargo"):
        return _skipped(tool, reason="cargo not found")

    with tempfile.TemporaryDirectory(prefix="code_review_agent_rust_") as tmp:
        proj_dir = os.path.join(tmp, "proj")
        src_dir = os.path.join(proj_dir, "src")
        os.makedirs(src_dir, exist_ok=True)

        with open(os.path.join(proj_dir, "Cargo.toml"), "w", encoding="utf-8", newline="\n") as f:
            f.write('[package]\nname = "tmp"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\n')
        with open(os.path.join(src_dir, "lib.rs"), "w", encoding="utf-8", newline="\n") as f:
            f.write(code)

        cmd = ["cargo", "clippy", "--message-format", "json", "--", "-D", "warnings"]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, cwd=proj_dir)
        except FileNotFoundError as e:
            return _skipped(tool, reason=str(e))

        # clippy emits a stream of JSON objects, one per line.
        messages: list[Any] = []
        stdout = (p.stdout or "").strip()
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                # ignore non-json lines
                continue

        return {
            "tool": tool,
            "exit_code": p.returncode,
            "messages": messages,
            "stderr": (p.stderr or "").strip()[:4000],
            # strict clippy returns non-zero on warnings with -D warnings
            "tool_error": bool(p.returncode != 0 and not messages),
        }
