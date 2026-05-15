# pyrefly: ignore [missing-import]
from pydantic import BaseModel
from datetime import datetime
# pyrefly: ignore [missing-import]
from .userSchema import UserBase
# pyrefly: ignore [missing-import]
from app.models.ticketModel import TicketStatus, Priority


class TicketCreate(BaseModel):
    title: str
    description: str
    created_by: int
    assigned_to: int | None = None
    priority: Priority

class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    status: TicketStatus = TicketStatus.open
    created_by: int
    assigned_to: int | None = None
    priority: Priority

    class Config:
        from_attributes = True

class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TicketStatus | None = None
    assigned_to: int | None = None
    priority: Priority | None = None
