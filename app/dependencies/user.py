# pyrefly: ignore [missing-import]
from fastapi import Depends
# pyrefly: ignore [missing-import]
from fastapi.security import OAuth2PasswordBearer
# pyrefly: ignore [missing-import]
from app.dependencies.db import get_db
from app.models.userModel import User
from app.core.security import verify_access_token
from app.core.exceptions import SessionException
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from sqlalchemy import select

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        username = verify_access_token(token)
    except ValueError:
        raise SessionException("Invalid or expired token")
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user:
        raise SessionException("User not found")
    return user