from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog


def audit_event(
    db: Session,
    user_id: int,
    action: str,
    resource: Optional[str] = None,
    resource_id: Optional[str] = None,
    request: Optional[Request] = None,
) -> None:
    ip_address = None
    user_agent = None
    if request:
        try:
            ip_address = request.client.host if request.client else None
        except Exception:
            ip_address = None
        user_agent = request.headers.get("user-agent")

    log = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=str(resource_id) if resource_id is not None else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    db.commit()

