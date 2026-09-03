from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.schemas import AgentQueryRequest, AgentQueryResponse
from backend.app.services.llm_service import llm_service

router = APIRouter(prefix="/agent", tags=["AI Analyst"])

@router.post("/query", response_model=AgentQueryResponse)
def query_ai_analyst(payload: AgentQueryRequest, db: Session = Depends(get_db)):
    result = llm_service.query_analyst(query=payload.query, db=db)
    return result
