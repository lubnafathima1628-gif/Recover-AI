from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from backend.app.core.database import get_db
from backend.app.payments.simulation_provider import simulation_provider
from backend.app.ml.recovery_model import recovery_model

router = APIRouter(tags=["Health & Status"])

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "service": "RecoverAI Engine API",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if db_ok else "unreachable",
        "simulation_mode": simulation_provider.mode,
        "ml_model_version": recovery_model.version,
        "environment": "local-production-ready"
    }
