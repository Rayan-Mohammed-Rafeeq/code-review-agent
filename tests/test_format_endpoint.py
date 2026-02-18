from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_format_endpoint_unknown_language_basic_formatter() -> None:
    client = TestClient(app)

    resp = client.post(
        "/v2/format",
        json={
            "code": "a=1  \n\n",
            "language": "unknownlang",
            "filename": "x.unknownlang",
        },
    )

    # basic formatter should always be available
    assert resp.status_code == 200
    data = resp.json()
    assert data["formatter"] == "basic"
    assert "a=1" in data["code"]
