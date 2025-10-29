from fastapi.testclient import TestClient
from app.main import app
from app.db import create_db_and_tables


create_db_and_tables()
client = TestClient(app)


def _login_token():
    r = client.post("/auth/login", json={"username": "admin@example.com", "password": "admin123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_licenses_summary_header_and_payload_consistency():
    token = _login_token()
    # Garante ao menos uma licença ativa
    r_create = client.post("/licenses/create", headers={"Authorization": f"Bearer {token}"})
    assert r_create.status_code == 200

    r = client.get("/licenses/summary", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "X-Capacity-Remaining" in r.headers
    assert r.headers["X-Capacity-Remaining"].isdigit()

    data = r.json()
    # Checagens básicas de estrutura
    for key in [
        "active_licenses",
        "inactive_licenses",
        "by_plan_active",
        "devices_per_license",
        "devices_allowed_total",
        "devices_count",
        "devices_remaining_total",
        "limit_enabled",
    ]:
        assert key in data

    # Header deve ser consistente com payload
    assert int(r.headers["X-Capacity-Remaining"]) == int(data["devices_remaining_total"])


def test_licenses_summary_metrics_exposed():
    token = _login_token()
    # Dispara o endpoint para registrar métrica
    r = client.get("/licenses/summary", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

    # Métricas devem conter user_capacity_remaining com contexto licenses_summary
    m = client.get("/metrics")
    assert m.status_code == 200
    text = m.text
    assert "user_capacity_remaining" in text
    assert 'context="licenses_summary"' in text

