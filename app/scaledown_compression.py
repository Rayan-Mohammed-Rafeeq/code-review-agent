"""ScaleDown prompt compression.

ScaleDown is NOT an LLM. It ONLY compresses prompts.

Public API:
- compress_with_scaledown(prompt: str) -> tuple[str, bool]

Behavior:
- Reads SCALEDOWN_API_KEY from environment.
- If missing/empty, returns (prompt, False).
- On any ScaleDown failure, returns (prompt, False).
"""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger("code_review_agent.scaledown")

_SCALEDOWN_URL = "https://api.scaledown.xyz/compress/raw/"
_TIMEOUT_SECONDS = 10.0


def compress_with_scaledown(prompt: str) -> tuple[str, bool]:
    """Compress the given prompt using ScaleDown.

    Args:
        prompt: Full prompt text to compress.

    Returns:
        (compressed_prompt, True) on success
        (original_prompt, False) on any failure or if API key is missing
    """
    api_key = (os.getenv("SCALEDOWN_API_KEY") or "").strip()
    if not api_key:
        return prompt, False

    if not prompt:
        return prompt, False

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "context": "Compress a code review prompt",
        "prompt": prompt,
        "scaledown": {"rate": "auto"},
    }

    try:
        with httpx.Client(timeout=_TIMEOUT_SECONDS, follow_redirects=True) as client:
            resp = client.post(_SCALEDOWN_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        compressed = data.get("compressed") or data.get("result")
        if not isinstance(compressed, str) or not compressed.strip():
            return prompt, False

        return compressed, True
    except Exception as exc:
        logger.debug("ScaleDown compression failed", extra={"error": type(exc).__name__, "detail": str(exc)})
        return prompt, False
