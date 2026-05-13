# pyrefly: ignore [missing-import]
from fastapi import APIRouter
# pyrefly: ignore [missing-import]
from app.schemas.userSchema import UserResponse
# pyrefly: ignore [missing-import]
from app.schemas.userSchema import passwordUpdate
# pyrefly: ignore [missing-import]
from app.dependencies.user import get_current_user
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from app.dependencies.db import get_db
# pyrefly: ignore [missing-import]
from fastapi import Depends

router= APIRouter(prefix="/employee",tags=["Employee"])

@router.get("/get/{user_id}", response_model=UserResponse)
def get_user(user_id: int,current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    pass

@router.patch("update-password/{user_id}", response_model=UserResponse)
def update_user_password(user_id: int,user_update:passwordUpdate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    pass