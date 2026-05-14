# pyrefly: ignore [missing-import]
from app.core.exceptions import AlreadyExistsException
from app.models.teamModel import Team
from app.db.redis import delete_by_prefix
from app.core.exceptions import NotFoundException
from app.db.redis import redis_client
from app.core.exceptions import PermissionDeniedException
# pyrefly: ignore [missing-import]
from app.schemas.userSchema import UserUpdate
# pyrefly: ignore [missing-import]
from app.schemas.userSchema import passwordUpdate
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from app.models.userModel import User
from app.core.security import hash_password
import json
# pyrefly: ignore [missing-import]
from app.schemas.userSchema import UserResponse

class UserServiceAdmin:
    def get_all_users(self, current_user, db: Session, limit: int, offset: int) -> list[UserResponse]:
        if current_user.role.value != "admin":
            raise PermissionDeniedException("You do not have permission to get all users")

        cache_key = f"all_users:{limit}:{offset}"
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return [UserResponse.model_validate(item) for item in json.loads(cached_data)]

        users = db.query(User).limit(limit).offset(offset).all()
        serialized = [UserResponse.model_validate(u).model_dump(mode="json") for u in users]
        redis_client.setex(cache_key, 60 * 60, json.dumps(serialized))

        return [UserResponse.model_validate(u) for u in users]
        

    def get_user(self, current_user, user_id: int, db: Session) -> UserResponse:
        if current_user.role.value != "admin":
            raise PermissionDeniedException("You do not have permission to get a user")

        cache_key = f"user:{user_id}"
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return UserResponse.model_validate(json.loads(cached_data))

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")

        redis_client.setex(cache_key, 60 * 60, json.dumps(UserResponse.model_validate(user).model_dump(mode="json")))
        return user

    def update_user(self, current_user, user_id: int, user_update: UserUpdate, db: Session)->UserResponse:
        if current_user.role.value != "admin":
            raise PermissionDeniedException("You do not have permission to update a user")
        
        user_obj = db.query(User).filter(User.id == user_id).first()  
        if not user_obj:
            raise NotFoundException("User not found")
        if user_update.username:
            if db.query(User).filter(User.username == user_update.username).first():
                raise AlreadyExistsException("Username already exists")
        if user_update.email:
            if db.query(User).filter(User.email == user_update.email).first():
                raise AlreadyExistsException("Email already exists")
        if user_update.team_id:
            team = db.query(Team).filter(Team.id == user_update.team_id).first()
            if not team:
                raise NotFoundException("Team not found")

        if user_update.name:
            user_obj.name = user_update.name
        if user_update.username:
            user_obj.username = user_update.username
        if user_update.email:
            user_obj.email = user_update.email
        if user_update.role:
            user_obj.role = user_update.role
        if user_update.team_id is not None:
            user_obj.team_id = user_update.team_id

        db.commit()
        db.refresh(user_obj)
        cache_key = f"user:{user_id}"
        redis_client.delete(cache_key)
        delete_by_prefix("all_users:")

        return {"message": f"User {user_id} updated successfully"}

    def delete_user(self,current_user,user_id: int,db: Session):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("You do not have permission to delete a user")
        if current_user.id == user_id:
            raise PermissionDeniedException("You cannot delete yourself")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")
        db.delete(user)
        db.commit()
        redis_client.delete(f"user:{user_id}")
        delete_by_prefix("all_users")  
        return {"message": f"User {user_id} deleted successfully"}

    def update_user_password(self,current_user,user_id: int,user_update:passwordUpdate,db: Session):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("You do not have permission to update a user password")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")
        user.hashed_password = hash_password(user_update.new_password)  
        db.commit()
        db.refresh(user)
        redis_client.delete(f"user:{user_id}")
        delete_by_prefix("all_users")  
        return {"message": f"Password updated successfully for user {user_id}"}

user_service_admin = UserServiceAdmin()