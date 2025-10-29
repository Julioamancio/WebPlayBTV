from fastapi.testclient import TestClient
from app.main import app
from app.db import create_db_and_tables


create_db_and_tables()
client = TestClient(app)


def test_ui_catalog_serves_html():
    r = client.get("/ui/catalog")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/html")
    assert "Catálogo de Canais" in r.text


def test_ui_devices_serves_html():
    r = client.get("/ui/devices")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/html")
    assert "Meus Dispositivos" in r.text


def test_ui_audit_serves_html():
    r = client.get("/ui/audit")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/html")
    assert "Auditoria" in r.text


def test_ui_login_serves_html():
    r = client.get("/ui/login")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/html")
    assert "Login" in r.text


def test_ui_home_serves_html():
    r = client.get("/ui/home")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/html")
    assert "Current playlist expires" in r.text
