# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.database import Base
# pyrefly: ignore [missing-import]
import enum

class TicketStatus(enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"

class Priority(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    priority = Column(Enum(Priority), nullable=False, default=Priority.low)
    status = Column(Enum(TicketStatus), nullable=False, default=TicketStatus.open)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    assigned_user = relationship("User", back_populates="assigned_tickets", foreign_keys=[assigned_to])
    created_by_user = relationship("User", back_populates="created_tickets", foreign_keys=[created_by])

    def __repr__(self):
        return f"<Ticket(id={self.id}, title='{self.title}', status='{self.status}')>"