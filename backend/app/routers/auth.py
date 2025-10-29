from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.config import DEVICES_PER_LICENSE, LICENSE_PLAN_DEVICE_LIMITS
from app.db import get_session
from app.models_auth import UserAccount
from app.models import License, Device
from passlib.context import CryptContext
from app.observability import USER_CAPACITY_REMAINING


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
    data: LoginRequest,
    session: Session = Depends(get_session),
    response: Response = None,
):
    # Try DB user first
    db_user = session.exec(select(UserAccount).where(UserAccount.username == data.username)).first()
    if db_user:
        if not pwd_context.verify(data.password, db_user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
        token = create_access_token(subject=db_user.username)
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
        return LoginResponse(
            access_token=token,
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
    return LoginResponse(
        access_token=token,
        capacity=CapacitySummary(
            active_licenses=active_licenses,
            devices_per_license=per_license,
            devices_allowed=devices_allowed,
            devices_count=devices_count,
            devices_remaining=devices_remaining,
            limit_enabled=limit_enabled,
        ),
    )


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
def register(data: RegisterRequest, session: Session = Depends(get_session)):
    existing = session.exec(select(UserAccount).where(UserAccount.username == data.username)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário já existe")
    password_hash = pwd_context.hash(data.password)
    user = UserAccount(username=data.username, full_name=data.full_name, password_hash=password_hash)
    session.add(user)
    session.commit()
    return {"status": "ok"}


@router.get("/me", response_model=UserProfile)
def me(current_user: UserProfile = Depends(get_current_user)):
    return current_user
