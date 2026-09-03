from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.models import Policy, Merchant
from backend.app.schemas.schemas import PolicyResponse, PolicyUpdate

router = APIRouter(prefix="/policies", tags=["Merchant Policies"])

@router.get("", response_model=PolicyResponse)
def get_policy(db: Session = Depends(get_db)):
    policy = db.query(Policy).first()
    if not policy:
        merchant = db.query(Merchant).first()
        merchant_id = merchant.merchant_id if merchant else "merchant_demo_electronics_01"
        policy = Policy(merchant_id=merchant_id)
        db.add(policy)
        db.commit()
        db.refresh(policy)
    return policy

@router.put("", response_model=PolicyResponse)
def update_policy(payload: PolicyUpdate, db: Session = Depends(get_db)):
    policy = db.query(Policy).first()
    if not policy:
        merchant = db.query(Merchant).first()
        merchant_id = merchant.merchant_id if merchant else "merchant_demo_electronics_01"
        policy = Policy(merchant_id=merchant_id)
        db.add(policy)

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(policy, field, value)

    db.commit()
    db.refresh(policy)
    return policy
