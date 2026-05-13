# pyrefly: ignore [missing-import]
from app.core.exceptions import NotFoundException
from app.db.redis import redis_client
from app.core.exceptions import PermissionDeniedException
from app.schemas.userSchema import UserCreate
# pyrefly: ignore [missing-import]
from app.schemas.userSchema import UserUpdate
# pyrefly: ignore [missing-import]
from app.schemas.userSchema import passwordUpdate
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from app.models.userModel import User
from app.core.security import hash_password

class UserServiceAdmin:
    def get_all_users(self,current_user,db: Session,limit:int,offset:int):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("You do not have permission to get all users")
        return db.query(User).limit(limit).offset(offset).all()

    def get_user(self,current_user,user_id: int,db: Session):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("You do not have permission to get a user")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")
        return user

    def update_user(self, current_user, user_id: int, user: UserUpdate, db: Session):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("You do not have permission to update a user")
        
        user_obj = db.query(User).filter(User.id == user_id).first()  # rename to user_obj
        if not user_obj:
            raise NotFoundException("User not found")
        
        for key, value in user.model_dump(exclude_unset=True).items():
            setattr(user_obj, key, value)                               
        
        db.commit()
        db.refresh(user_obj)
        return user_obj

    def delete_user(self,current_user,user_id: int,db: Session):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("You do not have permission to delete a user")
        if current_user.id == user_id:
            raise PermissionDeniedException("You cannot delete yourself")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")
        db.query(User).filter(User.id == user_id).delete()
        db.commit()
        return user

    def update_user_password(self,current_user,user_id: int,user_update:passwordUpdate,db: Session):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("You do not have permission to update a user password")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")
        user.hashed_password = hash_password(user_update.new_password)  
        db.commit()
        db.refresh(user)
        return user

user_service_admin = UserServiceAdmin()