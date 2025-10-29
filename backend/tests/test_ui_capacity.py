from fastapi.testclient import TestClient
from app.main import app
from app.db import create_db_and_tables


create_db_and_tables()
client = TestClient(app)


def test_ui_capacity_serves_html():
    r = client.get("/ui/capacity")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/html")
    assert "Resumo de Capacidade" in r.text

