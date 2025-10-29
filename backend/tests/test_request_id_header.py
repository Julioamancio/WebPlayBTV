from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_request_id_generated_on_health():
    r = client.get("/health")
    assert r.status_code == 200
    rid = r.headers.get("X-Request-ID")
    assert rid is not None and isinstance(rid, str) and len(rid) > 0


def test_request_id_preserved_when_sent_by_client():
    custom_id = "cli-req-123"
    r = client.get("/health", headers={"X-Request-ID": custom_id})
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == custom_id

