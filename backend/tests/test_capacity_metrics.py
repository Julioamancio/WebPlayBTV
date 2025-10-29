from fastapi.testclient import TestClient
from app.main import app
from app.db import create_db_and_tables


create_db_and_tables()
client = TestClient(app)


def _login_token():
    r = client.post("/auth/login", json={"username": "admin@example.com", "password": "admin123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_metrics_include_user_capacity_remaining():
    token = _login_token()
    # Aciona métricas em diferentes contextos
    client.get("/auth/capacity", headers={"Authorization": f"Bearer {token}"})
    client.get("/devices/capacity", headers={"Authorization": f"Bearer {token}"})
    # Busca métricas
    m = client.get("/metrics")
    assert m.status_code == 200
    body = m.text
    # Deve conter o gauge definido
    assert "user_capacity_remaining" in body
    # Deve conter pelo menos um contexto esperado
    assert 'context="auth_capacity"' in body or 'context="devices_capacity"' in body

