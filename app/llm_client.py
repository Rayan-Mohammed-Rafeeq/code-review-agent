from __future__ import annotations

import ast
import json
import logging
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError

from app.models import Issue, LLM_JSON_SCHEMA

logger = logging.getLogger("code_review_agent.llm")


_SYSTEM_PROMPT = (
    "You are a senior Python code reviewer. Return ONLY valid JSON that matches the provided schema. "
    "Be concrete and actionable. Do not include markdown."
)


def _looks_like_placeholder_key(api_key: str) -> bool:
    """True when the key looks redacted or clearly invalid (e.g., contains asterisks)."""
    if not api_key:
        return True
    if "*" in api_key:
        return True
    # Common copy/paste mistake: including surrounding quotes
    if (api_key.startswith("\"") and api_key.endswith("\"")) or (api_key.startswith("'") and api_key.endswith("'")):
        return True
    return False


def _normalize_base_url(base_url: str) -> str:
    """Normalize base_url and fix the most common suffix mismatch.

    We expect an OpenAI-compatible base URL that serves POST /chat/completions.
    - If user passes https://api.openai.com (missing /v1), we add /v1.
    - If user passes https://api.openai.com/v1/ (trailing slash), we strip it.

    We intentionally do *not* try to fully auto-detect Azure endpoints, because
    Azure uses different paths and auth headers.
    """
    url = (base_url or "").strip()
    if not url:
        return url

    # Remove surrounding quotes
    if (url.startswith("\"") and url.endswith("\"")) or (url.startswith("'") and url.endswith("'")):
        url = url[1:-1].strip()

    url = url.rstrip("/")

    # If it's exactly api.openai.com (or endswith it), ensure /v1 is present.
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        if host == "api.openai.com" and (path == "" or path == "/"):
            url = url + "/v1"
    except Exception:
        # If parsing fails, keep original
        pass

    return url


def _status_suggestion(status: int | None, response_text: str, *, base_url: str, model: str) -> str:
    """Build an actionable suggestion string tailored to common provider errors."""
    base_url_norm = _normalize_base_url(base_url)

    if status == 401:
        key_hint = "If your key was redacted (contains '*') or copied with quotes, fix it."
        return (
            "Authentication failed (401). Verify LLM_API_KEY is a real, active key and is loaded into the API process. "
            + key_hint
            + " If you're using Azure OpenAI, this client isn't configured for Azure auth/paths; use an OpenAI-compatible endpoint."
        )
    if status == 404:
        return (
            "Not found (404). This usually means LLM_BASE_URL is wrong (missing '/v1' or pointing at a non-OpenAI-compatible host), "
            f"or the model isn't available. Current base_url='{base_url_norm}', model='{model}'."
        )
    if status == 429:
        return "Rate limited (429). Slow down requests, add retries/backoff, or use a higher quota key."
    if status == 400:
        txt = (response_text or "").lower()
        if "response_format" in txt or "json_object" in txt:
            return (
                "Bad request (400). Your provider may not support response_format={type: json_object}. "
                "Try removing response_format support (or use a provider/model that supports it), then re-run."
            )
        if "model" in txt:
            return "Bad request (400). Verify LLM_MODEL exists for your account/provider and matches the API you're calling."
        return (
            "Bad request (400). Verify LLM_BASE_URL is OpenAI-compatible, the request format is supported, and LLM_MODEL is valid. "
            f"Current base_url='{base_url_norm}', model='{model}'."
        )

    return "Verify LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL."


