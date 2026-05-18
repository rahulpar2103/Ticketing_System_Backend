from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.limiter import limiter
from app.dependencies.db import get_db
from app.dependencies.user import get_current_user
from app.services.userServices.auth import auth_service
from app.schemas.userSchema import UserCreate, UserResponse, TokenResponse
from fastapi import BackgroundTasks
from app.core.email import send_welcome_email

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
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_user = auth_service.create_user(current_user, user, db)
    background_tasks.add_task(
        send_welcome_email,
        email=user.email,
        username=user.username,
        password=user.password,
    )
    return new_user
