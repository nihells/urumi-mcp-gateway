from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


@router.get("")
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    server_name: str | None = None,
    outcome: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List audit logs. Only administrators can view audit logs."""

    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator access required",
        )

    query = select(AuditLog)

    if server_name:
        query = query.where(AuditLog.server_name == server_name)

    if outcome:
        query = query.where(AuditLog.outcome == outcome)

    if start_time:
        query = query.where(AuditLog.timestamp >= start_time)

    if end_time:
        query = query.where(AuditLog.timestamp <= end_time)

    query = (
        query.order_by(AuditLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
    )

    logs = db.scalars(query).all()

    return {
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "server_name": log.server_name,
                "tool_name": log.tool_name,
                "timestamp": log.timestamp.isoformat(),
                "duration_ms": log.duration_ms,
                "outcome": log.outcome,
                "error_message": log.error_message,
            }
            for log in logs
        ],
    }