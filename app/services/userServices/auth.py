from app.core.exceptions import NotFoundException
from app.db.redis import safe_delete, delete_by_prefix
from app.models.userModel import UserRole, User
from app.models.teamModel import Team
from app.core.security import hash_password, verify_password, create_access_token
from app.core.exceptions import PermissionDeniedException, InvalidCredentialsException, AlreadyExistsException
from app.schemas.userSchema import UserCreate, UserResponse, TokenResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, or_


class AuthService:

    def create_user(self, current_user: User, user: UserCreate, db: Session) -> UserResponse:
        """Admin-only: create a new user account."""
        if current_user.role != UserRole.admin:
            raise PermissionDeniedException("Only admins can create users")

        existing = db.execute(
            select(User).where(
                or_(User.email == user.email, User.username == user.username)
            )
        ).scalar_one_or_none()

        if existing:
            raise AlreadyExistsException("A user with that email or username already exists")

        if '@' in user.username or '.' in user.username:
            raise AlreadyExistsException("Username cannot contain @ or .")

        if user.team_id is not None:
            team = db.query(Team).filter(Team.id == user.team_id).first()
            if not team:
                raise NotFoundException(f"Team {user.team_id} not found")

        new_user = User(
            name=user.name,
            username=user.username,
            email=user.email,
            hashed_password=hash_password(user.password),
            role=user.role,
            team_id=user.team_id,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        delete_by_prefix("all_users:")
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