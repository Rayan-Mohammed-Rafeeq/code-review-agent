from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow running as: python scripts/history_smoketest.py
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient

from app.main import app


def main() -> int:
    # Ensure we can call /review without external LLM access.
    os.environ.setdefault("LLM_PROVIDER", "none")

    c = TestClient(app)

    r = c.get("/history")
    print("/history(empty)", r.status_code, r.json())

    r = c.post(
        "/review",
        json={"code": "print(123)\n", "language": "python", "filename": "a.py", "strict": False},
    )
    print("/review", r.status_code)
    if r.status_code != 200:
        print(r.text)
        return 1

    r = c.get("/history")
    print("/history(after)", r.status_code, r.json())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
