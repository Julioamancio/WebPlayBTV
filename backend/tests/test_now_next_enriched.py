from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_now_basic_structure():
    r = client.get("/catalog/now")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        item = data[0]
        assert "tvg_id" in item
        assert "name" in item
        assert "logo" in item
        assert "current" in item
        assert "next" in item


def test_now_with_time_filter():
    r = client.get("/catalog/now", params={"time": "2025-01-01T08:30:00Z"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # Pelo menos um canal deve ter current ou next definido
    assert any((it.get("current") is not None or it.get("next") is not None) for it in data)


def test_next_basic_structure():
    r = client.get("/catalog/next")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        item = data[0]
        assert "tvg_id" in item
        assert "name" in item
        assert "logo" in item
        assert "next" in item


def test_enriched_channels_basic():
    r = client.get("/catalog/channels/enriched")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        ch = data[0]
        # Campos base
        for key in ["name", "url", "tvg_id", "group", "logo"]:
            assert key in ch
        # epg pode ser None ou objeto
        assert "epg" in ch


def test_enriched_channels_include_now():
    r = client.get(
        "/catalog/channels/enriched",
        params={"include_now": True, "time": "2025-01-01T08:30:00Z"},
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # Pelo menos um item deve conter current ou next
    assert any((it.get("current") is not None or it.get("next") is not None) for it in data)

