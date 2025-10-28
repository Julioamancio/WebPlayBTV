from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    username: str
    full_name: str | None = None


# Mini base de usuários para teste (NÃO usar em produção)
FAKE_USERS = {
    "admin@example.com": {
        "username": "admin@example.com",
        "full_name": "Admin",
        "password": "admin123",
    }
}


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserProfile:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    user = FAKE_USERS.get(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")

    return UserProfile(username=user["username"], full_name=user.get("full_name"))


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    user = FAKE_USERS.get(data.username)
    if not user or user["password"] != data.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    token = create_access_token(subject=user["username"])
    return TokenResponse(access_token=token)


@router.post("/logout")
def logout():
    # JWT é stateless; em produção usar blacklist/rota de revogação se necessário
    return {"status": "ok"}


@router.get("/me", response_model=UserProfile)
def me(current_user: UserProfile = Depends(get_current_user)):
    return current_user

