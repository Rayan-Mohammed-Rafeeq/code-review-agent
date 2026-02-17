import os

from fastapi.testclient import TestClient

from app.main import app


def test_post_review_returns_ranked_issues(monkeypatch):
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["LLM_API_KEY"] = "test"
    os.environ["LLM_BASE_URL"] = "http://test"
    os.environ["LLM_MODEL"] = "test"

    async def fake_review(self, *, compressed_context: str, static_analysis: dict):
        # Unsorted on purpose: should come back ordered by severity then category.
        return [
            {
                "severity": "low",
                "category": "style",
                "description": "nit",
                "suggestion": "format",
            },
            {
                "severity": "high",
                "category": "bug",
                "description": "crash",
                "suggestion": "fix",
            },
            {
                "severity": "high",
                "category": "security",
                "description": "secret",
                "suggestion": "env",
            },
        ]

    # Patch the LLMClient.review method to avoid real HTTP calls.
    from app import llm_client

    async def review_wrapper(self, *, compressed_context: str, static_analysis: dict, review_prompt: str | None = None):
        # Convert dicts to Issue models via the real validation path.
        from app.models import Issue

        raw = await fake_review(self, compressed_context=compressed_context, static_analysis=static_analysis)
        return [Issue.model_validate(x) for x in raw]

    monkeypatch.setattr(llm_client.LLMClient, "review", review_wrapper)

    client = TestClient(app)
    resp = client.post(
        "/review",
        json={"code": "def add(a,b):\n    return a+b\n", "filename": "t.py"},
    )
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert "compressed_context" in data
    assert "static_analysis" in data
    assert "issues" in data

    issues = data["issues"]
    assert issues[0]["severity"] == "high" and issues[0]["category"] == "security"
    assert issues[1]["severity"] == "high" and issues[1]["category"] == "bug"
    assert issues[2]["severity"] == "low" and issues[2]["category"] == "style"


def test_post_review_missing_llm_config_returns_400(client):
    # Use an explicit empty string to ensure Settings reads the missing key even if Pydantic cached env.
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["LLM_API_KEY"] = ""
    # Base URL and model now have defaults, but ensure any inherited env doesn't mask the missing-key case.
    os.environ.pop("LLM_BASE_URL", None)
    os.environ.pop("LLM_MODEL", None)

    r = client.post(
        "/review",
        json={"code": "print('hi')\n", "language": "python", "filename": "x.py", "strict": False},
    )
    assert r.status_code == 400
    assert "LLM is not configured" in r.text
    assert "LLM_API_KEY" in r.text


def test_post_review_offline_mode_succeeds_without_llm_config(client):
    os.environ["LLM_PROVIDER"] = "none"
    os.environ.pop("LLM_API_KEY", None)
    os.environ.pop("LLM_BASE_URL", None)
    os.environ.pop("LLM_MODEL", None)

    r = client.post(
        "/review",
        json={"code": "print('hi')\n", "language": "python", "filename": "x.py", "strict": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["issues"] == []
    assert "static_analysis" in body


def test_post_review_strict_mode_returns_formatted_findings(monkeypatch):
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["LLM_API_KEY"] = "test"
    os.environ["LLM_BASE_URL"] = "http://test"
    os.environ["LLM_MODEL"] = "test"

    async def fake_review(self, *, compressed_context: str, static_analysis: dict):
        return [
            {
                "severity": "medium",
                "category": "style",
                "description": "Unused variable 'x'.",
                "suggestion": "Remove the unused assignment or use the variable.",
            },
            {
                "severity": "high",
                "category": "bug",
                "description": "Function returns a constant regardless of input.",
                "suggestion": "Implement the intended logic or make the constant a named configuration.",
            },
        ]

    from app import llm_client

    async def review_wrapper(self, *, compressed_context: str, static_analysis: dict, review_prompt: str | None = None):
        from app.models import Issue

        raw = await fake_review(self, compressed_context=compressed_context, static_analysis=static_analysis)
        return [Issue.model_validate(x) for x in raw]

    monkeypatch.setattr(llm_client.LLMClient, "review", review_wrapper)

    client = TestClient(app)
    resp = client.post(
        "/review",
        json={"code": "def foo():\n    x = 10\n    return 5\n", "filename": "t.py", "strict": True},
    )
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert "strict_findings" in data
    text = data["strict_findings"]
    assert isinstance(text, str)

    # Exact required header lines and labels.
    assert "Issue 1\nSeverity: " in text
    assert "\nCategory: " in text
    assert "\nProblem: " in text
    assert "\nSuggestion: " in text

    # Ensure blocks are separated and numbering is stable.
    assert "Issue 1" in text
    assert "Issue 2" in text
    assert "\n\nIssue 2" in text

    # Trailing newline (useful for CLI copy/paste friendliness).
    assert text.endswith("\n")


def test_post_review_non_python_language_offline_mode_succeeds(client):
    os.environ["LLM_PROVIDER"] = "none"
    os.environ.pop("LLM_API_KEY", None)
    os.environ.pop("LLM_BASE_URL", None)
    os.environ.pop("LLM_MODEL", None)

    r = client.post(
        "/review",
        json={"code": "console.log('hi')\n", "language": "javascript", "filename": "x.js", "strict": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert "issues" in body
    assert isinstance(body["issues"], list)
    assert "static_analysis" in body
    static = body["static_analysis"]
    assert isinstance(static, dict)
    # For non-python, python-only tools should be skipped.
    assert (static.get("flake8") or {}).get("skipped") is True
    assert (static.get("bandit") or {}).get("skipped") is True


def test_post_review_v2_non_python_language_offline_mode_succeeds(client):
    os.environ["LLM_PROVIDER"] = "none"
    os.environ.pop("LLM_API_KEY", None)
    os.environ.pop("LLM_BASE_URL", None)
    os.environ.pop("LLM_MODEL", None)

    r = client.post(
        "/v2/review/file?strict=false",
        json={"code": "console.log('hi')\n", "language": "javascript", "filename": "x.js"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "issues" in body and isinstance(body["issues"], list)
    assert "score" in body and isinstance(body["score"], dict)
    assert "score" in body["score"]
    assert "counts_by_severity" in body["score"]
    assert "static_analysis" in body and isinstance(body["static_analysis"], dict)
    static = body["static_analysis"]
    assert (static.get("flake8") or {}).get("skipped") is True
    assert (static.get("bandit") or {}).get("skipped") is True

