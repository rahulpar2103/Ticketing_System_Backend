# pyrefly: ignore [missing-import]
from fastapi import APIRouter,Depends
# pyrefly: ignore [missing-import]
from app.dependencies.user import get_current_user
# pyrefly: ignore [missing-import]
from app.services.userServices.auth import auth_service
# pyrefly: ignore [missing-import]
from app.schemas.userSchema import UserCreate
# pyrefly: ignore [missing-import]
from app.schemas.userSchema import UserResponse
# pyrefly: ignore [missing-import]
from app.dependencies.db import get_db
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

router= APIRouter(prefix="/auth",tags=["Auth"])

@router.post("/create", status_code=201, response_model=UserResponse)
def create_user(user: UserCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return auth_service.create_user(current_user,user,db)

@router.post("/login", response_model=UserResponse)
def login(user: UserCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return auth_service.login(current_user,user,db)