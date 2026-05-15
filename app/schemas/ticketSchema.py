# pyrefly: ignore [missing-import]
from pydantic import BaseModel
from app.models.ticketModel import TicketStatus, Priority


class TicketCreate(BaseModel):
    title: str
    description: str
    priority: Priority
    assigned_to: int | None = None
    team_id: int | None = None

class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    status: TicketStatus
    priority: Priority
    created_by: int
    assigned_to: int | None = None
    assigned_to_username: str | None = None
    team_id: int | None = None
    team_name: str | None = None

    class Config:
        from_attributes = True

class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TicketStatus | None = None
    assigned_to: int | None = None
    team_id: int | None = None
    priority: Priority | None = None