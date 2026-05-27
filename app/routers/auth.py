import logging
from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.limiter import limiter
from app.dependencies.db import get_db
from app.dependencies.user import get_current_user
from app.services.userServices.auth import auth_service
from app.schemas.userSchema import UserCreate, UserResponse, TokenResponse
from app.core.email import send_welcome_email
from app.db.redis import safe_setex
from app.core.config import settings
from app.dependencies.user import oauth2_scheme

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return auth_service.login(form_data, db)

@router.post("/register", status_code=201, response_model=UserResponse)
@limiter.limit("20/minute")
def register(
    request: Request,
    user: UserCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_user = auth_service.create_user(current_user, user, db)
    try:
        send_welcome_email.delay(
            email=user.email,
            username=user.username,
            password=user.password,
        )
    except Exception as e:
        logger.warning(f"Failed to enqueue welcome email for {user.email}: {e}")
    return new_user

@router.post("/logout", status_code=200)
@limiter.limit("5/minute")
def logout(request: Request, token: str = Depends(oauth2_scheme)):
    safe_setex(f"blocklist:{token}", settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, "revoked")
    return {"message": "Successfully logged out"}
