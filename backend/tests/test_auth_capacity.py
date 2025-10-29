from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.config import DEVICES_PER_LICENSE
from app.db import engine, create_db_and_tables
from app.models import License, Device
from app.routers import auth as auth_router


client = TestClient(app)
# Garantir que as tabelas existem para os testes que usam DB
create_db_and_tables()


def test_login_returns_capacity_payload_for_fake_user():
    # Cleanup de possíveis licenças/dispositivos do admin de execuções anteriores
    with Session(engine) as session:
        from sqlmodel import select
        for d in session.exec(select(Device).where(Device.owner_username == "admin@example.com")).all():
            session.delete(d)
        for l in session.exec(select(License).where(License.owner_username == "admin@example.com")).all():
            session.delete(l)
        session.commit()

    r = client.post(
        "/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data and isinstance(data["access_token"], str)
    assert "capacity" in data and isinstance(data["capacity"], dict)
    cap = data["capacity"]
    for key in [
        "active_licenses",
        "devices_per_license",
        "devices_allowed",
        "devices_count",
        "devices_remaining",
        "limit_enabled",
    ]:
        assert key in cap

    # estrutura básica e consistência com config
    assert cap["active_licenses"] == 0
    assert cap["devices_count"] == 0
    assert cap["devices_per_license"] == DEVICES_PER_LICENSE
    if DEVICES_PER_LICENSE > 0:
        assert cap["limit_enabled"] is True
        assert cap["devices_allowed"] == 0
        assert cap["devices_remaining"] == 0
    else:
        assert cap["limit_enabled"] is False


def test_login_capacity_respects_plan_limits_for_db_user():
    username = "captest@example.com"
    password = "pw123"

    # Registrar usuário persistente via endpoint
    r = client.post(
        "/auth/register",
        json={"username": username, "password": password},
    )
    # Usuário pode já existir de execuções anteriores; aceitar 200 ou 400
    assert r.status_code in (200, 400)

    # Ajustar configuração usada pelo router de auth (monkeypatch em módulo)
    auth_router.DEVICES_PER_LICENSE = 2
    auth_router.LICENSE_PLAN_DEVICE_LIMITS = {"gold": 5}

    # Limpar estado prévio e criar licença ativa com plano + um dispositivo
    with Session(engine) as session:
        # cleanup de possíveis registros existentes
        from sqlmodel import select
        for d in session.exec(select(Device).where(Device.owner_username == username)).all():
            session.delete(d)
        for l in session.exec(select(License).where(License.owner_username == username)).all():
            session.delete(l)
        session.commit()

        lic = License(owner_username=username, status="active", plan="gold")
        session.add(lic)
        session.commit()
        session.refresh(lic)

        dev = Device(
            fingerprint="cap-fp-1",
            name="Device 1",
            platform="test",
            owner_username=username,
        )
        session.add(dev)
        session.commit()

    # Login do usuário persistente e validação da capacidade
    r2 = client.post("/auth/login", json={"username": username, "password": password})
    assert r2.status_code == 200
    data = r2.json()
    cap = data["capacity"]
    assert cap["limit_enabled"] is True
    assert cap["devices_per_license"] == 2
    assert cap["active_licenses"] == 1
    assert cap["devices_allowed"] == 5  # plano gold substitui por licença
    assert cap["devices_count"] == 1
    assert cap["devices_remaining"] == 4

