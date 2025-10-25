import json
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import verify_token
from app.db.session import get_db
from app.models import Device, License, User
from app.services.auth import get_user_by_email
from app.services.licenses import verify_device_secret

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(credentials.credentials, "access")
    if payload is None:
        raise credentials_exception

    email: str | None = payload.get("sub")
    if not email:
        raise credentials_exception

    user = get_user_by_email(db, email)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return current_user


def current_user_from_request(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = None
    auth_header = request.headers.get("authorization") or request.headers.get(
        "Authorization"
    )
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = request.query_params.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return user


async def require_active_license(
    request: Request,
    current_user: User = Depends(current_user_from_request),
    db: Session = Depends(get_db),
) -> User:
    license_record = (
        db.query(License)
        .filter(License.user_id == current_user.id, License.is_active.is_(True))
        .order_by(License.id)
        .first()
    )
    if not license_record:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No active license"
        )

    now_utc = datetime.now(timezone.utc)
    expires_at = license_record.expires_at
    if expires_at:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now_utc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="License expired"
            )

    device_id = request.headers.get("X-Device-ID") or request.query_params.get(
        "device_id"
    )
    device_key = request.headers.get("X-Device-Key") or request.query_params.get(
        "device_key"
    )
    if not device_id or not device_key:
        body_data: dict[str, object] | None = None
        content_type = (request.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
        if content_type == "application/json":
            body_bytes = getattr(request, "_body", None)
            if body_bytes is None:
                body_bytes = await request.body()
            request._body = body_bytes  # allow downstream handlers to reuse the body
            if body_bytes:
                try:
                    body_data = json.loads(body_bytes)
                except ValueError:
                    body_data = {}
            else:
                body_data = {}
            if not isinstance(body_data, dict):
                body_data = {}
        if isinstance(body_data, dict):
            device_id = device_id or body_data.get("device_id")
            device_key = device_key or body_data.get("device_secret") or body_data.get("device_key")
    if not device_id or not device_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device credentials not provided",
        )

    device = (
        db.query(Device)
        .filter(
            Device.device_id == device_id,
            Device.license_id == license_record.id,
            Device.is_active.is_(True),
        )
        .first()
    )
    if not device:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Device not authorized"
        )

    if not verify_device_secret(device, device_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid device key"
        )

    device.last_seen = datetime.now(timezone.utc)
    db.commit()
    db.refresh(device)

    return current_user

