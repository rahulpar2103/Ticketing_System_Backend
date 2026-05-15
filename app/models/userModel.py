# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, ForeignKey
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship
# pyrefly: ignore [missing-import]
from datetime import datetime, timezone
# pyrefly: ignore [missing-import]
from app.db.database import Base
# pyrefly: ignore [missing-import]
import enum

class UserRole(enum.Enum):
    admin = "admin"
    employee = "employee"
    agent = "agent"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role= Column(Enum(UserRole), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    team = relationship("Team", back_populates="users")
    assigned_tickets = relationship("Ticket", back_populates="assigned_user", foreign_keys="Ticket.assigned_to")
    created_tickets = relationship("Ticket", back_populates="created_by_user", foreign_keys="Ticket.created_by")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
