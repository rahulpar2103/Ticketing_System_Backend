from app.core.exceptions import AlreadyExistsException
from app.models.teamModel import Team
from app.db.redis import delete_by_prefix, safe_get, safe_setex, safe_delete
from app.core.exceptions import NotFoundException
from app.core.exceptions import PermissionDeniedException
from app.schemas.userSchema import UserUpdate
from app.schemas.userSchema import AdminPasswordReset
from sqlalchemy.orm import Session
from sqlalchemy import or_, asc, desc
from app.models.userModel import User, UserRole
from app.core.security import require_role, hash_password
from app.core.exceptions import ValidationException
import json
from app.schemas.userSchema import UserResponse

# Fields allowed for sorting on users
USER_SORTABLE_FIELDS = {
    "created_at": User.created_at,
    "updated_at": User.updated_at,
    "name": User.name,
    "username": User.username,
    "email": User.email,
    "role": User.role,
}


class UserServiceAdmin:
    def get_all_users(
        self, current_user, db: Session, limit: int, offset: int,
        search: str | None = None, role: str | None = None,
        team_id: int | None = None, is_active: bool | None = None,
        sort_by: str = "created_at", order: str = "desc",
    ) -> dict:
        require_role(current_user, UserRole.admin)

        query = db.query(User)

        # Default to active users only, unless explicitly filtered
        if is_active is None:
            query = query.filter(User.is_active == True)
        else:
            query = query.filter(User.is_active == is_active)

        # Search by name, username, or email
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    User.name.ilike(pattern),
                    User.username.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )

        # Filter by role
        if role:
            role_values = [r.strip() for r in role.split(",") if r.strip()]
            valid_roles = []
            for r in role_values:
                try:
                    valid_roles.append(UserRole(r))
                except ValueError:
                    raise ValidationException(
                        f"Invalid role '{r}'. Allowed: {[rl.value for rl in UserRole]}"
                    )
            if valid_roles:
                query = query.filter(User.role.in_(valid_roles))

        # Filter by team
        if team_id is not None:
            if team_id == 0:
                query = query.filter(User.team_id == None)
            else:
                query = query.filter(User.team_id == team_id)

        # Sorting
        column = USER_SORTABLE_FIELDS.get(sort_by)
        if column is None:
            raise ValidationException(
                f"Invalid sort_by '{sort_by}'. Allowed: {list(USER_SORTABLE_FIELDS.keys())}"
            )
        if order not in ("asc", "desc"):
            raise ValidationException("Invalid order. Allowed: 'asc', 'desc'")
        order_func = asc if order == "asc" else desc
        query = query.order_by(order_func(column))

        # Pagination with metadata
        total = query.count()
        users = query.limit(limit).offset(offset).all()
        items = [UserResponse.model_validate(u) for u in users]

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total,
        }
        

    def get_user(self, current_user, user_id: int, db: Session) -> UserResponse:
        require_role(current_user, UserRole.admin)

        cache_key = f"user:{user_id}"
        cached_data = safe_get(cache_key)
        if cached_data:
            return UserResponse.model_validate(json.loads(cached_data))

        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise NotFoundException("User not found")

        safe_setex(cache_key, 60 * 60, json.dumps(UserResponse.model_validate(user).model_dump(mode="json")))
        return UserResponse.model_validate(user)


    def update_user(self, current_user, user_id: int, user_update: UserUpdate, db: Session) -> dict:
        require_role(current_user, UserRole.admin)
        
        user_obj = db.query(User).filter(User.id == user_id).first()  
        if not user_obj:
            raise NotFoundException("User not found")
        if user_update.username is not None:
            if db.query(User).filter(User.username == user_update.username, User.id != user_id).first():
                raise AlreadyExistsException("Username already exists")
        if user_update.email is not None:
            if db.query(User).filter(User.email == user_update.email, User.id != user_id).first():
                raise AlreadyExistsException("Email already exists")
        if user_update.team_id is not None and user_update.team_id != 0:
            team = db.query(Team).filter(Team.id == user_update.team_id).first()
            if not team:
                raise NotFoundException("Team not found")
            if not team.is_active:
                raise ValidationException(f"Team {user_update.team_id} is deactivated and cannot be assigned")

        role_changed = user_update.role is not None and user_update.role != user_obj.role
        team_changed = user_update.team_id is not None and user_update.team_id != user_obj.team_id

        if user_update.name is not None:
            user_obj.name = user_update.name
        if user_update.username is not None:
            user_obj.username = user_update.username
        if user_update.email is not None:
            user_obj.email = user_update.email
        if user_update.role is not None:
            user_obj.role = user_update.role
        if user_update.team_id is not None:
            if user_update.team_id == 0:
                user_obj.team_id = None
            else:
                user_obj.team_id = user_update.team_id

        db.commit()
        db.refresh(user_obj)

        safe_delete(f"user:{user_id}")
        delete_by_prefix("all_users:")

        if role_changed or team_changed:
            delete_by_prefix(f"tickets:assigned_to_me:{user_id}:")
            delete_by_prefix(f"tickets:assigned_to_user:{user_id}:")
            delete_by_prefix(f"tickets:created:{user_id}:")
            delete_by_prefix(f"tickets:agent:{user_id}:")
            delete_by_prefix(f"tickets:employee:{user_id}:")
            delete_by_prefix(f"comments:ticket:")
            delete_by_prefix(f"tickets:assigned:{user_id}:")

        return {"message": f"User {user_id} updated successfully"}
    
    def delete_user(self,current_user,user_id: int,db: Session):
        require_role(current_user, UserRole.admin)
        if current_user.id == user_id:
            raise PermissionDeniedException("You cannot delete yourself")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")
        user.is_active = False
        db.commit()
        safe_delete(f"user:{user_id}")
        delete_by_prefix("all_users:")
        return {"message": f"User {user_id} deleted successfully"}

    def update_user_password(self, current_user, user_id: int, user_update: AdminPasswordReset, db: Session):
        require_role(current_user, UserRole.admin)
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise NotFoundException("User not found")
        user.hashed_password = hash_password(user_update.new_password)  
        db.commit()
        db.refresh(user)
        safe_delete(f"user:{user_id}")
        delete_by_prefix("all_users:")  
        return {"message": f"Password updated successfully for user {user_id}"}

    def reactivate_user(self, current_user, user_id: int, db: Session):
        """Re-enable a soft-deleted user account. Admin only."""
        require_role(current_user, UserRole.admin)
        user = db.query(User).filter(User.id == user_id, User.is_active == False).first()
        if not user:
            raise NotFoundException("User not found or is already active")
        user.is_active = True
        db.commit()
        safe_delete(f"user:{user_id}")
        delete_by_prefix("all_users:")
        return {"message": f"User {user_id} reactivated successfully"}

user_service_admin = UserServiceAdmin()