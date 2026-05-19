from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from app.db.database import Base
from sqlalchemy.orm import relationship

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    users = relationship("User", back_populates="team")

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}', description='{self.description}', is_active={self.is_active})>"