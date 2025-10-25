from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, selectinload

from app.api.deps.auth import get_current_active_user, require_admin_user
from app.db.session import get_db
from app.models import Device, License
from app.schemas import (
    AdminNotificationResponse,
    DeviceWithSecret,
    LicenseApproval,
    LicenseApprovalResult,
    LicenseDetailedResponse,
    LicenseRequestAdminResponse,
    LicenseRequestCreate,
    LicenseRequestResponse,
    LicenseRejection,
    LicenseResponse,
)
from app.services.audit import audit_event
from app.services.licenses import (
    approve_license_request,
    create_license_request,
    get_license_request,
    get_unread_notifications_count,
    list_admin_notifications,
    list_license_requests_for_admin,
    list_license_requests_for_user,
    reject_license_request,
)

router = APIRouter(prefix="/licenses", tags=["licenses"])


@router.post("/requests", response_model=LicenseRequestResponse, status_code=status.HTTP_201_CREATED)
def submit_license_request(
    payload: LicenseRequestCreate,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
    *,
    request: Request,
):
    license_request = create_license_request(
        db=db,
        user=current_user,
        plan_name=payload.plan_name,
        device_id=payload.device_id,
        device_name=payload.device_name,
        device_info=payload.device_info,
        notes=payload.notes,
    )
    audit_event(
        db,
        current_user.id,
        action="license_request_submitted",
        resource="license_request",
        resource_id=license_request.id,
        request=request,
    )
    return license_request


@router.get("/requests/me", response_model=List[LicenseRequestResponse])
def list_my_license_requests(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[LicenseRequestResponse]:
    return list_license_requests_for_user(db, user_id=current_user.id)


@router.get("/me", response_model=List[LicenseDetailedResponse])
def list_my_licenses(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[License]:
    licenses = (
        db.query(License)
        .options(selectinload(License.devices))
        .filter(License.user_id == current_user.id)
        .order_by(License.created_at.desc())
        .all()
    )
    return licenses


@router.get("/admin/requests", response_model=List[LicenseRequestAdminResponse])
def list_all_license_requests(
    admin=Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> List[LicenseRequestAdminResponse]:
    requests = list_license_requests_for_admin(db)
    return [
        LicenseRequestAdminResponse.from_orm(req).copy(update={"user_email": req.user.email if req.user else None})
        for req in requests
    ]


@router.post(
    "/admin/requests/{request_id}/approve",
    response_model=LicenseApprovalResult,
)
def approve_request(
    request_id: int,
    payload: LicenseApproval,
    admin=Depends(require_admin_user),
    db: Session = Depends(get_db),
    *,
    request: Request,
):
    license_request = get_license_request(db, request_id)
    if not license_request:
        raise HTTPException(status_code=404, detail="Pedido de licença não encontrado")
    try:
        license_obj, device, device_secret = approve_license_request(
            db=db,
            license_request=license_request,
            admin=admin,
            expires_in_days=payload.expires_in_days,
            admin_notes=payload.admin_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audit_event(
        db,
        admin.id,
        action="license_request_approved",
        resource="license",
        resource_id=license_obj.id,
        request=request,
    )
    audit_event(
        db,
        license_obj.user_id,
        action="license_request_approved",
        resource="license",
        resource_id=license_obj.id,
        request=request,
    )
    device_schema = DeviceWithSecret.from_orm(device)
    device_schema.device_secret = device_secret
    return LicenseApprovalResult(
        license=license_obj,
        device=device_schema,
    )


@router.post("/admin/requests/{request_id}/reject", response_model=LicenseRequestResponse)
def reject_request(
    request_id: int,
    payload: LicenseRejection,
    admin=Depends(require_admin_user),
    db: Session = Depends(get_db),
    *,
    request: Request,
):
    license_request = get_license_request(db, request_id)
    if not license_request:
        raise HTTPException(status_code=404, detail="Pedido de licença não encontrado")
    try:
        updated_request = reject_license_request(
            db=db,
            license_request=license_request,
            admin=admin,
            admin_notes=payload.admin_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audit_event(
        db,
        admin.id,
        action="license_request_rejected",
        resource="license_request",
        resource_id=updated_request.id,
        request=request,
    )
    audit_event(
        db,
        updated_request.user_id,
        action="license_request_rejected",
        resource="license_request",
        resource_id=updated_request.id,
        request=request,
    )
    return updated_request


@router.get("/admin/notifications", response_model=List[AdminNotificationResponse])
def list_notifications(
    admin=Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> List[AdminNotificationResponse]:
    return list_admin_notifications(db, admin.id)


@router.get("/admin/notifications/unread-count")
def unread_notifications_count(
    admin=Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    count = get_unread_notifications_count(db, admin.id)
    return {"count": count}


@router.post("/{license_id}/deactivate", response_model=LicenseResponse)
def deactivate_license(
    license_id: int,
    admin=Depends(require_admin_user),
    db: Session = Depends(get_db),
    *,
    request: Request,
):
    license_obj = (
        db.query(License)
        .filter(License.id == license_id)
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
        admin.id,
        action="license_deactivate",
        resource="license",
        resource_id=license_obj.id,
        request=request,
    )
    return license_obj


@router.post("/{license_id}/activate", response_model=LicenseResponse)
def activate_license(
    license_id: int,
    admin=Depends(require_admin_user),
    db: Session = Depends(get_db),
    *,
    request: Request,
):
    license_obj = (
        db.query(License)
        .filter(License.id == license_id)
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
        admin.id,
        action="license_activate",
        resource="license",
        resource_id=license_obj.id,
        request=request,
    )
    return license_obj
