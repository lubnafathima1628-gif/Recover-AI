from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.schemas import PredictRequest, PredictionResponse
from backend.app.ml.classifier import classifier
from backend.app.ml.recovery_model import recovery_model
from backend.app.ml.expected_value import expected_value_engine
from backend.app.ml.decision_engine import decision_engine

router = APIRouter(prefix="/predict", tags=["Predictions"])

@router.post("", response_model=dict)
def predict_recovery(payload: PredictRequest, db: Session = Depends(get_db)):
    f_class = classifier.classify(payload.failure_code)
    prob, explanation = recovery_model.predict_probability(
        amount=payload.amount,
        payment_method=payload.method,
        failure_category=f_class,
        customer_tenure_months=payload.customer_tenure or 6,
        successful_payments=payload.previous_successful or 3,
        failed_payments=payload.previous_failed or 1,
        customer_segment=payload.customer_segment or "Standard"
    )

    action, reason, requires_approval = decision_engine.select_action(
        amount=payload.amount,
        failure_category=f_class,
        probability=prob,
        expected_value=0.0
    )

    cost = expected_value_engine.get_intervention_cost(action)
    expected_val = expected_value_engine.calculate_expected_value(payload.amount, prob, action, cost)

    return {
        "failure_class": f_class,
        "recovery_probability": prob,
        "expected_value": expected_val,
        "intervention_cost": cost,
        "recommended_action": action,
        "decision_reason": reason,
        "requires_approval": requires_approval,
        "model_version": recovery_model.version,
        "explanation": explanation
    }
