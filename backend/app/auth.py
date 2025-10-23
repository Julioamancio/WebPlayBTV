from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, License, Device

import logging
import os


# Configurações JWT
SECRET_KEY = os.getenv("JWT_SECRET", "change-me-in-env")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
logger = logging.getLogger("webplayer.auth")

if SECRET_KEY == "change-me-in-env":
    logger.warning("JWT secret is using default value; set JWT_SECRET in environment for production use.")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access"):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        return None


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = verify_token(credentials.credentials, "access")
        if payload is None:
            raise credentials_exception

        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def current_user_from_request(
    request: Request,
    db: Session = Depends(get_db),
):
    token = None
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user


def require_active_license(
    request: Request,
    current_user: User = Depends(current_user_from_request),
    db: Session = Depends(get_db),
):
    lic = (
        db.query(License)
        .filter(License.user_id == current_user.id, License.is_active == True)
        .order_by(License.id)
        .first()
    )
    if not lic:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active license")

    device_id = request.headers.get("X-Device-ID") or request.query_params.get("device_id")
    device_name = request.headers.get("User-Agent")
    if not device_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device not provided")

    dev = (
        db.query(Device)
        .filter(Device.device_id == device_id, Device.user_id == current_user.id)
        .first()
    )

    now = datetime.utcnow()
    changed = False
    if not dev or not dev.is_active:
        current_count = (
            db.query(Device)
            .filter(Device.license_id == lic.id, Device.is_active == True)
            .count()
        )
        if current_count >= lic.max_devices:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Max devices reached for this license",
            )
        if not dev:
            dev = Device(
                device_id=device_id,
                device_name=device_name,
                user_id=current_user.id,
                license_id=lic.id,
                is_active=True,
                last_seen=now,
            )
            db.add(dev)
        else:
            dev.license_id = lic.id
            dev.is_active = True
            dev.last_seen = now
        changed = True
    else:
        if dev.last_seen != now:
            dev.last_seen = now
            changed = True

    if changed:
        db.commit()
        db.refresh(dev)

    return current_user
