import os
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_m3u_etag_and_304():
    r1 = client.get("/catalog/m3u")
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag is not None and len(etag) > 0

    r2 = client.get("/catalog/m3u", headers={"If-None-Match": etag})
    assert r2.status_code == 304


def test_epg_global_etag_and_304_no_query():
    r1 = client.get("/catalog/epg")
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag is not None and len(etag) > 0

    r2 = client.get("/catalog/epg", headers={"If-None-Match": etag})
    assert r2.status_code == 304


def test_epg_global_filters_and_pagination():
    # janela conhecida do sample.xml (README usa estes horários como exemplo)
    params = {
        "start": "2025-01-01T08:00:00Z",
        "end": "2025-01-01T09:00:00Z",
        "limit_per_channel": 1,
        "offset_per_channel": 0,
    }
    r1 = client.get("/catalog/epg", params=params)
    assert r1.status_code == 200
    data1 = r1.json()
    assert "programs" in data1 and isinstance(data1["programs"], dict)
    # cada canal não deve exceder o limite
    for ch, items in data1["programs"].items():
        assert len(items) <= params["limit_per_channel"]

    # mesmo filtro com offset alterado
    params2 = dict(params)
    params2["offset_per_channel"] = 1
    r2 = client.get("/catalog/epg", params=params2)
    assert r2.status_code == 200
    data2 = r2.json()
    assert "programs" in data2 and isinstance(data2["programs"], dict)
    for ch, items in data2["programs"].items():
        assert len(items) <= params2["limit_per_channel"]


def test_epg_global_etag_with_query():
    params = {
        "start": "2025-01-01T08:00:00Z",
        "end": "2025-01-01T09:00:00Z",
        "limit_per_channel": 1,
        "offset_per_channel": 0,
    }
    r1 = client.get("/catalog/epg", params=params)
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag is not None and len(etag) > 0

    r2 = client.get("/catalog/epg", params=params, headers={"If-None-Match": etag})
    assert r2.status_code == 304

