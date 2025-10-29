from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select
from datetime import datetime, timezone

from app.db import get_session
from app.models import AuditLog
from app.routers.auth import get_current_user, UserProfile


router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogResponse(BaseModel):
    id: int
    action: str
    resource: str
    resource_id: int | None
    details: str | None
    created_at: str


@router.get("/me", response_model=List[AuditLogResponse])
def list_my_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    actions: Optional[List[str]] = Query(default=None, description="Filtrar por ações"),
    resources: Optional[List[str]] = Query(default=None, description="Filtrar por recursos"),
    from_time: Optional[datetime] = Query(default=None, description="ISO8601; assume UTC se sem timezone"),
    to_time: Optional[datetime] = Query(default=None, description="ISO8601; assume UTC se sem timezone"),
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
):
    # Base query: logs do usuário atual
    q = select(AuditLog).where(AuditLog.actor_username == current_user.username)
    # Filtros por ação e recurso
    if actions:
        q = q.where(AuditLog.action.in_(actions))
    if resources:
        q = q.where(AuditLog.resource.in_(resources))
    # Intervalo de tempo (padroniza para UTC quando necessário)
    if from_time is not None:
        ft = from_time if from_time.tzinfo else from_time.replace(tzinfo=timezone.utc)
        q = q.where(AuditLog.created_at >= ft)
    if to_time is not None:
        tt = to_time if to_time.tzinfo else to_time.replace(tzinfo=timezone.utc)
        q = q.where(AuditLog.created_at <= tt)

    q = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    items = session.exec(q).all()
    return [
        AuditLogResponse(
            id=i.id,
            action=i.action,
            resource=i.resource,
            resource_id=i.resource_id,
            details=i.details,
            created_at=i.created_at.isoformat(),
        )
        for i in items
    ]
