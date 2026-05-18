from pydantic import BaseModel, EmailStr, field_validator
from app.models.userModel import UserRole

class UserCreate(BaseModel):
    name: str
    username: str
    email: EmailStr
    password: str
    role: UserRole
    team_id: int | None = None

    @field_validator("name", "username", mode="before")
    @classmethod
    def strip_and_reject_empty(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Must be a string")
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        return v

    @field_validator("username")
    @classmethod
    def username_length(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 50:
            raise ValueError("Username cannot exceed 50 characters")
        return v

    @field_validator("name")
    @classmethod
    def name_length(cls, v: str) -> str:
        if len(v) > 100:
            raise ValueError("Name cannot exceed 100 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserResponse(BaseModel):
    id: int
    name: str
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

    @field_validator("name", "username", mode="before")
    @classmethod
    def strip_and_reject_empty(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Must be a string")
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        return v

    @field_validator("username")
    @classmethod
    def username_length(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 50:
            raise ValueError("Username cannot exceed 50 characters")
        return v

    @field_validator("name")
    @classmethod
    def name_length(cls, v: str) -> str:
        if len(v) > 100:
            raise ValueError("Name cannot exceed 100 characters")
        return v

class passwordUpdate(BaseModel):
    current_password: str | None = None #Only for admin. Checks will be there for other roles.
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str