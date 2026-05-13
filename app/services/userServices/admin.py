# pyrefly: ignore [missing-import]
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
    def create_user(self,current_user,user:UserCreate,db: Session):
        if current_user.role != "admin":
            raise PermissionDeniedException("You do not have permission to create a user")
        
        existing_user=db.query(User).filter(User.email == user.email).first()
        if existing_user:
            raise Exception("User with this email already exists")

        user.hashed_password = hash_password(user.hashed_password)
        new_user=User(**user.dict())
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        keys=redis_client.keys("user:*")
        for key in keys:
            redis_client.delete(key)
        redis_client.delete("all_users")
        return new_user
        
    
    def get_all_users(self,current_user,db: Session,limit:int,offset:int):
        pass

    def get_user(self,current_user,user_id: int,db: Session):
        pass

    def update_user(self,current_user,user_id: int,user:UserUpdate,db: Session):
        pass

    def delete_user(self,current_user,user_id: int,db: Session):
        pass

    def update_user_password(self,current_user,user_id: int,user_update:passwordUpdate,db: Session):
        pass

user_service_admin = UserServiceAdmin()