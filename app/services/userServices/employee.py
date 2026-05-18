from app.db.redis import safe_setex, safe_get
from app.core.exceptions import MissingCredentialException
import json
from app.core.exceptions import InvalidCredentialsException
from app.core.security import verify_password
from app.core.exceptions import NotFoundException
from app.models.userModel import User, UserRole
from sqlalchemy.orm import Session
from app.core.exceptions import PermissionDeniedException
from app.core.security import hash_password
from app.schemas.userSchema import PasswordUpdate
from app.schemas.userSchema import UserResponse
class UserServiceEmployee:
    def get_user(self, current_user, user_id: int, db: Session) -> UserResponse:
        if current_user.role != UserRole.employee or current_user.id != user_id:
            raise PermissionDeniedException("You can only view your own profile")
        cache_key = f"user:{user_id}"
        cache_data = safe_get(cache_key)
        if cache_data:
            return UserResponse.model_validate(json.loads(cache_data))
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise NotFoundException("User not found")
        safe_setex(cache_key, 3600, json.dumps(UserResponse.model_validate(user).model_dump(mode="json")))
        return UserResponse.model_validate(user)

    
    def update_user_password(self, current_user, user_id: int, user_update: PasswordUpdate, db: Session):
        if current_user.role != UserRole.employee or current_user.id != user_id:
            raise PermissionDeniedException("You can change only your own password")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")
        if not verify_password(user_update.current_password, user.hashed_password):
            raise InvalidCredentialsException("Current password is incorrect")

        user.hashed_password = hash_password(user_update.new_password)  
        db.commit()
        db.refresh(user)
        return {"message": f"Password updated successfully for user {user_id}"}

user_service_employee = UserServiceEmployee()