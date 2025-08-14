"""
Computer Vision Artifact model for AI-detected features
"""

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from core.database import Base
import enum


class CvArtifactType(enum.Enum):
    """Computer vision artifact types"""
    pool = "pool"
    tree_canopy = "tree_canopy"
    driveway = "driveway"


class CvArtifact(Base):
    """Computer vision artifacts detected on parcels"""
    
    __tablename__ = "cv_artifacts"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4(), index=True)
    
    # Multi-tenant
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Parcel relationship
    parcel_id = Column(UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=False, index=True)
    
    # Artifact details
    type = Column(Enum(CvArtifactType), nullable=False, index=True)
    geometry = Column(Geometry("POLYGON", srid=4326), nullable=False, index=True)
    
    # Detection metadata
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    model_version = Column(String(50), nullable=True)
    detection_date = Column(DateTime(timezone=True), nullable=False)
    
    # Additional properties
    properties = Column(JSON, nullable=True)  # Type-specific properties
    
    # Quality metrics
    area_sqft = Column(Float, nullable=True)
    perimeter_ft = Column(Float, nullable=True)
    
    # Source information
    source_image_url = Column(String(500), nullable=True)
    source_resolution = Column(String(50), nullable=True)  # e.g., "30cm/pixel"
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    parcel = relationship("Parcel", back_populates="cv_artifacts")
    organization = relationship("Organization")
    
    def __repr__(self):
        return f"<CvArtifact(id={self.id}, type={self.type}, parcel_id={self.parcel_id})>"