"""DEPRECATED: ScaleDown is NOT an LLM.

This project uses ScaleDown ONLY for prompt compression via:
    app.scaledown_compression.compress_with_scaledown

Any code that treats ScaleDown as an LLM provider is intentionally disabled.
"""

from __future__ import annotations


class ScaleDownLLMClient:  # pragma: no cover
    def __init__(self, *args, **kwargs):
        raise RuntimeError(
            "ScaleDown is not an LLM provider. Remove ScaleDownLLMClient usage and use the real LLM client "
            "(OpenAI/Gemini/etc.) with prompt compression via app.scaledown_compression.compress_with_scaledown()."
        )
