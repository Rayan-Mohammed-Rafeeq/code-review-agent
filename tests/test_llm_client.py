import json

import httpx
import pytest

from app.llm_client import request_llm_review


def _mock_transport(payload: dict, status_code: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path.endswith("/chat/completions")
        return httpx.Response(status_code, json=payload)

    return httpx.MockTransport(handler)


def _mock_transport_assert_user_content(
    expected_substring: str, payload: dict, status_code: int = 200
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert body["messages"][1]["role"] == "user"
        assert expected_substring in body["messages"][1]["content"]
        return httpx.Response(status_code, json=payload)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_request_llm_review_happy_path():
    llm_content = json.dumps(
        {
            "issues": [
                {
                    "severity": "high",
                    "category": "security",
                    "description": "Hardcoded secret",
                    "suggestion": "Read secrets from environment variables.",
                    "location": "main.py:12",
                }
            ]
        }
    )

    payload = {"choices": [{"message": {"content": llm_content}}]}
    transport = _mock_transport(payload)

    async with httpx.AsyncClient(transport=transport, base_url="https://example.com/v1") as client:
        issues = await request_llm_review(
            api_key="k",
            base_url="https://example.com/v1",
            model="gpt",
            compressed_context="def f(): pass",
            static_analysis={"flake8": {}, "bandit": {}},
            client=client,
        )

    assert len(issues) >= 1
    assert issues[0].severity.value == "high"
    assert issues[0].category.value == "security"


@pytest.mark.asyncio
async def test_request_llm_review_non_json_content():
    payload = {"choices": [{"message": {"content": "not json"}}]}
    transport = _mock_transport(payload)

    async with httpx.AsyncClient(transport=transport, base_url="https://example.com/v1") as client:
        issues = await request_llm_review(
            api_key="k",
            base_url="https://example.com/v1",
            model="gpt",
            compressed_context="x",
            static_analysis={},
            client=client,
        )

    assert len(issues) == 1
    assert issues[0].severity.value == "high"
    assert "non-JSON" in issues[0].description


@pytest.mark.asyncio
async def test_request_llm_review_drops_invalid_items():
    # First item is missing required fields; second one is valid.
    llm_content = json.dumps(
        {
            "issues": [
                {"severity": "medium", "category": "bug"},
                {
                    "severity": "low",
                    "category": "style",
                    "description": "Minor style nit",
                    "suggestion": "Run black/ruff.",
                },
            ]
        }
    )

    payload = {"choices": [{"message": {"content": llm_content}}]}
    transport = _mock_transport(payload)

    async with httpx.AsyncClient(transport=transport, base_url="https://example.com/v1") as client:
        issues = await request_llm_review(
            api_key="k",
            base_url="https://example.com/v1",
            model="gpt",
            compressed_context="x",
            static_analysis={},
            client=client,
        )

    # Should keep the valid one, and append a low-severity note about dropped items.
    assert any(i.description == "Minor style nit" for i in issues)
    assert any("dropped" in (i.metadata or {}) for i in issues)


@pytest.mark.asyncio
async def test_request_llm_review_http_401_has_actionable_suggestion():
    payload = {
        "error": {
            "message": "Incorrect API key provided",
            "type": "invalid_request_error",
            "code": "invalid_api_key",
        }
    }
    transport = _mock_transport(payload, status_code=401)

    async with httpx.AsyncClient(transport=transport, base_url="https://example.com/v1") as client:
        issues = await request_llm_review(
            api_key="sk-not-a-real-key",
            base_url="https://example.com/v1",
            model="gpt",
            compressed_context="x",
            static_analysis={},
            client=client,
        )

    assert len(issues) == 1
    assert issues[0].severity.value == "high"
    assert issues[0].description == "LLM request failed: HTTP 401"
    assert "Authentication failed" in issues[0].suggestion
    assert (issues[0].metadata or {}).get("status_code") == 401


@pytest.mark.asyncio
async def test_request_llm_review_uses_review_prompt_override():
    llm_content = json.dumps(
        {
            "issues": [
                {
                    "severity": "low",
                    "category": "style",
                    "description": "nit",
                    "suggestion": "format",
                }
            ]
        }
    )

    payload = {"choices": [{"message": {"content": llm_content}}]}

    override_prompt = "THIS IS THE OVERRIDDEN REVIEW PROMPT"
    transport = _mock_transport_assert_user_content(override_prompt, payload)

    async with httpx.AsyncClient(transport=transport, base_url="https://example.com/v1") as client:
        issues = await request_llm_review(
            api_key="k",
            base_url="https://example.com/v1",
            model="gpt",
            compressed_context="x",
            static_analysis={},
            review_prompt=override_prompt,
            client=client,
        )

    assert len(issues) == 1
    assert issues[0].description == "nit"


@pytest.mark.asyncio
async def test_request_llm_review_allows_empty_issues_list():
    llm_content = json.dumps({"issues": []})
    payload = {"choices": [{"message": {"content": llm_content}}]}
    transport = _mock_transport(payload)

    async with httpx.AsyncClient(transport=transport, base_url="https://example.com/v1") as client:
        issues = await request_llm_review(
            api_key="k",
            base_url="https://example.com/v1",
            model="gpt",
            compressed_context="def add(a: int, b: int) -> int: return a + b",
            static_analysis={},
            client=client,
        )

    assert issues == []


@pytest.mark.asyncio
async def test_request_llm_review_filters_no_issue_placeholder():
    llm_content = json.dumps(
        {
            "issues": [
                {
                    "severity": "low",
                    "category": "style",
                    "description": "No issues found.",
                    "suggestion": "Review completed.",
                }
            ]
        }
    )
    payload = {"choices": [{"message": {"content": llm_content}}]}
    transport = _mock_transport(payload)

    async with httpx.AsyncClient(transport=transport, base_url="https://example.com/v1") as client:
        issues = await request_llm_review(
            api_key="k",
            base_url="https://example.com/v1",
            model="gpt",
            compressed_context="x",
            static_analysis={},
            client=client,
        )

    assert issues == []


@pytest.mark.asyncio
async def test_request_llm_review_filters_docstring_missing_claim_when_docstring_present():
    llm_content = json.dumps(
        {
            "issues": [
                {
                    "severity": "low",
                    "category": "style",
                    "description": "The function add(a, b) -> int does not include any documentation or comments.",
                    "suggestion": "Add a docstring.",
                }
            ]
        }
    )
    payload = {"choices": [{"message": {"content": llm_content}}]}
    transport = _mock_transport(payload)

    code = 'def add(a: int, b: int) -> int:\n    """Return the sum of two integers."""\n    return a + b\n'

    async with httpx.AsyncClient(transport=transport, base_url="https://example.com/v1") as client:
        issues = await request_llm_review(
            api_key="k",
            base_url="https://example.com/v1",
            model="gpt",
            compressed_context=code,
            static_analysis={},
            client=client,
        )

    assert issues == []


@pytest.mark.asyncio
async def test_request_llm_review_filters_generic_error_handling_nit_for_typed_add():
    llm_content = json.dumps(
        {
            "issues": [
                {
                    "severity": "low",
                    "category": "style",
                    "description": "The function add(a, b) -> int does not include any error checking or handling for non-integer inputs.",
                    "suggestion": "Add type checks.",
                }
            ]
        }
    )
    payload = {"choices": [{"message": {"content": llm_content}}]}
    transport = _mock_transport(payload)

    code = 'def add(a: int, b: int) -> int:\n    """Return the sum of two integers."""\n    return a + b\n'

    async with httpx.AsyncClient(transport=transport, base_url="https://example.com/v1") as client:
        issues = await request_llm_review(
            api_key="k",
            base_url="https://example.com/v1",
            model="gpt",
            compressed_context=code,
            static_analysis={},
            client=client,
        )

    assert issues == []


@pytest.mark.asyncio
async def test_request_llm_review_filters_generic_naming_nit_for_add():
    llm_content = json.dumps(
        {
            "issues": [
                {
                    "severity": "low",
                    "category": "style",
                    "description": "The function add uses a simple and clear name, but it may be beneficial to consider using a more descriptive name to improve readability.",
                    "suggestion": "Review completed.",
                }
            ]
        }
    )
    payload = {"choices": [{"message": {"content": llm_content}}]}
    transport = _mock_transport(payload)

    code = 'def add(a: int, b: int) -> int:\n    """Return the sum of two integers."""\n    return a + b\n'

    async with httpx.AsyncClient(transport=transport, base_url="https://example.com/v1") as client:
        issues = await request_llm_review(
            api_key="k",
            base_url="https://example.com/v1",
            model="gpt",
            compressed_context=code,
            static_analysis={},
            client=client,
        )

    assert issues == []
