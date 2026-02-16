from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AuthUser:
    username: str


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("utf-8"))


def _sign(secret: str, msg: bytes) -> str:
    return _b64url_encode(hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).digest())


def issue_token(*, username: str, secret: str, ttl_seconds: int = 60 * 60 * 24 * 7) -> str:
    """Issue a simple signed token.

    Format: b64url(payload).b64url(sig)

    This isn't a full JWT implementation, but it's sufficient for a demo/SaaS-like
    UX without adding dependencies.
    """
    now = int(time.time())
    exp = now + int(ttl_seconds)
    payload = ("%s|%s" % (username, exp)).encode("utf-8")
    sig = _sign(secret, payload)
    return "%s.%s" % (_b64url_encode(payload), sig)


def verify_token(*, token: str, secret: str) -> Optional[AuthUser]:
    try:
        payload_b64, sig = token.split(".", 1)
        payload = _b64url_decode(payload_b64)
        expected = _sign(secret, payload)
        if not hmac.compare_digest(expected, sig):
            return None
        username, exp_s = payload.decode("utf-8").split("|", 1)
        if int(exp_s) < int(time.time()):
            return None
        if not username.strip():
            return None
        return AuthUser(username=username)
    except Exception:
        return None


def get_auth_secret() -> str:
    # For real deployments, set AUTH_SECRET. For local dev/tests, use a deterministic
    # default so the UI works out-of-the-box.
    return os.getenv("AUTH_SECRET") or "dev-insecure-secret-change-me"
