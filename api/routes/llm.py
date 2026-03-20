from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Query
from sqlalchemy.orm import Session

from db.database import get_db
from api.services.auth_service import get_current_user
from api.schemas.llm import LlmResponse
from api.services import llm_service

router = APIRouter(prefix="/llm", tags=["llm"])

@router.get("/ask", response_model=LlmResponse)
async def ask_question(
    query: str, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    answer, sources = llm_service.get_answer_from_agent(query, current_user.id, db)
    return LlmResponse.model_validate({
        "question": query,
        "answer": answer,
        "sources": sources
    })
