from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.app.core.database import get_db
from backend.app.models.models import Notification, Merchant
from backend.app.schemas.schemas import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("", response_model=List[NotificationResponse])
def list_notifications(db: Session = Depends(get_db)):
    notifications = db.query(Notification).order_by(Notification.created_at.desc()).limit(20).all()
    if not notifications:
        # Generate default realistic notifications if empty
        merchant = db.query(Merchant).first()
        merchant_id = merchant.merchant_id if merchant else "merchant_demo_electronics_01"
        defaults = [
            ("₹42,500 Ultra-Wide Monitor payment requires manager approval", "High-value transaction exceeds ₹15,000 threshold.", "ALERT"),
            ("₹24,000 Enterprise Cloud Sync successfully recovered", "Recovered via automated WhatsApp 1-click payment link.", "SUCCESS"),
            ("UPI failure rate spike detected across bank switches", "Switch timeout increased 14% in the last 60 minutes.", "WARNING"),
            ("14 at-risk payments automatically queued for recovery", "Expected recovery yield: ₹89,400.", "INFO")
        ]
        for title, msg, n_type in defaults:
            n = Notification(
                merchant_id=merchant_id,
                title=title,
                message=msg,
                type=n_type
            )
            db.add(n)
        db.commit()
        notifications = db.query(Notification).order_by(Notification.created_at.desc()).all()

    return notifications

@router.post("/{id}/read", response_model=NotificationResponse)
def mark_notification_read(id: str, db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.notification_id == id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif
