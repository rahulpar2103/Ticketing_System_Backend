from app.models.userModel import UserRole
from app.core.security import hash_password, verify_password, create_access_token
from app.models.userModel import User
from app.db.redis import redis_client
from app.core.exceptions import PermissionDeniedException, InvalidCredentialsException, AlreadyExistsException
from app.schemas.userSchema import UserCreate, UserResponse, TokenResponse
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from sqlalchemy import select, or_


class AuthService:

    def create_user(self, current_user: User, user: UserCreate, db: Session) -> UserResponse:
        """Admin-only: create a new user account."""
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Only admins can create users")

        existing = db.execute(
            select(User).where(
                or_(User.email == user.email, User.username == user.username)
            )
        ).scalar_one_or_none()
        if existing:
            raise AlreadyExistsException("A user with that email or username already exists")

        new_user = User(
            name=user.name,
            username=user.username,
            email=user.email,
            hashed_password=hash_password(user.password),
            role=UserRole(user.role),
            team_id=user.team_id,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Bust paginated user list cache
        redis_client.delete("all_users")
        for key in redis_client.scan_iter("user:*"):
            redis_client.delete(key)

        return new_user

    def login(self, form_data, db: Session) -> TokenResponse:
        """Public: authenticate with username (or email) + password, return a JWT."""
        identifier = form_data.username   

        if "@" in identifier:
            user = db.execute(select(User).where(User.email == identifier)).scalar_one_or_none()
        else:
            user = db.execute(select(User).where(User.username == identifier)).scalar_one_or_none()

        if not user:
            raise InvalidCredentialsException()
        if not user.is_active:
            raise InvalidCredentialsException("Account is disabled")
        if not verify_password(form_data.password, user.hashed_password):
            raise InvalidCredentialsException()

        access_token = create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}


auth_service = AuthService()