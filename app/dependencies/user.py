from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from app.dependencies.db import get_db
from app.models.userModel import User
from app.core.security import verify_access_token
from app.core.exceptions import SessionException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.redis import safe_get

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if safe_get(f"blocklist:{token}"):
        raise SessionException("Token has been revoked")
        
    try:
        username = verify_access_token(token)
    except ValueError:
        raise SessionException("Invalid or expired token")
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user:
        raise SessionException("User not found")
    if not user.is_active:
        raise SessionException("Account is disabled")
    return user