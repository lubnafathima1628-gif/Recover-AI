from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any

from backend.app.core.database import get_db
from backend.app.services.demo_service import demo_engine
from backend.app.models.models import Payment, Order, Customer, Prediction, RecoveryAttempt, AuditLog, Notification

router = APIRouter(prefix="/demo", tags=["Demo Engine"])

@router.post("/run")
def run_demo(db: Session = Depends(get_db)):
    """
    Executes automated batch recovery across active at-risk payments in the database.
    """
    from backend.app.payments.payment_service import PaymentService
    payment_service = PaymentService(db)

    failed_payments = db.query(Payment).filter(
        Payment.status == "FAILED",
        Payment.requires_approval == False
    ).limit(30).all()

    recovered_count = 0
    total_recovered_amount = 0.0

    for payment in failed_payments:
        res = payment_service.execute_recovery(payment.payment_id, actor="DEMO_AUTO_RECOVERY")
        if res.get("status") == "SUCCESS":
            recovered_count += 1
            total_recovered_amount += res.get("recovered_amount", 0.0)

    return {
        "status": "SUCCESS",
        "recovered_count": recovered_count,
        "total_recovered_amount": total_recovered_amount,
        "message": f"Processed {len(failed_payments)} at-risk transactions, successfully recovering ₹{total_recovered_amount:,.2f}."
    }

@router.post("/reset")
def reset_demo(db: Session = Depends(get_db)):
    """Resets database and re-seeds fresh synthetic transactions."""
    # Delete children first
    db.query(RecoveryAttempt).delete()
    db.query(Prediction).delete()
    db.query(AuditLog).delete()
    db.query(Notification).delete()
    db.query(Payment).delete()
    db.query(Order).delete()
    db.commit()

    # Re-seed
    res = demo_engine.generate_seed_dataset(db, total_count=300)
    return {"status": "SUCCESS", "message": "Demo environment reset and seeded with 300 transactions."}

@router.get("/stream")
def stream_demo_events(db: Session = Depends(get_db)):
    """SSE real-time stream for the interactive live recovery demo command center."""
    return StreamingResponse(
        demo_engine.run_live_demo_stream(db),
        media_type="text/event-stream"
    )
