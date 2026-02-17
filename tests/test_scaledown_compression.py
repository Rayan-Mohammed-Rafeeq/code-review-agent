"""Tests for ScaleDown compression integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from app.scaledown_compression import compress_with_scaledown


def test_no_api_key_returns_original_prompt(monkeypatch):
    monkeypatch.delenv("SCALEDOWN_API_KEY", raising=False)
    monkeypatch.delenv("SCALEDOWN_ENABLED", raising=False)
    original = "This is my review prompt"
    out, used = compress_with_scaledown(original)
    assert out == original
    assert used is False


def test_scaledown_disabled_env_var_forces_noop(monkeypatch):
    monkeypatch.setenv("SCALEDOWN_API_KEY", "k")
    monkeypatch.setenv("SCALEDOWN_ENABLED", "false")

    # Even if ScaleDown would succeed, we should never call it when disabled.
    with patch("httpx.Client") as client_cls:
        out, used = compress_with_scaledown("ORIGINAL")
        client_cls.assert_not_called()

    assert out == "ORIGINAL"
    assert used is False


def test_empty_prompt_returns_empty(monkeypatch):
    monkeypatch.setenv("SCALEDOWN_API_KEY", "k")
    monkeypatch.delenv("SCALEDOWN_ENABLED", raising=False)
    out, used = compress_with_scaledown("")
    assert out == ""
    assert used is False


def test_successful_compression(monkeypatch):
    monkeypatch.setenv("SCALEDOWN_API_KEY", "k")
    monkeypatch.delenv("SCALEDOWN_ENABLED", raising=False)

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"compressed": "COMPRESSED"}

    with patch("httpx.Client") as client_cls:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None
        client.post.return_value = mock_resp
        client_cls.return_value = client

        out, used = compress_with_scaledown("ORIGINAL")

    assert out == "COMPRESSED"
    assert used is True


def test_failure_falls_back(monkeypatch):
    monkeypatch.setenv("SCALEDOWN_API_KEY", "k")
    monkeypatch.delenv("SCALEDOWN_ENABLED", raising=False)

    with patch("httpx.Client") as client_cls:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None
        client.post.side_effect = httpx.ConnectError("nope")
        client_cls.return_value = client

        out, used = compress_with_scaledown("ORIGINAL")

    assert out == "ORIGINAL"
    assert used is False
