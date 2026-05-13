# pyrefly: ignore [missing-import]
from pydantic import BaseModel, EmailStr
from app.models.userModel import UserRole

class UserCreate(BaseModel):
    name: str
    username: str
    email: EmailStr
    password: str          
    role: UserRole
    team_id: int | None = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    team_id: int | None = None
    is_active: bool

    model_config = {"from_attributes": True}

class UserUpdate(BaseModel):
    name: str | None = None
    username: str | None = None
    email: EmailStr | None = None
    role: UserRole | None = None
    team_id: int | None = None

class passwordUpdate(BaseModel):
    current_password: str | None = None #Only for admin. Checks will be there for other roles.
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str