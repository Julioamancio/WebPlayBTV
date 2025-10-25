from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_active_user, require_active_license
from app.db.session import get_db
from app.models import Device, License, User
from app.schemas import (
    DeviceCreate,
    DeviceHeartbeat,
    DeviceResponse,
    DeviceUnbind,
)
from app.services.audit import audit_event

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/bind", response_model=DeviceResponse)
def bind_device(
    payload: DeviceCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    *,
    request: Request,
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")

    license_obj = (
        db.query(License)
        .filter(License.id == payload.license_id)
        .first()
    )
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    if not license_obj.is_active:
        raise HTTPException(status_code=400, detail="License inactive")

    current_count = (
        db.query(Device)
        .filter(Device.license_id == license_obj.id, Device.is_active.is_(True))
        .count()
    )
    if current_count >= license_obj.max_devices:
        raise HTTPException(
            status_code=400, detail="Max devices reached for this license"
        )

    device = Device(
        device_id=payload.device_id,
        device_name=payload.device_name,
        user_id=license_obj.user_id,
        license_id=license_obj.id,
        is_active=True,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    audit_event(
        db,
        current_user.id,
        action="device_bind",
        resource="device",
        resource_id=device.id,
        request=request,
    )
    return device


@router.post("/unbind", response_model=DeviceResponse)
def unbind_device(
    payload: DeviceUnbind,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    *,
    request: Request,
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")

    device = (
        db.query(Device)
        .filter(Device.id == payload.id)
        .first()
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if not device.is_active:
        raise HTTPException(status_code=400, detail="Device already inactive")

    device.is_active = False
    db.commit()
    db.refresh(device)
    audit_event(
        db,
        current_user.id,
        action="device_unbind",
        resource="device",
        resource_id=device.id,
        request=request,
    )
    return device


@router.post("/heartbeat", response_model=DeviceResponse)
def heartbeat_device(
    payload: DeviceHeartbeat,
    current_user: User = Depends(require_active_license),
    db: Session = Depends(get_db),
    *,
    request: Request,
):
    device = (
        db.query(Device)
        .filter(Device.device_id == payload.device_id, Device.user_id == current_user.id)
        .first()
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.last_seen = datetime.now(timezone.utc)
    db.commit()
    db.refresh(device)
    audit_event(
        db,
        current_user.id,
        action="device_heartbeat",
        resource="device",
        resource_id=device.id,
        request=request,
    )
    return device


@router.get("/me", response_model=List[DeviceResponse])
def list_devices(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[Device]:
    query = db.query(Device)
    if not current_user.is_admin:
        query = query.filter(Device.user_id == current_user.id)
    return query.order_by(Device.created_at.asc()).all()
