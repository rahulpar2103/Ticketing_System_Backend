from pydantic import BaseModel, EmailStr, field_validator
from app.models.userModel import UserRole
import re

def validate_strong_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[@$!%*?&#]", v):
        raise ValueError("Password must contain at least one special character (@, $, !, %, *, ?, &, #)")
    return v

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
    def password_strength(cls, v: str) -> str:
        return validate_strong_password(v)


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
        if v is None:
            return v
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

class PasswordUpdate(BaseModel):
    """For agent/employee: must provide current password to change their own."""
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_strength(cls, v: str) -> str:
        return validate_strong_password(v)


class AdminPasswordReset(BaseModel):
    """For admin: can reset any user's password without knowing the current one."""
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_strength(cls, v: str) -> str:
        return validate_strong_password(v)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str