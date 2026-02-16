from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional


def _b64url_decode_to_json(segment: str) -> Optional[Dict[str, Any]]:
    try:
        padding = "=" * (-len(segment) % 4)
        raw = base64.urlsafe_b64decode((segment + padding).encode("utf-8"))
        obj = json.loads(raw.decode("utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


@dataclass(frozen=True)
class TokenHints:
    aud: Optional[str]
    iss: Optional[str]
    sub: Optional[str]
    email: Optional[str]
    firebase_project_id: Optional[str]


def get_token_hints(id_token: str) -> Optional[TokenHints]:
    """Parse the *unverified* JWT payload and return safe routing hints.

    This does not verify signatures. It's only for debugging config mismatches like
    CONFIGURATION_NOT_FOUND.
    """
    if not id_token or "." not in id_token:
        return None

    parts = id_token.split(".")
    if len(parts) < 2:
        return None

    payload = _b64url_decode_to_json(parts[1])
    if not payload:
        return None

    aud = payload.get("aud")
    iss = payload.get("iss")
    sub = payload.get("sub")
    email = payload.get("email")

    firebase_project_id = None
    if isinstance(iss, str) and iss.startswith("https://securetoken.google.com/"):
        firebase_project_id = iss.rsplit("/", 1)[-1]

    return TokenHints(
        aud=aud if isinstance(aud, str) else None,
        iss=iss if isinstance(iss, str) else None,
        sub=sub if isinstance(sub, str) else None,
        email=email if isinstance(email, str) else None,
        firebase_project_id=firebase_project_id,
    )
