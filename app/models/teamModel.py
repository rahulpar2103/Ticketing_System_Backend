# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, String, DateTime, Boolean
# pyrefly: ignore [missing-import]
from app.db.database import Base
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship
# pyrefly: ignore [missing-import]
from datetime import datetime, timezone

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    #Relationships
    users = relationship("User", back_populates="team")

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}', description='{self.description}', is_active={self.is_active})>"