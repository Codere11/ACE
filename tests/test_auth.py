from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_login_success_admin():
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    data = r.json()
    assert "token" in data
    assert data["user"]["role"] == "admin"


def test_login_fail():
    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_me_requires_token():
    r = client.get("/api/auth/me")
    assert r.status_code == 401
