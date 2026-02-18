from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FormatResult:
    formatted_code: str
    formatter: str
    changed: bool


class FormatterUnavailableError(RuntimeError):
    pass


def _run(cmd: list[str], *, timeout_s: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )


def _normalize_language(language: str | None) -> str:
    lang = (language or "").strip().lower()
    aliases = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "c#": "csharp",
        "csharp": "csharp",
        "golang": "go",
    }
    return aliases.get(lang, lang)


def _ext_for_language(lang: str) -> str:
    return {
        "python": "py",
        "javascript": "js",
        "typescript": "ts",
        "java": "java",
        "csharp": "cs",
        "go": "go",
        "rust": "rs",
    }.get(lang, "txt")


def _pick_python_formatter() -> tuple[str, list[str]]:
    # Prefer Black if available, else autopep8.
    black = _run(["black", "--version"])
    if black.returncode == 0:
        return "black", ["black", "-q", "-"]

    autopep8 = _run(["autopep8", "--version"])
    if autopep8.returncode == 0:
        return "autopep8", ["autopep8", "-"]

    raise FormatterUnavailableError("No Python formatter available (install black or autopep8)")


def format_code(*, code: str, language: str | None, filename: str | None = None) -> FormatResult:
    """Format code for a language.

    Contract:
    - Input: code string + optional language and filename
    - Output: formatted code (may equal input)
    - Errors:
      - FormatterUnavailableError when no formatter is installed
      - RuntimeError for unexpected formatter failures

    Notes:
    - For JS/TS we use Prettier (stdin) and infer parser from language.
    - For Java we use google-java-format (requires the CLI installed and available on PATH).
    - For Go we use gofmt.
    - For Rust we use rustfmt.
    - For C# we try dotnet format (file-based) if available; if not, we raise unavailable.
    """

    lang = _normalize_language(language)

    if lang == "python":
        formatter, cmd = _pick_python_formatter()
        proc = subprocess.run(cmd, input=code, text=True, capture_output=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "Python formatter failed")
        out = proc.stdout
        return FormatResult(formatted_code=out, formatter=formatter, changed=out != code)

    if lang in {"javascript", "typescript"}:
        # Prettier auto-chooses parser by file extension, but for stdin we set it.
        parser = "babel" if lang == "javascript" else "typescript"
        proc = subprocess.run(
            ["prettier", "--parser", parser],
            input=code,
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            raise FormatterUnavailableError(proc.stderr.strip() or "Prettier failed. Is it installed?")
        out = proc.stdout
        return FormatResult(formatted_code=out, formatter="prettier", changed=out != code)

    if lang == "java":
        # google-java-format only works on files.
        which = _run(["google-java-format", "--version"])
        if which.returncode != 0:
            raise FormatterUnavailableError("google-java-format not found on PATH")

        ext = _ext_for_language(lang)
        with tempfile.TemporaryDirectory() as td:
            fp = Path(td) / (filename or f"Input.{ext}")
            fp.write_text(code, encoding="utf-8")
            proc = _run(["google-java-format", "-i", str(fp)])
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip() or "google-java-format failed")
            out = fp.read_text(encoding="utf-8")
            return FormatResult(formatted_code=out, formatter="google-java-format", changed=out != code)

    if lang == "go":
        which = _run(["gofmt", "-w", "--help"])  # gofmt has no version on some installs
        if which.returncode != 0:
            raise FormatterUnavailableError("gofmt not found on PATH")
        proc = subprocess.run(["gofmt"], input=code, text=True, capture_output=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "gofmt failed")
        out = proc.stdout
        return FormatResult(formatted_code=out, formatter="gofmt", changed=out != code)

    if lang == "rust":
        which = _run(["rustfmt", "--version"])
        if which.returncode != 0:
            raise FormatterUnavailableError("rustfmt not found on PATH")
        # rustfmt accepts stdin only with special flags; easiest is file-based.
        with tempfile.TemporaryDirectory() as td:
            fp = Path(td) / (filename or f"main.{_ext_for_language(lang)}")
            fp.write_text(code, encoding="utf-8")
            proc = _run(["rustfmt", str(fp)])
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip() or "rustfmt failed")
            out = fp.read_text(encoding="utf-8")
            return FormatResult(formatted_code=out, formatter="rustfmt", changed=out != code)

    if lang == "csharp":
        # dotnet format is project-based; without a solution it can’t reliably format.
        # For now, we treat it as unavailable unless a solution context exists.
        raise FormatterUnavailableError(
            "C# formatting requires a project/solution context (dotnet format). Not supported for single-file stdin yet."
        )

    # Fallback: trim trailing whitespace + ensure newline at EOF.
    formatted = "\n".join([re.sub(r"[ \t]+$", "", ln) for ln in code.splitlines()])
    if code.endswith("\n"):
        formatted += "\n"
    else:
        formatted += "\n" if formatted else ""

    return FormatResult(formatted_code=formatted, formatter="basic", changed=formatted != code)
