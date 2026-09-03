from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from backend.app.core.database import get_db
from backend.app.models.models import Payment, Customer, Order, Prediction, RecoveryAttempt, Policy
from backend.app.schemas.schemas import PaymentResponse, PaymentCreate
from backend.app.payments.payment_service import PaymentService
from backend.app.ml.classifier import classifier
from backend.app.ml.recovery_model import recovery_model
from backend.app.ml.expected_value import expected_value_engine
from backend.app.ml.decision_engine import decision_engine

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.get("", response_model=List[PaymentResponse])
def list_transactions(
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    method: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0
):
    query = db.query(Payment)
    if status:
        query = query.filter(Payment.status == status.upper())
    if method:
        query = query.filter(Payment.method == method.upper())
    if search:
        query = query.join(Customer).filter(
            (Payment.payment_id.ilike(f"%{search}%")) |
            (Customer.name.ilike(f"%{search}%")) |
            (Customer.email.ilike(f"%{search}%"))
        )

    payments = query.order_by(Payment.timestamp.desc()).offset(offset).limit(limit).all()
    return payments

@router.get("/{id}", response_model=PaymentResponse)
def get_transaction(id: str, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.payment_id == id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return payment

@router.post("", response_model=PaymentResponse)
def create_transaction(payload: PaymentCreate, db: Session = Depends(get_db)):
    # Find or create demo customer
    customer = None
    if payload.customer_id:
        customer = db.query(Customer).filter(Customer.customer_id == payload.customer_id).first()
    if not customer:
        customer = db.query(Customer).first()
    if not customer:
        customer = Customer(
            merchant_id="merchant_demo_electronics_01",
            name=payload.customer_name or "Alex Retailer",
            email=payload.customer_email or "alex.retail@example.com",
            segment="Standard",
            preferred_channel="EMAIL"
        )
        db.add(customer)
        db.flush()

    payment_service = PaymentService(db)
    payment = payment_service.create_payment(
        merchant_id=customer.merchant_id,
        amount=payload.amount,
        customer_id=customer.customer_id,
        method=payload.method,
        force_failure_reason=payload.failure_reason or payload.failure_code
    )

    # If failed, generate diagnosis and ML prediction
    if payment.status == "FAILED":
        f_class = classifier.classify(payment.failure_code, payment.failure_reason)
        prob, explanation = recovery_model.predict_probability(
            amount=payment.amount,
            payment_method=payment.method,
            failure_category=f_class,
            customer_tenure_months=customer.tenure,
            successful_payments=customer.successful_payments,
            failed_payments=customer.failed_payments,
            customer_segment=customer.segment
        )
        policy = db.query(Policy).filter(Policy.merchant_id == payment.merchant_id).first()
        action, reason, need_appr = decision_engine.select_action(
            amount=payment.amount,
            failure_category=f_class,
            probability=prob,
            expected_value=0.0,
            policy=policy
        )
        cost = expected_value_engine.get_intervention_cost(action)
        ev = expected_value_engine.calculate_expected_value(payment.amount, prob, action, cost)

        pred = Prediction(
            payment_id=payment.payment_id,
            failure_class=f_class,
            recovery_probability=prob,
            expected_value=ev,
            intervention_cost=cost,
            recommended_action=action,
            model_version=recovery_model.version,
            explanation=explanation
        )
        db.add(pred)
        db.commit()
        db.refresh(payment)

    return payment
