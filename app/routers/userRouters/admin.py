from app.services.userServices.admin import user_service_admin
# pyrefly: ignore [missing-import]
from app.schemas.userSchema import passwordUpdate
# pyrefly: ignore [missing-import]
from app.schemas.userSchema import UserResponse,UserUpdate
# pyrefly: ignore [missing-import]
from fastapi import APIRouter,Depends
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from app.dependencies.db import get_db
# pyrefly: ignore [missing-import]
from app.dependencies.user import get_current_user

router= APIRouter(prefix="/admin",tags=["Admin" ])

@router.get("/get-all", response_model=list[UserResponse])
def get_all_users(current_user=Depends(get_current_user),db: Session = Depends(get_db), limit: int=10, offset: int=0):
    return user_service_admin.get_all_users(current_user,db,limit,offset)

@router.get("/get/{user_id}", response_model=UserResponse)
def get_user(user_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service_admin.get_user(current_user,user_id,db)

@router.patch("/update/{user_id}", response_model=UserResponse)
def update_user(user_id: int,user:UserUpdate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service_admin.update_user(current_user,user_id,user,db)

@router.delete("/{user_id}", response_model=UserResponse)
def delete_user(user_id: int,current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service_admin.delete_user(current_user,user_id,db)

@router.patch("/update-password/{user_id}", response_model=UserResponse)
def update_user_password(user_id: int,user_update:passwordUpdate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service_admin.update_user_password(current_user,user_id,user_update,db)