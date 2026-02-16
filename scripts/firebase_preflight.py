from __future__ import annotations

import json
import os
from pathlib import Path

import requests


def _load_env_file(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    _load_env_file()
    api_key = (os.getenv("FIREBASE_WEB_API_KEY") or "").strip()
    if not api_key:
        print("FIREBASE_WEB_API_KEY is not set")
        return 2

    def call(name: str, url: str, payload: dict) -> None:
        try:
            r = requests.post(url, json=payload, timeout=20)
        except requests.exceptions.RequestException as e:
            print(f"{name}: request failed: {e.__class__.__name__}: {e}")
            return

        print("=" * 80)
        print(name)
        print("status:", r.status_code)
        try:
            j = r.json()
            print(json.dumps(j, indent=2)[:4000])
        except ValueError:
            print(r.text[:4000])

    base = "https://identitytoolkit.googleapis.com/v1"
    call(
        "createAuthUri (preflight)",
        f"{base}/accounts:createAuthUri?key={api_key}",
        {"identifier": "test@example.com", "continueUri": "http://localhost"},
    )
    call(
        "signInWithPassword (expected INVALID_PASSWORD or EMAIL_NOT_FOUND if configured)",
        f"{base}/accounts:signInWithPassword?key={api_key}",
        {"email": "nobody@example.com", "password": "not-a-real-password", "returnSecureToken": True},
    )
    call(
        "signUp (expected EMAIL_EXISTS or OK if configured)",
        f"{base}/accounts:signUp?key={api_key}",
        {"email": "nobody@example.com", "password": "not-a-real-password", "returnSecureToken": True},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
