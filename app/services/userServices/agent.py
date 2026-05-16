from app.core.exceptions import MissingCredentialException
from app.db.redis import delete_by_prefix
from app.core.security import verify_password
from app.core.exceptions import InvalidCredentialsException
from app.schemas.userSchema import UserResponse
import json
from app.db.redis import redis_client
from app.core.exceptions import NotFoundException
# pyrefly: ignore [missing-import]
from app.models.userModel import User
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from app.core.exceptions import PermissionDeniedException
# pyrefly: ignore [missing-import]
from app.core.security import hash_password
# pyrefly: ignore [missing-import]
from app.schemas.userSchema import passwordUpdate

class UserServiceAgent:
    def get_user(self, current_user, user_id: int, db: Session) -> UserResponse:
        cache_key = f"user:{user_id}"
        cached_data = redis_client.get(cache_key)
        target_user = UserResponse.model_validate(json.loads(cached_data)) if cached_data else None

        if current_user.role.value == "agent":
            if current_user.id != user_id:
                if target_user is None:
                    target_user = db.query(User).filter(User.id == user_id).first()
                    if not target_user:
                        raise NotFoundException("User not found")
                if current_user.team_id is None or current_user.team_id != target_user.team_id:
                    raise PermissionDeniedException("You can only view your own profile or your teammates.")
        elif current_user.role.value == "employee" or current_user.role.value=="admin":
            raise PermissionDeniedException("Not authorized to access this endpoint.")
        if target_user:
            return target_user

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")

        redis_client.setex(cache_key, 60 * 60, json.dumps(UserResponse.model_validate(user).model_dump(mode="json")))
        return UserResponse.model_validate(user)

    
    def update_user_password(self,current_user,user_id: int,user_update:passwordUpdate,db: Session):
        if current_user.role.value != "agent" and current_user.role.value != "admin":
            raise PermissionDeniedException("You are not authorized to perform this action")
        if current_user.id != user_id:
            raise PermissionDeniedException("You can change only your own password")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")
        if not user_update.current_password:
            raise MissingCredentialException("Current password is required")
        if not verify_password(user_update.current_password, user.hashed_password):
            raise InvalidCredentialsException("Current password is incorrect")
        if not user_update.new_password:
            raise MissingCredentialException("New password is required")
        if len(user_update.new_password) < 8:
            raise InvalidCredentialsException("New password must be at least 8 characters long")
        user.hashed_password = hash_password(user_update.new_password)  
        db.commit()
        db.refresh(user)
        redis_client.delete(f"user:{user_id}")
        delete_by_prefix("all_users:")  
        return {"message": f"Password updated successfully for user {user_id}"}

user_service_agent = UserServiceAgent()