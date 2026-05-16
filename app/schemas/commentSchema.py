# pyrefly: ignore [missing-import]
from pydantic import BaseModel
from datetime import datetime

class CommentCreate(BaseModel):
    comment: str

class CommentUpdate(BaseModel):
    comment: str

class CommentResponse(BaseModel):
    id: int
    comment: str
    ticket_id: int
    user_id: int | None = None
    username: str | None = None
    is_edited: bool
    created_at: datetime

    model_config = {"from_attributes": True}