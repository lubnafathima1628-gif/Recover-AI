from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.models import AuditLog

class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        merchant_id: str,
        event_type: str,
        action: str,
        actor: str = "AI_ENGINE",
        payment_id: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Appends an immutable audit event to the ledger.
        """
        audit_entry = AuditLog(
            merchant_id=merchant_id,
            payment_id=payment_id,
            event_type=event_type,
            actor=actor,
            action=action,
            reason=reason,
            metadata_json=metadata or {}
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        return audit_entry

audit_service = AuditService()
