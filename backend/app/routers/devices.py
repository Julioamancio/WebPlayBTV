from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import Device, AuditLog
from app.routers.auth import get_current_user, UserProfile
from app.models import License
from app.config import DEVICES_PER_LICENSE, LICENSE_PLAN_DEVICE_LIMITS
from app.observability import USER_CAPACITY_REMAINING, CAPACITY_LIMIT_REACHED_TOTAL


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


class DeviceCapacityResponse(BaseModel):
    active_licenses: int
    devices_per_license: int
    limit_enabled: bool
    devices_allowed: int
    devices_count: int
    devices_remaining: int


@router.post("/register", response_model=DeviceResponse)
def register_device(
    data: DeviceRegisterRequest,
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
    response: Response = None,
):
    # Cálculo de capacidade atual do usuário
    per_license = int(DEVICES_PER_LICENSE)
    limit_enabled = per_license > 0
    active_licenses = []
    if limit_enabled:
        active_licenses = session.exec(
            select(License).where(
                License.owner_username == current_user.username,
                License.status == "active",
            )
        ).all()
    devices_count = len(
        session.exec(select(Device).where(Device.owner_username == current_user.username)).all()
    )
    if limit_enabled:
        if LICENSE_PLAN_DEVICE_LIMITS:
            max_allowed = 0
            for lic in active_licenses:
                plan = getattr(lic, "plan", None)
                max_allowed += int(LICENSE_PLAN_DEVICE_LIMITS.get(plan, per_license))
        else:
            max_allowed = len(active_licenses) * per_license
    else:
        max_allowed = 0

    existing = session.exec(
        select(Device).where(
            Device.fingerprint == data.fingerprint,
            Device.owner_username == current_user.username,
        )
    ).first()

    if existing:
        # Header com capacidade atual (sem alteração no registro)
        if response is not None:
            remaining = max(0, max_allowed - devices_count) if limit_enabled else 0
            response.headers["X-Capacity-Remaining"] = str(remaining)
        # Métrica de capacidade no fluxo de registro (sem alteração)
        USER_CAPACITY_REMAINING.labels(current_user.username, "devices_register").set(
            max(0, max_allowed - devices_count) if limit_enabled else 0
        )
        return DeviceResponse(
            id=existing.id,
            fingerprint=existing.fingerprint,
            name=existing.name,
            platform=existing.platform,
        )

    # Regra opcional de limite por licença ativa
    if limit_enabled:
        if len(active_licenses) == 0:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nenhuma licença ativa")
        # Bloquear se limite atingido
        if devices_count >= max_allowed:
            # Contador de limite atingido
            CAPACITY_LIMIT_REACHED_TOTAL.labels("devices_register").inc()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Limite de dispositivos atingido ({devices_count}/{max_allowed})",
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
    log = AuditLog(
        actor_username=current_user.username,
        action="device.register",
        resource="device",
        resource_id=device.id,
        details=device.fingerprint,
    )
    session.add(log)
    session.commit()

    # Header com capacidade restante após registrar o dispositivo
    if response is not None:
        updated_count = devices_count + 1
        remaining_after = max(0, max_allowed - updated_count) if limit_enabled else 0
        response.headers["X-Capacity-Remaining"] = str(remaining_after)
    # Métrica de capacidade após registrar dispositivo
    USER_CAPACITY_REMAINING.labels(current_user.username, "devices_register").set(
        max(0, max_allowed - (devices_count + 1)) if limit_enabled else 0
    )

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


@router.delete("/{device_id}")
def delete_my_device(
    device_id: int,
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
):
    device = session.exec(select(Device).where(Device.id == device_id)).first()
    if not device:
        # Idempotente: remover algo inexistente retorna ok
        return {"status": "ok"}
    if device.owner_username != current_user.username:
        # Não permitir remover dispositivo de outro usuário
        from fastapi import HTTPException, status as http_status

        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Operação não permitida")
    session.delete(device)
    session.commit()
    log = AuditLog(
        actor_username=current_user.username,
        action="device.delete",
        resource="device",
        resource_id=device.id,
        details=device.fingerprint,
    )
    session.add(log)
    session.commit()
    return {"status": "ok"}


@router.get("/capacity", response_model=DeviceCapacityResponse)
def device_capacity(
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
        session.exec(
            select(Device).where(Device.owner_username == current_user.username)
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
    if response is not None:
        response.headers["X-Capacity-Remaining"] = str(devices_remaining)
    # Métrica de capacidade do endpoint de capacidade
    USER_CAPACITY_REMAINING.labels(current_user.username, "devices_capacity").set(devices_remaining)
    return DeviceCapacityResponse(
        active_licenses=active_licenses,
        devices_per_license=per_license,
        limit_enabled=limit_enabled,
        devices_allowed=devices_allowed,
        devices_count=devices_count,
        devices_remaining=devices_remaining,
    )

