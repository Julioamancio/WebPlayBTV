from fastapi.testclient import TestClient
from app.main import app
from app.db import create_db_and_tables


create_db_and_tables()
client = TestClient(app)


def _login_token():
    r = client.post("/auth/login", json={"username": "admin@example.com", "password": "admin123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_licenses_rules_includes_header():
    token = _login_token()
    r = client.get("/licenses/rules", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "X-Capacity-Remaining" in r.headers
    assert r.headers["X-Capacity-Remaining"].isdigit()

