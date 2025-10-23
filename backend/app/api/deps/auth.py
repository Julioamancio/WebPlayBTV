from datetime import datetime

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import verify_token
from app.db.session import get_db
from app.models import Device, License, User
from app.services.auth import get_user_by_email

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


def require_active_license(
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

    device_id = request.headers.get("X-Device-ID") or request.query_params.get(
        "device_id"
    )
    device_name = request.headers.get("User-Agent")
    if not device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Device not provided"
        )

    device = (
        db.query(Device)
        .filter(Device.device_id == device_id, Device.user_id == current_user.id)
        .first()
    )

    now = datetime.utcnow()
    changed = False
    if not device or not device.is_active:
        current_count = (
            db.query(Device)
            .filter(Device.license_id == license_record.id, Device.is_active.is_(True))
            .count()
        )
        if current_count >= license_record.max_devices:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Max devices reached for this license",
            )
        if not device:
            device = Device(
                device_id=device_id,
                device_name=device_name,
                user_id=current_user.id,
                license_id=license_record.id,
                is_active=True,
                last_seen=now,
            )
            db.add(device)
        else:
            device.license_id = license_record.id
            device.is_active = True
            device.last_seen = now
        changed = True
    else:
        if device.last_seen != now:
            device.last_seen = now
            changed = True

    if changed:
        db.commit()
        db.refresh(device)

    return current_user

