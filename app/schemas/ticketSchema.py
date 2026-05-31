from pydantic import BaseModel, field_validator
from app.models.ticketModel import TicketStatus, Priority
from datetime import datetime

class TicketCreate(BaseModel):
    title: str
    description: str
    priority: Priority
    assigned_to: int | None = None
    team_id: int | None = None

    @field_validator("title", "description", mode="before")
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

    @field_validator("title")
    @classmethod
    def title_length(cls, v: str) -> str:
        if len(v) > 150:
            raise ValueError("Title cannot exceed 150 characters")
        return v

    @field_validator("description")
    @classmethod
    def description_length(cls, v: str) -> str:
        if len(v) > 2000:
            raise ValueError("Description cannot exceed 2000 characters")
        return v

class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TicketStatus | None = None
    assigned_to: int | None = None
    team_id: int | None = None
    priority: Priority | None = None

    @field_validator("title", "description", mode="before")
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

    @field_validator("title")
    @classmethod
    def title_length(cls, v: str) -> str:
        if len(v) > 150:
            raise ValueError("Title cannot exceed 150 characters")
        return v

    @field_validator("description")
    @classmethod
    def description_length(cls, v: str) -> str:
        if len(v) > 2000:
            raise ValueError("Description cannot exceed 2000 characters")
        return v

class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    status: TicketStatus
    priority: Priority
    created_by: int
    created_by_username: str | None = None
    assigned_to: int | None = None
    assigned_to_username: str | None = None
    team_id: int | None = None
    team_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    resolved_at: datetime | None = None
    due_at: datetime | None = None
    sla_breached: bool = False
    comment_count: int = 0
    attachment_count: int = 0
    is_active: bool = True

    model_config = {"from_attributes": True}
