"""Tiny OpenRouter smoke test.

Runs one POST to /chat/completions using Settings() (loads .env).
Prints status code + first part of response.

Usage:
  python scripts/openrouter_smoketest.py
"""

from __future__ import annotations

import json

import httpx

from app.settings import get_settings


def main() -> None:
    s = get_settings()
    url = s.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": "Bearer " + (s.llm_api_key or ""),
        "Content-Type": "application/json",
    }

    # Optional OpenRouter attribution headers
    if "openrouter.ai" in (s.llm_base_url or ""):
        if s.openrouter_site_url:
            headers["HTTP-Referer"] = s.openrouter_site_url
        if s.openrouter_app_title:
            headers["X-Title"] = s.openrouter_app_title

    payload = {"model": s.llm_model, "messages": [{"role": "user", "content": "ping"}]}

    try:
        r = httpx.post(url, headers=headers, json=payload, timeout=30.0, follow_redirects=True)
        print("status:", r.status_code)
        print("response_headers:", json.dumps({k: r.headers.get(k) for k in ["retry-after", "x-ratelimit-remaining", "x-ratelimit-reset"]}, indent=2))
        print("body_snippet:", r.text[:500])
    except Exception as exc:
        print("exception:", type(exc).__name__, str(exc))


if __name__ == "__main__":
    main()

