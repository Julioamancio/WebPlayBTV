from fastapi.testclient import TestClient
from app.main import app
from app.db import create_db_and_tables
from app.services import rate_limit as rl


# Garantir que as tabelas existam (inclui RevokedToken)
create_db_and_tables()
client = TestClient(app)


def _login_tokens():
    r = client.post(
        "/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    assert r.status_code == 200
    data = r.json()
    return data["access_token"], data.get("refresh_token")


def test_login_returns_refresh_token():
    r = client.post(
        "/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "refresh_token" in data
    assert isinstance(data["refresh_token"], str) and len(data["refresh_token"]) > 0


def test_refresh_and_revoke_flow_blocks_subsequent_refresh():
    _, refresh = _login_tokens()
    assert refresh is not None

    # Primeiro refresh deve funcionar
    r1 = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r1.status_code == 200
    data1 = r1.json()
    assert "access_token" in data1 and isinstance(data1["access_token"], str)
    assert "refresh_token" in data1 and isinstance(data1["refresh_token"], str)

    # Revogar o refresh token
    r_rev = client.post("/auth/revoke", json={"refresh_token": refresh})
    assert r_rev.status_code in (200, 204)

    # Novo refresh com o mesmo token deve falhar
    r2 = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 401


def test_refresh_rotation_revokes_old_token_and_allows_new_token():
    # Login para obter refresh inicial
    _, old_refresh = _login_tokens()
    assert old_refresh is not None

    # Chama refresh para rotacionar: deve retornar novo refresh_token
    r_rot = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert r_rot.status_code == 200
    rot_data = r_rot.json()
    assert "access_token" in rot_data and isinstance(rot_data["access_token"], str)
    assert "refresh_token" in rot_data and isinstance(rot_data["refresh_token"], str)
    new_refresh = rot_data["refresh_token"]
    assert new_refresh != old_refresh

    # Tentar usar o refresh antigo deve falhar
    r_old = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert r_old.status_code == 401

    # Usar o refresh novo deve funcionar e pode retornar outro novo refresh
    r_new = client.post("/auth/refresh", json={"refresh_token": new_refresh})
    assert r_new.status_code == 200
    new_data = r_new.json()
    assert "access_token" in new_data and isinstance(new_data["access_token"], str)
    assert "refresh_token" in new_data and isinstance(new_data["refresh_token"], str)


def test_rate_limit_login_blocks_after_threshold():
    # Ativar e configurar limites baixos para o teste
    rl.RATE_LIMIT_ENABLED = True
    rl.RATE_LIMIT_WINDOW_SECONDS = 60
    rl.RATE_LIMIT_LOGIN_PER_WINDOW = 2
    rl._requests.clear()  # limpar estado de janela

    # Duas tentativas dentro da janela devem passar (mesmo com senha errada)
    for _ in range(2):
        r = client.post(
            "/auth/login",
            json={"username": "admin@example.com", "password": "wrong"},
        )
        assert r.status_code in (200, 401)

    # Terceira tentativa deve ser bloqueada por rate limit
    r3 = client.post(
        "/auth/login",
        json={"username": "admin@example.com", "password": "wrong"},
    )
    assert r3.status_code == 429