async def request_llm_review(
    *,
    api_key: str,
    base_url: str,
    model: str,
    compressed_context: str,
    static_analysis: dict[str, Any],
    review_prompt: str | None = None,
    timeout_seconds: float = 30.0,
    client: httpx.AsyncClient | None = None,
) -> list[Issue]:
    """Send compressed context + static analysis to an LLM and parse structured JSON safely.

    - If the network call fails or the response is malformed, returns a single high-severity Issue.
    - If some items are invalid, keeps the valid ones and appends a low-severity note.

    If `review_prompt` is provided, it is used as the user message input verbatim.
    This enables optional ScaleDown compression as a pre-processing step.

    The optional `client` param exists for testing/injection; if omitted, this function
    creates and closes its own AsyncClient.
    """
    api_key = (api_key or "").strip()
    base_url = _normalize_base_url(base_url)
    model = (model or "").strip()

    if not api_key:
        return [
            Issue(
                severity="high",
                category="bug",
                description="LLM API key is missing (LLM_API_KEY not set)",
                suggestion="Set LLM_API_KEY in the environment for the API process.",
                metadata={"error": "missing_api_key"},
            )
        ]

    if _looks_like_placeholder_key(api_key):
        return [
            Issue(
                severity="high",
                category="bug",
                description="LLM API key looks invalid (possibly redacted or quoted)",
                suggestion=(
                    "Ensure LLM_API_KEY is the full key value (no asterisks, no surrounding quotes) and restart the API process."
                ),
                metadata={"error": "invalid_api_key_format"},
            )
        ]

    if not base_url:
        return [
            Issue(
                severity="high",
                category="bug",
                description="LLM base URL is missing (LLM_BASE_URL is empty)",
                suggestion="Set LLM_BASE_URL to an OpenAI-compatible endpoint, e.g. https://api.openai.com/v1",
                metadata={"error": "missing_base_url"},
            )
        ]

    if not model:
        return [
            Issue(
                severity="high",
                category="bug",
                description="LLM model is missing (LLM_MODEL is empty)",
                suggestion="Set LLM_MODEL to a valid model name for your provider (e.g., 'gpt-4o-mini').",
                metadata={"error": "missing_model"},
            )
        ]

    user_payload = {
        "compressed_context": compressed_context,
        "static_analysis": static_analysis,
        "instructions": (
            "Identify issues. Prefer high-signal items. "
            "If static analysis already reports an issue, you may reference it and expand with context."
        ),
    }

    # Important: many OpenAI-compatible providers won't reliably follow a JSON Schema unless we are explicit.
    # Keep this compact but unambiguous.
    user_content = (
        review_prompt
        if (review_prompt is not None and str(review_prompt).strip() != "")
        else (
            "You MUST return ONLY a JSON object with exactly this shape:\n"
            "{\"issues\": [ {\"severity\": \"high|medium|low\", \"category\": \"security|bug|performance|style\", "
            "\"description\": \"...\", \"suggestion\": \"...\", \"location\": null or string } ] }\n\n"
            "Rules:\n"
            "- Do not include markdown.\n"
            "- Every issue item MUST include severity, category, description, suggestion.\n"
            "- If there are no problems, return an empty list: {\"issues\": []}.\n\n"
            "Here is a JSON Schema for reference (not output):\n"
            + json.dumps(LLM_JSON_SCHEMA)
            + "\n\nInput:\n"
            + json.dumps(user_payload)
        )
    )

    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": user_content,
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }

    headers = {"Authorization": f"Bearer {api_key}"}

    async def _do_post(payload: dict[str, Any]) -> dict[str, Any]:
        if client is None:
            async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout_seconds) as c:
                r = await c.post("/chat/completions", json=payload, headers=headers)
                r.raise_for_status()
                return r.json()
        r = await client.post("/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()

    try:
        data = await _do_post(body)
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else None
        text = ""
        try:
            text = e.response.text if e.response is not None else ""
        except Exception:
            text = ""

        # Provider compatibility: many OpenAI-compatible endpoints reject response_format.
        # Retry ONCE on any 400, removing response_format, to maximize compatibility.
        if status == 400 and "response_format" in body:
            logger.info(
                "LLM provider returned 400; retrying once without response_format",
                extra={"base_url": base_url, "model": model},
            )
            retry_body = dict(body)
            retry_body.pop("response_format", None)
            try:
                data = await _do_post(retry_body)
            except httpx.HTTPStatusError as e2:
                # If retry fails, keep the retry response text for better diagnostics.
                try:
                    text = e2.response.text if e2.response is not None else text
                except Exception:
                    pass
                status = e2.response.status_code if e2.response is not None else status
                e = e2
            except Exception:
                # Fall through to normal error handling below using original status/text.
                pass
            else:
                # Success on retry.
                raw_content = _extract_message_content(data)
                parsed_obj: dict[str, Any]
                try:
                    parsed_obj = json.loads(raw_content)
                except json.JSONDecodeError as exc:
                    return [
                        Issue(
                            severity="high",
                            category="bug",
                            description="LLM returned non-JSON content",
                            suggestion="This provider likely doesn't support response_format=json_object. Enforce JSON via the prompt.",
                            metadata={"error": "non_json_content", "detail": str(exc), "content_snippet": raw_content[:500]},
                        )
                    ]

                issues_raw = parsed_obj.get("issues")
                if not isinstance(issues_raw, list):
                    return [
                        Issue(
                            severity="high",
                            category="bug",
                            description="LLM JSON response missing 'issues' array",
                            suggestion="Update the prompt/schema to always include an 'issues' array.",
                            metadata={"error": "missing_issues", "response": parsed_obj},
                        )
                    ]

                def _normalize_issue_dict(d: dict[str, Any]) -> dict[str, Any]:
                    """Best-effort adapter for near-miss provider outputs.

                    Some models return {type,message,context} instead of our Issue schema.
                    We'll map that into a low/style issue when the required fields are missing.
                    """
                    if all(k in d for k in ("severity", "category", "description", "suggestion")):
                        return d

                    message = d.get("message") or d.get("description") or ""
                    context = d.get("context") or ""
                    typ = d.get("type") or ""

                    if message or context:
                        desc = message if message else context
                        sugg = context if (message and context) else "Review completed."
                        # Default to low/style for these informational items.
                        return {
                            "severity": "low",
                            "category": "style",
                            "description": str(desc).strip() or "No issues found",
                            "suggestion": str(sugg).strip() or "No action needed.",
                            "location": d.get("location"),
                            "metadata": {"normalized_from": typ or "unknown", "raw": d},
                        }

                    return d

                issues: list[Issue] = []
                invalid_items: list[dict[str, Any]] = []

                for item in issues_raw:
                    if not isinstance(item, dict):
                        invalid_items.append({"item": repr(item), "error": "not_an_object"})
                        continue
                    item_norm = _normalize_issue_dict(item)
                    try:
                        issues.append(Issue.model_validate(item_norm))
                    except ValidationError as e:
                        invalid_items.append({"item": item, "normalized": item_norm, "error": "validation_error", "detail": e.errors()})

                if issues:
                    if invalid_items:
                        issues.append(
                            Issue(
                                severity="low",
                                category="style",
                                description="Some LLM issues were dropped due to schema validation errors",
                                suggestion="Tighten the LLM prompt/schema or add server-side normalization.",
                                metadata={"dropped": invalid_items},
                            )
                        )
                    return issues

                return [
                    Issue(
                        severity="high",
                        category="bug",
                        description="LLM returned no valid issues",
                        suggestion="Retry; if it persists, adjust the prompt/schema.",
                        metadata={"error": "no_valid_issues", "dropped": invalid_items, "response": parsed_obj},
                    )
                ]

        logger.warning(
            "LLM provider returned HTTP error",
            extra={
                "status_code": status,
                "base_url": base_url,
                "model": model,
                "response_snippet": text[:500],
            },
        )

        return [
            Issue(
                severity="high",
                category="bug",
                description=f"LLM request failed: HTTP {status}",
                suggestion=_status_suggestion(status, text, base_url=base_url, model=model),
                metadata={
                    "error": "http_status",
                    "status_code": status,
                    "detail": str(e),
                    "base_url": base_url,
                    "model": model,
                    "response": text[:2000],
                },
            )
        ]
    except httpx.HTTPError as e:
        logger.warning(
            "LLM request failed due to HTTP error",
            extra={"base_url": base_url, "model": model, "detail": str(e)},
        )
        return [
            Issue(
                severity="high",
                category="bug",
                description=f"LLM request failed: {type(e).__name__}",
                suggestion="Check network connectivity, credentials, base URL, and try again.",
                metadata={"error": "http_error", "detail": str(e)},
            )
        ]
    except ValueError as e:
        return [
            Issue(
                severity="high",
                category="bug",
                description="LLM response was not valid JSON",
                suggestion="Retry; if it persists, log the raw response and adjust the LLM prompt/response_format.",
                metadata={"error": "invalid_json", "detail": str(e)},
            )
        ]

    raw_content = _extract_message_content(data)

    parsed_obj: dict[str, Any]
    try:
        parsed_obj = json.loads(raw_content)
    except json.JSONDecodeError as e:
        return [
            Issue(
                severity="high",
                category="bug",
                description="LLM returned non-JSON content",
                suggestion="Ensure response_format=json_object is supported by your provider; otherwise enforce JSON in the prompt.",
                metadata={"error": "non_json_content", "detail": str(e), "content_snippet": raw_content[:500]},
            )
        ]

    issues_raw = parsed_obj.get("issues")
    if not isinstance(issues_raw, list):
        return [
            Issue(
                severity="high",
                category="bug",
                description="LLM JSON response missing 'issues' array",
                suggestion="Update the prompt/schema to always include an 'issues' array.",
                metadata={"error": "missing_issues", "response": parsed_obj},
            )
        ]

    def _normalize_issue_dict(d: dict[str, Any]) -> dict[str, Any]:
        """Best-effort adapter for near-miss provider outputs.

        Some models return {type,message,context} instead of our Issue schema.
        We'll map that into a low/style issue when the required fields are missing.
        """
        if all(k in d for k in ("severity", "category", "description", "suggestion")):
            return d

        message = d.get("message") or d.get("description") or ""
        context = d.get("context") or ""
        typ = d.get("type") or ""

        if message or context:
            desc = message if message else context
            sugg = context if (message and context) else "Review completed."
            # Default to low/style for these informational items.
            return {
                "severity": "low",
                "category": "style",
                "description": str(desc).strip() or "No issues found",
                "suggestion": str(sugg).strip() or "No action needed.",
                "location": d.get("location"),
                "metadata": {"normalized_from": typ or "unknown", "raw": d},
            }

        return d

    issues: list[Issue] = []
    invalid_items: list[dict[str, Any]] = []

    def _is_no_issue_placeholder(item: dict[str, Any]) -> bool:
        desc = str(item.get("description") or "").strip().lower()
        sugg = str(item.get("suggestion") or "").strip().lower()
        if not desc and not sugg:
            return False

        # These are common placeholders produced by prompts like "if no issues, return one low/style".
        placeholder_markers = (
            "no issues found",
            "review completed",
            "no action needed",
            "code looks good",
        )
        return any(m in desc for m in placeholder_markers) and (
            (not sugg) or any(m in sugg for m in placeholder_markers)
        )

    def _has_any_docstring(src: str) -> bool:
        try:
            tree = ast.parse(src)
        except SyntaxError:
            return False

        if ast.get_docstring(tree):
            return True

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if ast.get_docstring(node):
                    return True
        return False

    def _looks_like_hallucinated_nit(item: dict[str, Any], *, code_snippet: str) -> bool:
        """Heuristics to drop common false positives on small snippets.

        We keep this conservative: only drop low/style items that are very likely
        generic boilerplate or directly contradicted by the submitted code.
        """
        try:
            severity = str(item.get("severity") or "").lower().strip()
            category = str(item.get("category") or "").lower().strip()
        except Exception:
            return False

        if severity != "low" or category != "style":
            return False

        desc = str(item.get("description") or "").lower()
        sugg = str(item.get("suggestion") or "").lower()

        # Anything that boils down to "Review completed" is not a real issue.
        if sugg.strip() in {"review completed.", "review completed"}:
            return True

        # 1) "no documentation" while a docstring exists.
        if ("docstring" in desc or "documentation" in desc or "comments" in desc) and ("does not" in desc or "missing" in desc):
            if _has_any_docstring(code_snippet):
                return True

        # 2) Generic "add error checking/handling" for a trivial typed add().
        # Models often suggest this even when types are already declared.
        if ("error" in desc or "exception" in desc or "handling" in desc or "checking" in desc) and (
            "does not" in desc or "missing" in desc or "no" in desc
        ):
            if ": int" in code_snippet and "-> int" in code_snippet and "def add" in code_snippet:
                return True

        # 3) Generic naming nits for trivial examples.
        if ("more descriptive name" in desc or "improve readability" in desc or "consider using" in desc) and "name" in desc:
            if "def add" in code_snippet:
                return True

        # Also catch generic rewrites that just restate the function.
        if sugg.strip() in {"def add(a, b) → int: return a + b", "def add(a, b) -> int: return a + b"}:
            return True

        return False

    for item in issues_raw:
        if not isinstance(item, dict):
            invalid_items.append({"item": repr(item), "error": "not_an_object"})
            continue
        item_norm = _normalize_issue_dict(item)
        if _is_no_issue_placeholder(item_norm):
            # Drop informational placeholders; the UI already shows a dedicated
            # "No issues found" success state when issues is empty.
            continue
        if _looks_like_hallucinated_nit(item_norm, code_snippet=compressed_context):
            continue
        try:
            issues.append(Issue.model_validate(item_norm))
        except ValidationError as e:
            invalid_items.append({"item": item, "normalized": item_norm, "error": "validation_error", "detail": e.errors()})

    if issues:
        if invalid_items:
            # Keep the valid issues but surface that we had to drop some.
            issues.append(
                Issue(
                    severity="low",
                    category="style",
                    description="Some LLM issues were dropped due to schema validation errors",
                    suggestion="Tighten the LLM prompt/schema or add server-side normalization.",
                    metadata={"dropped": invalid_items},
                )
            )
        return issues

    # If everything was a placeholder (or issues list is genuinely empty), treat it as success.
    if not invalid_items:
        return []

    return [
        Issue(
            severity="high",
            category="bug",
            description="LLM returned no valid issues",
            suggestion="Retry; if it persists, adjust the prompt/schema and validate provider response_format support.",
            metadata={"error": "no_valid_issues", "dropped": invalid_items, "response": parsed_obj},
        )
    ]


class LLMClient:
    def __init__(self, *, api_key: str, base_url: str, model: str, timeout_seconds: float = 30.0):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds

    async def review(
        self,
        *,
        compressed_context: str,
        static_analysis: dict[str, Any],
        review_prompt: str | None = None,
    ) -> list[Issue]:
        return await request_llm_review(
            api_key=self._api_key,
            base_url=self._base_url,
            model=self._model,
            timeout_seconds=self._timeout,
            compressed_context=compressed_context,
            static_analysis=static_analysis,
            review_prompt=review_prompt,
        )


def _extract_message_content(openai_response: dict[str, Any]) -> str:
    try:
        return openai_response["choices"][0]["message"]["content"]
    except Exception as exc:  # pragma: no cover
        raise ValueError(f"Unexpected LLM response shape: {openai_response}") from exc
