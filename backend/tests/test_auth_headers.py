from fastapi.testclient import TestClient
from app.main import app
from app.db import create_db_and_tables


# Garantir que as tabelas existam para endpoints que consultam o DB
create_db_and_tables()

client = TestClient(app)


def _login_token():
    r = client.post("/auth/login", json={"username": "admin@example.com", "password": "admin123"})
    assert r.status_code == 200
    return r.json()["access_token"], r.headers


def test_auth_capacity_includes_header():
    token, _ = _login_token()
    r = client.get("/auth/capacity", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "X-Capacity-Remaining" in r.headers
    assert r.headers["X-Capacity-Remaining"].isdigit()


def test_login_includes_capacity_header():
    r = client.post("/auth/login", json={"username": "admin@example.com", "password": "admin123"})
    assert r.status_code == 200
    data = r.json()
    assert "capacity" in data
    assert "X-Capacity-Remaining" in r.headers
    # Consistência: header e payload devem refletir o mesmo valor
    assert r.headers["X-Capacity-Remaining"].isdigit()
    assert int(r.headers["X-Capacity-Remaining"]) == int(data["capacity"]["devices_remaining"]) 

