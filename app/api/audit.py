from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.core.database import get_db
from backend.app.models.models import AuditLog
from backend.app.schemas.schemas import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["Audit Trail"])

@router.get("", response_model=List[AuditLogResponse])
def list_audit_logs(
    db: Session = Depends(get_db),
    payment_id: Optional[str] = None,
    event_type: Optional[str] = None,
    actor: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0
):
    query = db.query(AuditLog)
    if payment_id:
        query = query.filter(AuditLog.payment_id == payment_id)
    if event_type:
        query = query.filter(AuditLog.event_type == event_type.upper())
    if actor:
        query = query.filter(AuditLog.actor.ilike(f"%{actor}%"))

    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()
    return logs

@router.get("/{id}", response_model=List[AuditLogResponse])
def get_payment_audit_trail(id: str, db: Session = Depends(get_db)):
    """Returns chronological append-only audit events for a transaction or audit ID."""
    logs = db.query(AuditLog).filter(
        (AuditLog.payment_id == id) | (AuditLog.audit_id == id)
    ).order_by(AuditLog.timestamp.asc()).all()
    return logs
