from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any, Dict, Optional

logger = logging.getLogger("code_review_agent.firebase")


def _raw_cred_json() -> Optional[str]:
    # Preferred: a single env var holding the entire JSON key.
    raw = (os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") or "").strip()
    if raw:
        return raw

    # Alternate: a file path env var.
    p = (os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE") or "").strip()
    if p and os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None

    # Common default file location in repo root.
    default_path = os.path.join(os.getcwd(), "firebase-service-account.json")
    if os.path.exists(default_path):
        try:
            with open(default_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None

    return None


def _cred_source() -> str:
    """Return a human-friendly description of where creds were loaded from (if any)."""
    if (os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") or "").strip():
        return "env:FIREBASE_SERVICE_ACCOUNT_JSON"
    p = (os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE") or "").strip()
    if p:
        return f"env:FIREBASE_SERVICE_ACCOUNT_FILE({p})"
    default_path = os.path.join(os.getcwd(), "firebase-service-account.json")
    if os.path.exists(default_path):
        return f"file:{default_path}"
    return "missing"


def _looks_like_service_account(info: dict) -> bool:
    # Minimum keys we expect for firebase_admin.credentials.Certificate
    needed = {"type", "project_id", "private_key", "client_email"}
    return needed.issubset(set(info.keys()))


def _format_firebase_exception(e: Exception) -> str:
    # firebase_admin typically raises firebase_admin.exceptions.FirebaseError
    code = getattr(e, "code", None)
    msg = getattr(e, "message", None)
    parts = [e.__class__.__name__]
    if code:
        parts.append(f"code={code}")
    if msg:
        parts.append(f"message={msg}")
    else:
        parts.append(f"detail={str(e)}")
    return " ".join(parts)


@lru_cache(maxsize=1)
def _init_admin() -> bool:
    """Initialize firebase_admin if configured. Returns True if available."""
    try:
        import firebase_admin
        from firebase_admin import credentials

        if firebase_admin._apps:  # type: ignore[attr-defined]
            return True

        raw = _raw_cred_json()
        if not raw:
            # Not configured is a normal local/dev state.
            logger.info("Firebase Admin not configured (no service account). Falling back to demo auth.")
            return False

        info = json.loads(raw)
        if not isinstance(info, dict) or not _looks_like_service_account(info):
            logger.warning(
                "Firebase service account JSON is present but doesn't look like a service account key (source=%s). Falling back to demo auth.",
                _cred_source(),
            )
            return False

        cred = credentials.Certificate(info)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin initialized (project_id=%s, source=%s)", info.get("project_id"), _cred_source())
        return True
    except Exception as e:
        # Surface the root cause for debugging (including CONFIGURATION_NOT_FOUND).
        logger.warning(
            "Firebase Admin initialization failed (%s, source=%s). Falling back to demo auth.",
            _format_firebase_exception(e),
            _cred_source(),
            exc_info=True,
        )
        return False


def verify_firebase_id_token(id_token: str) -> Optional[Dict[str, Any]]:
    """Verify a Firebase ID token.

    Returns the decoded token dict (contains uid, email, etc) or None.
    """
    if not id_token:
        return None

    if not _init_admin():
        return None

    try:
        from firebase_admin import auth

        decoded = auth.verify_id_token(id_token)
        return decoded
    except Exception as e:
        logger.info("Firebase token verification failed (%s). Treating as anonymous.", _format_firebase_exception(e))
        return None
