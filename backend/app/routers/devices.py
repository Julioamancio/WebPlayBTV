from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import Device
from app.routers.auth import get_current_user, UserProfile


router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceRegisterRequest(BaseModel):
    fingerprint: str
    name: str | None = None
    platform: str | None = None


class DeviceResponse(BaseModel):
    id: int
    fingerprint: str
    name: str | None
    platform: str | None


@router.post("/register", response_model=DeviceResponse)
def register_device(
    data: DeviceRegisterRequest,
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
):
    existing = session.exec(
        select(Device).where(
            Device.fingerprint == data.fingerprint,
            Device.owner_username == current_user.username,
        )
    ).first()

    if existing:
        return DeviceResponse(
            id=existing.id,
            fingerprint=existing.fingerprint,
            name=existing.name,
            platform=existing.platform,
        )

    device = Device(
        fingerprint=data.fingerprint,
        name=data.name,
        platform=data.platform,
        owner_username=current_user.username,
    )
    session.add(device)
    session.commit()
    session.refresh(device)

    return DeviceResponse(
        id=device.id,
        fingerprint=device.fingerprint,
        name=device.name,
        platform=device.platform,
    )


@router.get("/me", response_model=List[DeviceResponse])
def list_my_devices(
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
):
    devices = session.exec(
        select(Device).where(Device.owner_username == current_user.username)
    ).all()
    return [
        DeviceResponse(
            id=d.id,
            fingerprint=d.fingerprint,
            name=d.name,
            platform=d.platform,
        )
        for d in devices
    ]

