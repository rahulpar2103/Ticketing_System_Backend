from pydantic import BaseModel, field_validator
from datetime import datetime

class CommentCreate(BaseModel):
    comment: str

    @field_validator("comment", mode="before")
    @classmethod
    def strip_and_reject_empty(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Must be a string")
        v = v.strip()
        if not v:
            raise ValueError("Comment cannot be empty or whitespace")
        if len(v) > 2000:
            raise ValueError("Comment cannot exceed 2000 characters")
        return v

class CommentUpdate(BaseModel):
    comment: str

    @field_validator("comment", mode="before")
    @classmethod
    def strip_and_reject_empty(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Must be a string")
        v = v.strip()
        if not v:
            raise ValueError("Comment cannot be empty or whitespace")
        if len(v) > 2000:
            raise ValueError("Comment cannot exceed 2000 characters")
        return v


class CommentResponse(BaseModel):
    id: int
    comment: str
    ticket_id: int
    user_id: int | None = None
    username: str | None = None
    is_edited: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
