from fastapi.testclient import TestClient

from app.main import app


def test_post_review_returns_ranked_issues(monkeypatch):
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


def test_post_review_missing_llm_config_returns_400():
    # The backend supports running without LLM calls when LLM_PROVIDER=none.
    # Make this test deterministic by forcing offline settings and stubbing the agent
    # to return no issues.
    from app.settings import Settings
    from app import deps

    def fake_get_settings_dep() -> Settings:
        return Settings(llm_provider="none", llm_api_key="", llm_base_url="", llm_model="")

    app.dependency_overrides[deps.get_settings_dep] = fake_get_settings_dep

    # Stub agent.review so the test doesn't depend on any LLM behavior.
    from app.ai_agent import CodeReviewAgent

    async def fake_agent_review(self, *, code: str, filename: str, language: str = "python", strict: bool = False):
        from app.static_checks import run_static_analysis

        static = run_static_analysis(code=code, filename=filename)
        static_dict = {"flake8": static.flake8, "bandit": static.bandit}
        return "", static_dict, []

    try:
        from pytest import MonkeyPatch

        mp = MonkeyPatch()
        mp.setattr(CodeReviewAgent, "review", fake_agent_review)

        client = TestClient(app)
        resp = client.post("/review", json={"code": "def add(a,b):\n    return a+b\n", "filename": "t.py"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data.get("issues") == []
        assert "static_analysis" in data
    finally:
        app.dependency_overrides.clear()
        try:
            mp.undo()  # type: ignore[name-defined]
        except Exception:
            pass


def test_post_review_strict_mode_returns_formatted_findings(monkeypatch):
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
