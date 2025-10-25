from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, Sequence

from sqlalchemy.orm import Session, selectinload

from app.core.security import get_password_hash, verify_password
from app.models import (
    AdminNotification,
    Device,
    License,
    LicenseRequest,
    User,
)
def _notify_admins(db: Session, message: str, payload: dict[str, str] | None = None) -> None:
    admins: Sequence[User] = (
        db.query(User).filter(User.is_admin.is_(True), User.is_active.is_(True)).all()
    )
    payload_json = json.dumps(payload) if payload else None
    now = datetime.utcnow()
    for admin in admins:
        notification = AdminNotification(
            admin_id=admin.id,
            type="license_request",
            message=message,
            payload=payload_json,
            created_at=now,
        )
        db.add(notification)


def create_license_request(
    db: Session,
    user: User,
    plan_name: str,
    device_id: str,
    device_name: Optional[str] = None,
    device_info: Optional[str] = None,
    notes: Optional[str] = None,
) -> LicenseRequest:
    license_request = LicenseRequest(
        user_id=user.id,
        plan_name=plan_name,
        max_devices=1,
        status="pending",
        device_id=device_id,
        device_name=device_name,
        device_info=device_info,
        notes=notes,
    )
    db.add(license_request)
    db.flush()
    _notify_admins(
        db,
        message=f"Novo pedido de licenca de {user.email}",
        payload={"license_request_id": str(license_request.id)},
    )
    db.commit()
    db.refresh(license_request)
    return license_request


def list_license_requests_for_user(db: Session, user_id: int) -> list[LicenseRequest]:
    return (
        db.query(LicenseRequest)
        .filter(LicenseRequest.user_id == user_id)
        .order_by(LicenseRequest.requested_at.desc())
        .all()
    )


def list_license_requests_for_admin(db: Session) -> list[LicenseRequest]:
    return (
        db.query(LicenseRequest)
        .options(selectinload(LicenseRequest.user))
        .order_by(
            LicenseRequest.status.asc(),
            LicenseRequest.requested_at.desc(),
        )
        .all()
    )


def _mark_notifications_read(db: Session, request_id: int, admin_id: int) -> None:
    now = datetime.utcnow()
    (
        db.query(AdminNotification)
        .filter(
            AdminNotification.admin_id == admin_id,
            AdminNotification.type == "license_request",
            AdminNotification.payload.like(f'%"{request_id}"%'),
            AdminNotification.is_read.is_(False),
        )
        .update({AdminNotification.is_read: True, AdminNotification.read_at: now})
    )


def approve_license_request(
    db: Session,
    license_request: LicenseRequest,
    admin: User,
    expires_in_days: int = 30,
    admin_notes: Optional[str] = None,
) -> tuple[License, Device, str]:
    if license_request.status != "pending":
        raise ValueError("License request already processed.")

    now = datetime.utcnow()
    license_request.status = "approved"
    license_request.decided_at = now
    license_request.decided_by = admin.id
    if admin_notes:
        license_request.admin_notes = admin_notes

    license_key = secrets.token_urlsafe(16)
    expires_at = now + timedelta(days=expires_in_days)
    license_obj = License(
        license_key=license_key,
        user_id=license_request.user_id,
        plan_name=license_request.plan_name,
        max_devices=license_request.max_devices,
        is_active=True,
        expires_at=expires_at,
        issued_at=now,
        request_id=license_request.id,
        approved_by=admin.id,
    )
    db.add(license_obj)
    db.flush()

    device_secret = secrets.token_urlsafe(16)
    secret_hash = get_password_hash(device_secret)
    existing_device = (
        db.query(Device)
        .filter(Device.device_id == license_request.device_id)
        .first()
    )
    if existing_device:
        existing_device.license_id = license_obj.id
        existing_device.user_id = license_request.user_id
        existing_device.device_name = license_request.device_name
        existing_device.is_active = True
        existing_device.secret_hash = secret_hash
        existing_device.hardware_info = license_request.device_info
        device = existing_device
    else:
        device = Device(
            device_id=license_request.device_id,
            device_name=license_request.device_name,
            user_id=license_request.user_id,
            license_id=license_obj.id,
            is_active=True,
            secret_hash=secret_hash,
            hardware_info=license_request.device_info,
        )
        db.add(device)
    license_request.device_secret = device_secret

    _mark_notifications_read(db, license_request.id, admin.id)

    db.commit()
    db.refresh(license_request)
    db.refresh(license_obj)
    db.refresh(device)
    return license_obj, device, device_secret


def reject_license_request(
    db: Session,
    license_request: LicenseRequest,
    admin: User,
    admin_notes: Optional[str] = None,
) -> LicenseRequest:
    if license_request.status != "pending":
        raise ValueError("License request already processed.")

    now = datetime.utcnow()
    license_request.status = "rejected"
    license_request.decided_at = now
    license_request.decided_by = admin.id
    if admin_notes:
        license_request.admin_notes = admin_notes
    license_request.device_secret = None

    _mark_notifications_read(db, license_request.id, admin.id)
    db.commit()
    db.refresh(license_request)
    return license_request


def get_license_request(db: Session, request_id: int) -> Optional[LicenseRequest]:
    return (
        db.query(LicenseRequest)
        .filter(LicenseRequest.id == request_id)
        .first()
    )


def list_admin_notifications(db: Session, admin_id: int) -> list[AdminNotification]:
    return (
        db.query(AdminNotification)
        .filter(AdminNotification.admin_id == admin_id)
        .order_by(AdminNotification.created_at.desc())
        .all()
    )


def verify_device_secret(device: Device, raw_secret: Optional[str]) -> bool:
    if not raw_secret or not device.secret_hash:
        return False
    return verify_password(raw_secret, device.secret_hash)


def get_unread_notifications_count(db: Session, admin_id: int) -> int:
    return (
        db.query(AdminNotification)
        .filter(AdminNotification.admin_id == admin_id, AdminNotification.is_read.is_(False))
        .count()
    )
