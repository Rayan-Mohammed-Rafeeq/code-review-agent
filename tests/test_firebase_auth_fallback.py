from fastapi.testclient import TestClient

from app.main import app


def test_configz_includes_firebase_status_fields():
    client = TestClient(app)
    r = client.get("/configz")
    assert r.status_code == 200
    data = r.json()
    assert "firebase" in data
    assert "credential_source" in data["firebase"]
    assert "initialized" in data["firebase"]
    # In tests we don't configure Firebase by default.
    assert data["firebase"]["initialized"] in (False, True)


def test_firebase_debug_endpoint_available_without_auth():
    client = TestClient(app)
    r = client.get("/auth/firebase_debug")
    assert r.status_code == 200
    payload = r.json()
    assert "firebase" in payload
    assert "token_hints" in payload
