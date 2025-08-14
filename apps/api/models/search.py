"""
Search model for tracking property searches and queries
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from core.database import Base


class Search(Base):
    """Search model for tracking property searches"""
    
    __tablename__ = "searches"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4(), index=True)
    
    # Multi-tenant
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Search details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Search criteria
    query_text = Column(Text, nullable=True)
    filters = Column(JSON, nullable=True)  # JSON object with search filters
    
    # Geographic search area
    search_area = Column(Geometry("POLYGON", srid=4326), nullable=True, index=True)
    
    # Search results metadata
    result_count = Column(String(50), nullable=True)  # Could be "0", "150", "1000+", etc.
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="searches")
    user = relationship("User", back_populates="searches")
    exports = relationship("Export", back_populates="search", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Search(id={self.id}, name='{self.name}', user_id={self.user_id})>"