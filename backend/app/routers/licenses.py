from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import License, AuditLog
from app.routers.auth import get_current_user, UserProfile
from app.models import Device
from app.config import DEVICES_PER_LICENSE, LICENSE_PLAN_DEVICE_LIMITS
from app.observability import USER_CAPACITY_REMAINING


router = APIRouter(prefix="/licenses", tags=["licenses"])


class LicenseResponse(BaseModel):
    id: int
    status: str
    created_at: str


@router.post("/create", response_model=LicenseResponse)
def create_license(
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
):
    lic = License(owner_username=current_user.username)
    session.add(lic)
    session.commit()
    session.refresh(lic)
    log = AuditLog(
        actor_username=current_user.username,
        action="license.create",
        resource="license",
        resource_id=lic.id,
        details=None,
    )
    session.add(log)
    session.commit()
    return LicenseResponse(id=lic.id, status=lic.status, created_at=lic.created_at.isoformat())


@router.get("/me", response_model=List[LicenseResponse])
def list_my_licenses(
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
):
    items = session.exec(select(License).where(License.owner_username == current_user.username)).all()
    return [
        LicenseResponse(id=i.id, status=i.status, created_at=i.created_at.isoformat())
        for i in items
    ]


@router.post("/{license_id}/deactivate", response_model=LicenseResponse)
def deactivate_license(
    license_id: int,
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
):
    lic = session.exec(select(License).where(License.id == license_id)).first()
    if not lic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Licença não encontrada")
    if lic.owner_username != current_user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operação não permitida")
    lic.status = "inactive"
    session.add(lic)
    session.commit()
    session.refresh(lic)
    log = AuditLog(
        actor_username=current_user.username,
        action="license.deactivate",
        resource="license",
        resource_id=lic.id,
        details=None,
    )
    session.add(log)
    session.commit()
    return LicenseResponse(id=lic.id, status=lic.status, created_at=lic.created_at.isoformat())


class LicenseRulesResponse(BaseModel):
    active_licenses: int
    devices_per_license: int
    devices_allowed: int
    devices_count: int
    limit_enabled: bool
    limit_reached: bool


@router.get("/rules", response_model=LicenseRulesResponse)
def license_rules(
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
    response: Response = None,
):
    per_license = int(DEVICES_PER_LICENSE)
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
    limit_enabled = per_license > 0
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
    limit_reached = limit_enabled and devices_count >= devices_allowed if limit_enabled else False
    # Header e métrica de capacidade baseada em regras de licença
    devices_remaining = max(0, devices_allowed - devices_count) if limit_enabled else 0
    if response is not None:
        response.headers["X-Capacity-Remaining"] = str(devices_remaining)
    USER_CAPACITY_REMAINING.labels(current_user.username, "licenses_rules").set(devices_remaining)
    return LicenseRulesResponse(
        active_licenses=active_licenses,
        devices_per_license=per_license,
        devices_allowed=devices_allowed,
        devices_count=devices_count,
        limit_enabled=limit_enabled,
        limit_reached=limit_reached,
    )


class LicenseSummaryResponse(BaseModel):
    active_licenses: int
    inactive_licenses: int
    by_plan_active: dict[str, int]
    devices_per_license: int
    devices_allowed_total: int
    devices_count: int
    devices_remaining_total: int
    limit_enabled: bool


@router.get("/summary", response_model=LicenseSummaryResponse)
def licenses_summary(
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
    inactive_count = len(
        session.exec(
            select(License).where(
                License.owner_username == current_user.username,
                License.status == "inactive",
            )
        ).all()
    )
    active_licenses = len(active_list)
    # by_plan para ativas (None tratado como "default")
    by_plan: dict[str, int] = {}
    for lic in active_list:
        plan = getattr(lic, "plan", None)
        key = plan if (isinstance(plan, str) and plan.strip() != "") else "default"
        by_plan[key] = by_plan.get(key, 0) + 1

    devices_count = len(
        session.exec(select(Device).where(Device.owner_username == current_user.username)).all()
    )
    if limit_enabled:
        if LICENSE_PLAN_DEVICE_LIMITS:
            devices_allowed_total = 0
            for lic in active_list:
                plan = getattr(lic, "plan", None)
                devices_allowed_total += int(LICENSE_PLAN_DEVICE_LIMITS.get(plan, per_license))
        else:
            devices_allowed_total = active_licenses * per_license
    else:
        devices_allowed_total = 0
    devices_remaining_total = max(0, devices_allowed_total - devices_count) if limit_enabled else 0

    # Header e métrica de capacidade
    if response is not None:
        response.headers["X-Capacity-Remaining"] = str(devices_remaining_total)
    USER_CAPACITY_REMAINING.labels(current_user.username, "licenses_summary").set(
        devices_remaining_total
    )

    return LicenseSummaryResponse(
        active_licenses=active_licenses,
        inactive_licenses=inactive_count,
        by_plan_active=by_plan,
        devices_per_license=per_license,
        devices_allowed_total=devices_allowed_total,
        devices_count=devices_count,
        devices_remaining_total=devices_remaining_total,
        limit_enabled=limit_enabled,
    )


class LicenseWithPlanResponse(BaseModel):
    id: int
    status: str
    created_at: str
    plan: str | None


class SetPlanRequest(BaseModel):
    plan: str | None = None


@router.post("/{license_id}/set_plan", response_model=LicenseWithPlanResponse)
def set_license_plan(
    license_id: int,
    req: SetPlanRequest,
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
):
    lic = session.exec(select(License).where(License.id == license_id)).first()
    if not lic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Licença não encontrada")
    if lic.owner_username != current_user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operação não permitida")

    new_plan = req.plan.strip() if isinstance(req.plan, str) else None
    if new_plan == "":
        new_plan = None
    if LICENSE_PLAN_DEVICE_LIMITS and new_plan is not None:
        if new_plan not in LICENSE_PLAN_DEVICE_LIMITS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plano inválido")

    lic.plan = new_plan
    session.add(lic)
    session.commit()
    session.refresh(lic)
    log = AuditLog(
        actor_username=current_user.username,
        action="license.set_plan",
        resource="license",
        resource_id=lic.id,
        details=(new_plan or ""),
    )
    session.add(log)
    session.commit()
    return LicenseWithPlanResponse(
        id=lic.id,
        status=lic.status,
        created_at=lic.created_at.isoformat(),
        plan=lic.plan,
    )


class PlanInfo(BaseModel):
    name: str
    devices_allowed_per_license: int


@router.get("/plans", response_model=List[PlanInfo])
def list_license_plans(current_user: UserProfile = Depends(get_current_user)):
    if LICENSE_PLAN_DEVICE_LIMITS:
        return [
            PlanInfo(name=name, devices_allowed_per_license=int(limit))
            for name, limit in LICENSE_PLAN_DEVICE_LIMITS.items()
        ]
    default_limit = int(DEVICES_PER_LICENSE)
    if default_limit > 0:
        return [PlanInfo(name="default", devices_allowed_per_license=default_limit)]
    return []
