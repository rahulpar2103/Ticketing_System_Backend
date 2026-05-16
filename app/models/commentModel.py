# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, ForeignKey, Text, Boolean, DateTime, func
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship
# pyrefly: ignore [missing-import]
from app.db.database import Base

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    comment = Column(Text, nullable=False)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=func.now())
    is_edited = Column(Boolean, default=False)

    #Relationships
    user = relationship("User", back_populates="comments")
    ticket = relationship("Ticket", back_populates="comments")

