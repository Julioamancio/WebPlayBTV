import json
import logging
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_logging_includes_request_id_and_basic_fields(caplog):
    caplog.set_level(logging.INFO, logger="webplay.request")
    rid = "rid-abc-123"
    r = client.get("/health", headers={"X-Request-ID": rid})
    assert r.status_code == 200

    records = [rec for rec in caplog.records if rec.name == "webplay.request"]
    assert len(records) > 0
    # Pelo menos um registro deve conter o request_id enviado
    found = False
    for rec in records:
        try:
            data = json.loads(rec.message)
        except Exception:
            continue
        if data.get("request_id") == rid and data.get("path") == "/health":
            # Campos básicos
            assert data.get("method") == "GET"
            assert isinstance(data.get("status"), int)
            assert isinstance(data.get("duration_ms"), int)
            found = True
            break
    assert found

