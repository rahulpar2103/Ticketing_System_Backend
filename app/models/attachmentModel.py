import enum
from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class AttachmentStatus(enum.Enum):
    pending = "pending"
    uploaded = "uploaded"


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    filename = Column(String, nullable=False)
    s3_key = Column(String, nullable=False, unique=True)
    content_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)  # populated on confirm
    status = Column(Enum(AttachmentStatus), nullable=False, default=AttachmentStatus.pending)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    ticket = relationship("Ticket", back_populates="attachments")
    uploader = relationship("User", foreign_keys=[uploaded_by])

    def __repr__(self):
        return f"<Attachment(id={self.id}, filename='{self.filename}', status='{self.status}')>"
