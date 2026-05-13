# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends
# pyrefly: ignore [missing-import]
from fastapi.security import OAuth2PasswordRequestForm
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.user import get_current_user
from app.services.userServices.auth import auth_service
from app.schemas.userSchema import UserCreate, UserResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Public endpoint — no token required. Accepts username or email in the username field."""
    return auth_service.login(form_data, db)


@router.post("/create", status_code=201, response_model=UserResponse)
def create_user(
    user: UserCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Admin-only — requires a valid Bearer token."""
    return auth_service.create_user(current_user, user, db)