import json
import os
import subprocess
import tempfile

import pytest

from app.static_checks import run_static_analysis, run_static_analysis_on_file


def test_static_checks_return_shapes():
    code = "def add(a,b):\n    return a+b\n"
    res = run_static_analysis(code=code, filename="t.py")
    assert "exit_code" in res.flake8
    assert "issues" in res.flake8
    assert "exit_code" in res.bandit
    assert "result" in res.bandit


def test_static_checks_on_file_returns_json_serializable_dict():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "sample.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write("def add(a,b):\n    return a+b\n")

        out = run_static_analysis_on_file(path)

    assert set(out.keys()) == {"metadata", "flake8", "bandit"}
    assert out["metadata"]["path"].lower().endswith("sample.py")
    assert "scanned_at" in out["metadata"]
    assert out["flake8"]["tool"] == "flake8"
    assert out["bandit"]["tool"] == "bandit"

    # Must be JSON serializable
    json.dumps(out)


def test_static_checks_on_file_requires_py_extension():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "sample.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("hi")

        with pytest.raises(ValueError):
            run_static_analysis_on_file(path)


def test_static_checks_flags_undefined_name_typo():
    res = run_static_analysis(code='prin("hello")\n', filename="input.py")
    issues = res.flake8.get("issues") or []
    assert issues, "Expected at least one static-analysis issue for undefined name"
    assert any(i.get("code") == "F821" for i in issues)


def test_flake8_parsing_windows_drive_letter_paths(monkeypatch):
    from app.static_checks import run_static_analysis

    class _P:
        def __init__(self) -> None:
            self.returncode = 1
            self.stdout = r"C:\\tmp\\input.py|1|1|F821|undefined name 'prin'\n"
            self.stderr = ""

    def _fake_run(*args, **kwargs):
        return _P()

    monkeypatch.setattr(subprocess, "run", _fake_run)

    res = run_static_analysis(code='prin("hello")\n', filename="input.py")
    issues = res.flake8.get("issues") or []
    assert any(i.get("code") == "F821" for i in issues)
