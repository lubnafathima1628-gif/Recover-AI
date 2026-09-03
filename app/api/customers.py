from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from backend.app.core.database import get_db
from backend.app.models.models import Customer, Payment, Order
from backend.app.schemas.schemas import CustomerResponse, CustomerCreate

router = APIRouter(prefix="/customers", tags=["Customers"])

@router.get("", response_model=List[CustomerResponse])
def list_customers(
    db: Session = Depends(get_db),
    segment: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0
):
    query = db.query(Customer)
    if segment:
        query = query.filter(Customer.segment == segment)
    if search:
        query = query.filter(
            (Customer.name.ilike(f"%{search}%")) |
            (Customer.email.ilike(f"%{search}%"))
        )

    return query.order_by(Customer.lifetime_value.desc()).offset(offset).limit(limit).all()

@router.get("/{id}", response_model=Dict[str, Any])
def get_customer_profile(id: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.customer_id == id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    payments = db.query(Payment).filter(Payment.customer_id == id).order_by(Payment.timestamp.desc()).all()
    
    total_failed = sum(1 for p in payments if p.status == "FAILED")
    total_recovered = sum(1 for p in payments if p.status == "SUCCESS" and p.recovery_attempts)
    rec_rate = (total_recovered / max(total_failed + total_recovered, 1)) * 100

    return {
        "customer": {
            "customer_id": customer.customer_id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "segment": customer.segment,
            "preferred_channel": customer.preferred_channel,
            "tenure": customer.tenure,
            "total_payments": customer.total_payments,
            "successful_payments": customer.successful_payments,
            "failed_payments": customer.failed_payments,
            "lifetime_value": customer.lifetime_value,
            "recovery_rate": round(rec_rate, 1),
            "created_at": customer.created_at
        },
        "payments": [
            {
                "payment_id": p.payment_id,
                "amount": p.amount,
                "method": p.method,
                "status": p.status,
                "failure_code": p.failure_code,
                "failure_reason": p.failure_reason,
                "timestamp": p.timestamp
            } for p in payments
        ]
    }
