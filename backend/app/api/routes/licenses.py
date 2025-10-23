import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_active_user
from app.db.session import get_db
from app.models import Device, License, User
from app.schemas import LicenseCreate, LicenseResponse
from app.services.audit import audit_event

router = APIRouter(prefix="/licenses", tags=["licenses"])


@router.post("/issue", response_model=LicenseResponse)
def issue_license(
    payload: LicenseCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request | None = None,
):
    license_key = secrets.token_urlsafe(16)
    license_obj = License(
        license_key=license_key,
        user_id=current_user.id,
        plan_name=payload.plan_name,
        max_devices=payload.max_devices,
        is_active=True,
    )
    db.add(license_obj)
    db.commit()
    db.refresh(license_obj)

    audit_event(
        db,
        current_user.id,
        action="license_issue",
        resource="license",
        resource_id=license_obj.id,
        request=request,
    )
    return license_obj


@router.post("/{license_id}/deactivate", response_model=LicenseResponse)
def deactivate_license(
    license_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request | None = None,
):
    license_obj = (
        db.query(License)
        .filter(License.id == license_id, License.user_id == current_user.id)
        .first()
    )
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    if not license_obj.is_active:
        raise HTTPException(status_code=400, detail="License already inactive")

    license_obj.is_active = False
    db.query(Device).filter(Device.license_id == license_obj.id).update(
        {Device.is_active: False}
    )
    db.commit()
    db.refresh(license_obj)
    audit_event(
        db,
        current_user.id,
        action="license_deactivate",
        resource="license",
        resource_id=license_obj.id,
        request=request,
    )
    return license_obj


@router.post("/{license_id}/activate", response_model=LicenseResponse)
def activate_license(
    license_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request | None = None,
):
    license_obj = (
        db.query(License)
        .filter(License.id == license_id, License.user_id == current_user.id)
        .first()
    )
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    if license_obj.is_active:
        raise HTTPException(status_code=400, detail="License already active")

    license_obj.is_active = True
    db.commit()
    db.refresh(license_obj)
    audit_event(
        db,
        current_user.id,
        action="license_activate",
        resource="license",
        resource_id=license_obj.id,
        request=request,
    )
    return license_obj


@router.get("/me", response_model=List[LicenseResponse])
def list_licenses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[License]:
    return (
        db.query(License)
        .filter(License.user_id == current_user.id)
        .order_by(License.created_at.asc())
        .all()
    )
