from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def _login_token():
    r = client.post("/auth/login", json={"username": "admin@example.com", "password": "admin123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_devices_capacity_includes_header():
    token = _login_token()
    r = client.get("/devices/capacity", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    # Header deve estar presente
    assert "X-Capacity-Remaining" in r.headers
    # Valor deve ser um inteiro representado como string
    assert r.headers["X-Capacity-Remaining"].isdigit()


def test_register_device_includes_header():
    token = _login_token()
    body = {"fingerprint": "hdr-fp-123", "name": "hdr-dev", "platform": "test"}
    r = client.post("/devices/register", json=body, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "X-Capacity-Remaining" in r.headers
    assert r.headers["X-Capacity-Remaining"].isdigit()
    # cleanup do dispositivo recém criado
    dev_id = r.json().get("id")
    if dev_id:
        client.delete(f"/devices/{dev_id}", headers={"Authorization": f"Bearer {token}"})

