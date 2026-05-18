from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.limiter import limiter
from app.services.userServices.admin import user_service_admin
from app.schemas.userSchema import passwordUpdate, UserResponse, UserUpdate
from app.dependencies.db import get_db
from app.dependencies.user import get_current_user

router = APIRouter(prefix="/users/admin", tags=["Admin Users"])

@router.get("/get-all", response_model=list[UserResponse])
@limiter.limit("30/minute")
def get_all_users(request: Request, current_user=Depends(get_current_user), db: Session = Depends(get_db), limit: int=10, offset: int=0):
    return user_service_admin.get_all_users(current_user, db, limit, offset)

@router.get("/get/{user_id}", response_model=UserResponse)
@limiter.limit("30/minute")
def get_user(request: Request, user_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service_admin.get_user(current_user, user_id, db)

@router.patch("/update/{user_id}", response_model=dict)
@limiter.limit("20/minute")
def update_user(request: Request, user_id: int, user: UserUpdate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service_admin.update_user(current_user, user_id, user, db)

@router.delete("/{user_id}", response_model=dict)
@limiter.limit("20/minute")
def delete_user(request: Request, user_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service_admin.delete_user(current_user, user_id, db)

@router.patch("/update-password/{user_id}", response_model=dict)
@limiter.limit("5/minute")
def update_user_password(request: Request, user_id: int, user_update: passwordUpdate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service_admin.update_user_password(current_user, user_id, user_update, db)