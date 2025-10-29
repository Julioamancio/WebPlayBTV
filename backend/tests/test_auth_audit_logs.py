import json
from fastapi.testclient import TestClient
from app.main import app
from app.db import create_db_and_tables


create_db_and_tables()
client = TestClient(app)


def _login():
    rid = "rid-login-123"
    r = client.post(
        "/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 200
    data = r.json()
    return data["access_token"], data.get("refresh_token"), rid


def test_audit_login_contains_request_id():
    token, _, rid = _login()
    # Buscar logs do usuário
    r = client.get(
        "/audit/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    # Deve existir um item com action auth.login e details contendo request_id
    found = False
    for it in items:
        if it.get("action") == "auth.login" and isinstance(it.get("details"), str):
            if f"request_id={rid}" in it["details"]:
                found = True
                break
    assert found


def test_audit_refresh_contains_request_id_and_jti():
    token, refresh, _ = _login()
    rid = "rid-refresh-456"
    r = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh},
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 200
    # Buscar logs do usuário
    r2 = client.get(
        "/audit/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    items = r2.json()
    found = False
    for it in items:
        if it.get("action") == "auth.refresh" and isinstance(it.get("details"), str):
            if f"request_id={rid}" in it["details"] and "jti=" in it["details"]:
                found = True
                break
    assert found


def test_audit_revoke_contains_request_id():
    token, refresh, _ = _login()
    rid = "rid-revoke-789"
    r = client.post(
        "/auth/revoke",
        json={"refresh_token": refresh},
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 200
    # Buscar logs do usuário
    r2 = client.get(
        "/audit/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    items = r2.json()
    found = False
    for it in items:
        if it.get("action") == "auth.revoke" and isinstance(it.get("details"), str):
            if f"request_id={rid}" in it["details"]:
                found = True
                break
    assert found

