from passlib.context import CryptContext
import jwt
from jwt.exceptions import InvalidTokenError
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.models.userModel import User, UserRole
from app.core.exceptions import PermissionDeniedException

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise ValueError("Invalid token")
        return username
    except InvalidTokenError:
        raise ValueError("Invalid token")

def require_role(current_user: User, allowed_roles: UserRole | list[UserRole]):
    """Ensure the user has one of the allowed roles, else raise PermissionDeniedException."""
    if isinstance(allowed_roles, UserRole):
        allowed_roles = [allowed_roles]
    if current_user.role not in allowed_roles:
        raise PermissionDeniedException("Not allowed to access this endpoint")