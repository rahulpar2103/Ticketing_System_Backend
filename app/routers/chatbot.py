from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.dependencies.db import get_db
from app.dependencies.user import get_current_user
from app.models.userModel import User
from app.services.rag_service import generate_chatbot_response

router = APIRouter()

class ChatMessage(BaseModel):
    role: str  # 'user' or 'model'
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

@router.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Endpoint to receive user chat messages, retrieve profile-scoped context, 
    and return the generated chatbot answer.
    """
    # Convert Pydantic models to standard list of dicts for the service layer
    history_list = [{"role": msg.role, "content": msg.content} for msg in request.history]
    
    try:
        response_text = generate_chatbot_response(
            db=db,
            query=request.message,
            chat_history=history_list,
            user=current_user
        )
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
