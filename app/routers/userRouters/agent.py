# pyrefly: ignore [missing-import]
from app.schemas.userSchema import passwordUpdate
# pyrefly: ignore [missing-import]
from fastapi import APIRouter,Depends
# pyrefly: ignore [missing-import]
from app.dependencies.user import get_current_user
# pyrefly: ignore [missing-import]
from app.dependencies.db import get_db
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

router= APIRouter(prefix="/agent",tags=["Agent"])

@router.get("/get-user")
def get_user(current_user=Depends(get_current_user),db: Session = Depends(get_db)):
    pass

@router.get("/get-team-members")
def get_team_members(current_user=Depends(get_current_user),db: Session = Depends(get_db)):
    pass

@router.patch("/update-password/{user_id}")
def update_user_password(user_id: int,user_update:passwordUpdate, current_user=Depends(get_current_user),db: Session = Depends(get_db)):
    pass
