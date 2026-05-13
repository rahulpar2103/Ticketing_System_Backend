from app.core.security import hash_password, verify_password, create_access_token, verify_access_token
# pyrefly: ignore [missing-import]
from app.models.userModel import User
# pyrefly: ignore [missing-import]
from app.db.redis import redis_client
# pyrefly: ignore [missing-import]
from app.core.exceptions import PermissionDeniedException
# pyrefly: ignore [missing-import]
from app.schemas.userSchema import UserCreate
# pyrefly: ignore [missing-import]
from app.schemas import UserResponse
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

class AuthService:
    def create_user(self, current_user, user: UserCreate, db: Session):
        if current_user.role != "admin":
            raise PermissionDeniedException("You do not have permission to create a user")
        
        existing_user=db.query(User).filter(User.email == user.email, User.username==user.username).first()
        if existing_user:
            raise Exception("User with this email or username already exists")

        user.hashed_password = hash_password(user.hashed_password)
        new_user=User(**user.dict())
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        keys=redis_client.keys("user:*")
        for key in keys:
            redis_client.delete(key)
        redis_client.delete("all_users:")
        return new_user

    def login(self, user: UserCreate, db: Session):
        existing_user=db.query(User).filter(User.email == user.email).first()
        if not existing_user:
            raise Exception("User with this email does not exist")
        
        if not verify_password(user.hashed_password, existing_user.hashed_password):
            raise Exception("Invalid password")
        
        access_token = create_access_token(data={"sub": existing_user.username})
        return {"access_token": access_token, "token_type": "bearer", "user": existing_user}

auth_service = AuthService()