from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, func
from app.db.database import Base
from pgvector.sqlalchemy import Vector

class VectorDocument(Base):
    __tablename__ = "vector_documents"

    id = Column(Integer, primary_key=True, index=True)
    document_type = Column(String(50), nullable=False)  # 'ticket', 'comment', etc.
    reference_id = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=False)  # 768 dimensions for Google's text-embedding-004
    metadata_json = Column(JSON, nullable=True)      # JSON metadata containing role permissions, team_id, ticket status, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<VectorDocument(id={self.id}, type='{self.document_type}', ref_id={self.reference_id})>"
