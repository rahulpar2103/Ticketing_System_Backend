# pyrefly: ignore [missing-import]
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    name: str
    username: str
    email: EmailStr
    password: str          
    role: str
    team_id: int | None = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    team_id: int | None = None
    is_active: bool

    model_config = {"from_attributes": True}

class UserUpdate(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    role: str | None = None
    team_id: int | None = None

class passwordUpdate(BaseModel):
    current_password: str
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str