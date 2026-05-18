# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, func, Boolean      
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship
# pyrefly: ignore [missing-import]
from app.db.database import Base
import enum
# pyrefly: ignore [missing-import]
import sqlalchemy as sa

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
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True, default=None)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True, nullable=False, server_default=sa.true())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    assigned_user = relationship("User", back_populates="assigned_tickets", foreign_keys=[assigned_to])
    created_by_user = relationship("User", back_populates="created_tickets", foreign_keys=[created_by])
    team = relationship("Team", foreign_keys=[team_id])
    comments = relationship("Comment", back_populates="ticket", passive_deletes=True)

    def __repr__(self):
        return f"<Ticket(id={self.id}, title='{self.title}', status='{self.status}')>"