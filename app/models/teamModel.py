# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, String
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship
# pyrefly: ignore [missing-import]
from app.db.database import Base

class Team(Base):
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    
    # Relationships
    members = relationship("User", back_populates="team")
    tickets = relationship("Ticket", back_populates="team")
    
    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}')>"