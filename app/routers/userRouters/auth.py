# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, Request
# pyrefly: ignore [missing-import]
from fastapi.security import OAuth2PasswordRequestForm
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from app.core.limiter import limiter
# pyrefly: ignore [missing-import]
from app.dependencies.db import get_db
# pyrefly: ignore [missing-import]
from app.dependencies.user import get_current_user
# pyrefly: ignore [missing-import]
from app.services.userServices.auth import auth_service
# pyrefly: ignore [missing-import]
from app.schemas.userSchema import UserCreate, UserResponse, TokenResponse
# pyrefly: ignore [missing-import]
from fastapi import BackgroundTasks
# pyrefly: ignore [missing-import]
from app.core.email import send_welcome_email

router = APIRouter(tags=["Auth"])

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return auth_service.login(form_data, db)

@router.post("/create", status_code=201, response_model=UserResponse)
@limiter.limit("20/minute")
def create_user(
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
