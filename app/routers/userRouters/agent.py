from app.services.userServices.agent import user_service_agent
# pyrefly: ignore [missing-import]
from app.schemas.userSchema import passwordUpdate
# pyrefly: ignore [missing-import]
from app.schemas.userSchema import UserResponse
# pyrefly: ignore [missing-import]
from fastapi import APIRouter,Depends
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from app.dependencies.db import get_db
# pyrefly: ignore [missing-import]
from app.dependencies.user import get_current_user

router= APIRouter(prefix="/users/agent",tags=["Agent Users"])

@router.get("/get/{user_id}", response_model=UserResponse)
def get_user(user_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service_agent.get_user(current_user,user_id,db)

@router.patch("/update-password/{user_id}", response_model=dict)
def update_user_password(user_id: int,user_update:passwordUpdate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    message = user_service_agent.update_user_password(current_user,user_id,user_update,db)
    return message