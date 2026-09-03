from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from backend.app.core.database import get_db
from backend.app.schemas.schemas import AnalyticsSummary, LeakageAnalytics, ActionPerformance
from backend.app.services.analytics_service import analytics_service
from backend.app.ml.evaluation import model_evaluator

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/summary", response_model=AnalyticsSummary)
def get_analytics_summary(db: Session = Depends(get_db)):
    return analytics_service.get_summary(db)

@router.get("/leakage", response_model=LeakageAnalytics)
def get_leakage_breakdown(db: Session = Depends(get_db)):
    return analytics_service.get_leakage_breakdown(db)

@router.get("/actions", response_model=List[ActionPerformance])
def get_action_performance(db: Session = Depends(get_db)):
    return analytics_service.get_action_performance(db)

@router.get("/ml-metrics")
def get_ml_metrics():
    return model_evaluator.get_evaluation_metrics()

@router.get("/trends")
def get_trend_series(days: int = Query(7, le=90), db: Session = Depends(get_db)):
    return analytics_service.get_trend_series(db, days=days)
