# pyrefly: ignore [missing-import]
from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str
    hashed_password: str
    role: str
    team_id: int | None=None

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    team_id: int | None=None

class UserUpdate(BaseModel):
    name: str | None=None
    email: str | None=None
    role: str | None=None
    team_id: int | None=None

class passwordUpdate(BaseModel):
    current_password: str
    new_password: str