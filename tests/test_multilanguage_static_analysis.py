import os

from fastapi.testclient import TestClient

from app.main import app


def _offline():
    os.environ["LLM_PROVIDER"] = "none"
    os.environ.pop("LLM_API_KEY", None)
    os.environ.pop("LLM_BASE_URL", None)
    os.environ.pop("LLM_MODEL", None)


def test_v2_review_static_analysis_shapes_for_all_languages():
    _offline()
    client = TestClient(app)

    cases = [
        ("python", "x.py", "def f():\n    return 1\n"),
        ("javascript", "x.js", "console.log('hi')\n"),
        ("typescript", "x.ts", "const x: number = 1\n"),
        ("java", "X.java", "class X { int x = 1; }\n"),
        ("csharp", "X.cs", "class X { static void Main(){} }\n"),
        ("go", "x.go", "package main\nfunc main(){}\n"),
        ("rust", "x.rs", "pub fn f() { }\n"),
    ]

    for language, filename, code in cases:
        r = client.post(
            "/v2/review/file?strict=false",
            json={"code": code, "language": language, "filename": filename},
        )
        assert r.status_code == 200, (language, r.text)
        body = r.json()
        static = body.get("static_analysis") or {}
        assert isinstance(static, dict)

        # Always present
        assert "flake8" in static
        assert "bandit" in static
        assert "eslint" in static

        # Language-specific keys should also always be present (skipped when not applicable).
        assert "javac" in static
        assert "dotnet_format" in static
        assert "golangci_lint" in static
        assert "cargo_clippy" in static


def test_language_specific_tool_is_not_missing_when_applies():
    _offline()
    client = TestClient(app)

    r = client.post(
        "/v2/review/file?strict=false",
        json={"code": "class X {}\n", "language": "java", "filename": "X.java"},
    )
    assert r.status_code == 200
    static = r.json().get("static_analysis") or {}
    assert "javac" in static
    assert isinstance(static["javac"], dict)
