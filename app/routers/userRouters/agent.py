from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.limiter import limiter
from app.services.userServices.agent import user_service_agent
from app.schemas.userSchema import passwordUpdate, UserResponse
from app.dependencies.db import get_db
from app.dependencies.user import get_current_user

router = APIRouter(prefix="/users/agent", tags=["Agent Users"])

@router.get("/get/{user_id}", response_model=UserResponse)
@limiter.limit("30/minute")
def get_user(request: Request, user_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service_agent.get_user(current_user, user_id, db)

@router.patch("/update-password/{user_id}", response_model=dict)
@limiter.limit("5/minute")
def update_user_password(request: Request, user_id: int, user_update: passwordUpdate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service_agent.update_user_password(current_user, user_id, user_update, db)