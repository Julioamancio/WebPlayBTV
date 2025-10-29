from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from app.config import DEVICES_PER_LICENSE, LICENSE_PLAN_DEVICE_LIMITS
from app.db import get_session
from app.models_auth import UserAccount, RevokedToken
from app.models import License, Device, AuditLog
from passlib.context import CryptContext
from app.observability import USER_CAPACITY_REMAINING
import uuid


router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=True)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    username: str
    password: str


class CapacitySummary(BaseModel):
    active_licenses: int
    devices_per_license: int
    devices_allowed: int
    devices_count: int
    devices_remaining: int
    limit_enabled: bool


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    capacity: CapacitySummary
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None


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


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    payload = {"sub": subject, "type": "refresh", "exp": expire, "jti": jti}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> UserProfile:
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
    # Try DB first
    db_user = session.exec(select(UserAccount).where(UserAccount.username == username)).first()
    if db_user:
        return UserProfile(username=db_user.username, full_name=db_user.full_name)
    # Fallback to fake user
    user = FAKE_USERS.get(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    return UserProfile(username=user["username"], full_name=user.get("full_name"))


@router.post("/login", response_model=LoginResponse)
def login(
    request: Request,
    data: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
):
    # Try DB user first
    db_user = session.exec(select(UserAccount).where(UserAccount.username == data.username)).first()
    if db_user:
        if not pwd_context.verify(data.password, db_user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
        token = create_access_token(subject=db_user.username)
        refresh = create_refresh_token(subject=db_user.username)
        # Compute capacity summary for this user
        per_license = int(DEVICES_PER_LICENSE)
        limit_enabled = per_license > 0
        active_list = session.exec(
            select(License).where(
                License.owner_username == db_user.username,
                License.status == "active",
            )
        ).all()
        active_licenses = len(active_list)
        devices_count = len(
            session.exec(
                select(Device).where(Device.owner_username == db_user.username)
            ).all()
        )
        if limit_enabled:
            if LICENSE_PLAN_DEVICE_LIMITS:
                devices_allowed = 0
                for lic in active_list:
                    plan = getattr(lic, "plan", None)
                    devices_allowed += int(LICENSE_PLAN_DEVICE_LIMITS.get(plan, per_license))
            else:
                devices_allowed = active_licenses * per_license
        else:
            devices_allowed = 0
        devices_remaining = max(0, devices_allowed - devices_count) if limit_enabled else 0
        # Header e métrica de capacidade no login para usuário persistente
        if response is not None:
            response.headers["X-Capacity-Remaining"] = str(devices_remaining)
        USER_CAPACITY_REMAINING.labels(db_user.username, "auth_login").set(devices_remaining)
        # Audit: login bem-sucedido
        rid = getattr(request.state, "request_id", request.headers.get("X-Request-ID", ""))
        session.add(
            AuditLog(
                actor_username=db_user.username,
                action="auth.login",
                resource="auth",
                resource_id=None,
                details=f"status=success request_id={rid}",
            )
        )
        session.commit()
        return LoginResponse(
            access_token=token,
            refresh_token=refresh,
            capacity=CapacitySummary(
                active_licenses=active_licenses,
                devices_per_license=per_license,
                devices_allowed=devices_allowed,
                devices_count=devices_count,
                devices_remaining=devices_remaining,
                limit_enabled=limit_enabled,
            ),
        )
    # Fallback to fake user for dev/demo
    user = FAKE_USERS.get(data.username)
    if not user or user["password"] != data.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    token = create_access_token(subject=user["username"])
    refresh = create_refresh_token(subject=user["username"])
    # Compute capacity summary for fake user (no licenses/devices persisted)
    per_license = int(DEVICES_PER_LICENSE)
    limit_enabled = per_license > 0
    active_list = session.exec(
        select(License).where(
            License.owner_username == user["username"],
            License.status == "active",
        )
    ).all()
    active_licenses = len(active_list)
    devices_count = len(
        session.exec(
            select(Device).where(Device.owner_username == user["username"])
        ).all()
    )
    if limit_enabled:
        if LICENSE_PLAN_DEVICE_LIMITS:
            devices_allowed = 0
            for lic in active_list:
                plan = getattr(lic, "plan", None)
                devices_allowed += int(LICENSE_PLAN_DEVICE_LIMITS.get(plan, per_license))
        else:
            devices_allowed = active_licenses * per_license
    else:
        devices_allowed = 0
    devices_remaining = max(0, devices_allowed - devices_count) if limit_enabled else 0
    # Header e métrica de capacidade para fake user (dev/demo)
    if response is not None:
        response.headers["X-Capacity-Remaining"] = str(devices_remaining)
    USER_CAPACITY_REMAINING.labels(user["username"], "auth_login").set(devices_remaining)
    # Audit: login bem-sucedido (fake user)
    rid = getattr(request.state, "request_id", request.headers.get("X-Request-ID", ""))
    session.add(
        AuditLog(
            actor_username=user["username"],
            action="auth.login",
            resource="auth",
            resource_id=None,
            details=f"status=success request_id={rid}",
        )
    )
    session.commit()
    return LoginResponse(
        access_token=token,
        refresh_token=refresh,
        capacity=CapacitySummary(
            active_licenses=active_licenses,
            devices_per_license=per_license,
            devices_allowed=devices_allowed,
            devices_count=devices_count,
            devices_remaining=devices_remaining,
            limit_enabled=limit_enabled,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: Request, data: RefreshRequest, session: Session = Depends(get_session)):
    try:
        payload = jwt.decode(data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido")

    token_type = payload.get("type")
    if token_type != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tipo de token inválido")

    username: str | None = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inválido no token")

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token sem jti")
    # Checar blacklist
    revoked = session.exec(select(RevokedToken).where(RevokedToken.jti == jti)).first()
    if revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revogado")
    # Rotação: revogar o refresh token atual e emitir novo
    exp = payload.get("exp")
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else datetime.now(timezone.utc)
    session.add(RevokedToken(jti=jti, owner_username=username, expires_at=expires_at))
    session.commit()

    # Audit: refresh/rotação
    rid = getattr(request.state, "request_id", request.headers.get("X-Request-ID", ""))
    session.add(
        AuditLog(
            actor_username=username,
            action="auth.refresh",
            resource="auth",
            resource_id=None,
            details=f"rotated=true jti={jti} request_id={rid}",
        )
    )
    session.commit()

    new_access = create_access_token(subject=username)
    new_refresh = create_refresh_token(subject=username)
    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


class RevokeRequest(BaseModel):
    refresh_token: str


@router.post("/revoke")
def revoke_token(request: Request, data: RevokeRequest, session: Session = Depends(get_session)):
    try:
        payload = jwt.decode(data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        # Já expirado: considerar revogado
        return {"status": "ok"}
    except jwt.InvalidTokenError:
        # Token inválido: tratar como revogado para segurança
        return {"status": "ok"}

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token não é refresh")

    jti = payload.get("jti")
    username = payload.get("sub")
    exp = payload.get("exp")
    if not jti or not exp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token incompleto")

    # Inserir na blacklist se ainda não presente
    exists = session.exec(select(RevokedToken).where(RevokedToken.jti == jti)).first()
    if not exists:
        # exp vem como timestamp UNIX da lib
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        session.add(RevokedToken(jti=jti, owner_username=username, expires_at=expires_at))
        session.commit()
    # Audit: revogação explícita
    rid = getattr(request.state, "request_id", request.headers.get("X-Request-ID", ""))
    session.add(
        AuditLog(
            actor_username=username or "",
            action="auth.revoke",
            resource="auth",
            resource_id=None,
            details=f"jti={jti} request_id={rid}",
        )
    )
    session.commit()
    return {"status": "ok"}


@router.get("/capacity", response_model=CapacitySummary)
def capacity(
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
    response: Response = None,
):
    per_license = int(DEVICES_PER_LICENSE)
    limit_enabled = per_license > 0
    active_list = session.exec(
        select(License).where(
            License.owner_username == current_user.username,
            License.status == "active",
        )
    ).all()
    active_licenses = len(active_list)
    devices_count = len(
        session.exec(select(Device).where(Device.owner_username == current_user.username)).all()
    )
    if limit_enabled:
        if LICENSE_PLAN_DEVICE_LIMITS:
            devices_allowed = 0
            for lic in active_list:
                plan = getattr(lic, "plan", None)
                devices_allowed += int(LICENSE_PLAN_DEVICE_LIMITS.get(plan, per_license))
        else:
            devices_allowed = active_licenses * per_license
    else:
        devices_allowed = 0
    devices_remaining = max(0, devices_allowed - devices_count) if limit_enabled else 0
    # Header e métrica de capacidade
    if response is not None:
        response.headers["X-Capacity-Remaining"] = str(devices_remaining)
    USER_CAPACITY_REMAINING.labels(current_user.username, "auth_capacity").set(devices_remaining)
    return CapacitySummary(
        active_licenses=active_licenses,
        devices_per_license=per_license,
        devices_allowed=devices_allowed,
        devices_count=devices_count,
        devices_remaining=devices_remaining,
        limit_enabled=limit_enabled,
    )


@router.post("/logout")
def logout():
    # JWT é stateless; em produção usar blacklist/rota de revogação se necessário
    return {"status": "ok"}


class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str | None = None


@router.post("/register")
def register(request: Request, data: RegisterRequest, session: Session = Depends(get_session)):
    existing = session.exec(select(UserAccount).where(UserAccount.username == data.username)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário já existe")
    password_hash = pwd_context.hash(data.password)
    user = UserAccount(username=data.username, full_name=data.full_name, password_hash=password_hash)
    session.add(user)
    session.commit()
    # Audit: registro
    rid = getattr(request.state, "request_id", request.headers.get("X-Request-ID", ""))
    session.add(
        AuditLog(
            actor_username=data.username,
            action="auth.register",
            resource="auth",
            resource_id=None,
            details=f"status=success request_id={rid}",
        )
    )
    session.commit()
    return {"status": "ok"}


@router.get("/me", response_model=UserProfile)
def me(current_user: UserProfile = Depends(get_current_user)):
    return current_user
