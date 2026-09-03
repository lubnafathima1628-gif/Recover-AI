from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from backend.app.core.database import get_db
from backend.app.models.models import Payment, Prediction, Customer
from backend.app.schemas.schemas import PaymentResponse, RecoveryExecuteRequest, RecoveryExecutionResult
from backend.app.payments.payment_service import PaymentService

router = APIRouter(tags=["Recovery Engine"])

@router.get("/recovery/queue", response_model=List[PaymentResponse])
def get_recovery_queue(
    db: Session = Depends(get_db),
    min_probability: Optional[float] = None,
    min_amount: Optional[float] = None,
    failure_category: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0
):
    """
    Returns active at-risk payments prioritized by Expected Recovery Value (EV) descending.
    """
    query = db.query(Payment).filter(Payment.status == "FAILED")

    if min_amount:
        query = query.filter(Payment.amount >= min_amount)
    if failure_category:
        query = query.filter(Payment.failure_code == failure_category.upper())

    # Join prediction to filter or sort by Expected Value
    query = query.outerjoin(Prediction)

    if min_probability:
        query = query.filter(Prediction.recovery_probability >= min_probability)
    if action:
        query = query.filter(Prediction.recommended_action == action.upper())

    # Order by Expected Value descending (default)
    payments = query.order_by(Prediction.expected_value.desc().nullslast()).offset(offset).limit(limit).all()
    return payments

@router.post("/recover/{id}", response_model=RecoveryExecutionResult)
def execute_recovery_action(
    id: str,
    payload: Optional[RecoveryExecuteRequest] = None,
    db: Session = Depends(get_db)
):
    payment_service = PaymentService(db)
    action = payload.action if payload else None
    channel = payload.channel if payload else None
    force_override = payload.force_override if payload else False

    try:
        result = payment_service.execute_recovery(
            payment_id=id,
            action=action,
            channel=channel,
            force_override=force_override,
            actor="AI_RECOVERY_ENGINE"
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/recovery/{id}/approve", response_model=PaymentResponse)
def approve_recovery(id: str, db: Session = Depends(get_db)):
    payment_service = PaymentService(db)
    try:
        payment = payment_service.approve_recovery(id, actor="MANAGER_APPROVER")
        return payment
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/recovery/{id}/reject", response_model=PaymentResponse)
def reject_recovery(id: str, db: Session = Depends(get_db)):
    payment_service = PaymentService(db)
    try:
        payment = payment_service.reject_recovery(id, actor="MANAGER_APPROVER")
        return payment
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/recovery/{id}/reconcile", response_model=Dict[str, Any])
def reconcile_payment(id: str, db: Session = Depends(get_db)):
    payment_service = PaymentService(db)
    try:
        result = payment_service.verify_and_reconcile(id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
