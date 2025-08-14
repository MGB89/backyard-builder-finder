"""
Footprint models for building footprints, zoning rules, and derived buildable areas
"""

from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Integer, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from core.database import Base
import enum


class FootprintType(enum.Enum):
    """Building footprint types"""
    main = "main"
    outbuilding = "outbuilding"
    driveway = "driveway"


class Footprint(Base):
    """Building footprints extracted from satellite imagery"""
    
    __tablename__ = "footprints"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4(), index=True)
    
    # Parcel relationship
    parcel_id = Column(UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=False, index=True)
    
    # Footprint details
    type = Column(Enum(FootprintType), nullable=False, index=True)
    geometry = Column(Geometry("POLYGON", srid=4326), nullable=False, index=True)
    area_sqft = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Source information
    source_dataset = Column(String(255), nullable=True)
    source_date = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    parcel = relationship("Parcel", back_populates="footprints")
    
    def __repr__(self):
        return f"<Footprint(id={self.id}, parcel_id={self.parcel_id}, type={self.type})>"


class ZoningRule(Base):
    """Zoning rules and constraints for parcels"""
    
    __tablename__ = "zoning_rules"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4(), index=True)
    
    # Parcel relationship
    parcel_id = Column(UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=False, index=True)
    
    # Zoning details
    zoning_code = Column(String(50), nullable=False, index=True)
    zoning_description = Column(Text, nullable=True)
    
    # Setback requirements (in feet)
    front_setback = Column(Float, nullable=True)
    rear_setback = Column(Float, nullable=True)
    side_setback = Column(Float, nullable=True)
    side_setback_total = Column(Float, nullable=True)
    
    # Coverage limits (as percentages)
    max_lot_coverage = Column(Float, nullable=True)
    max_impervious_coverage = Column(Float, nullable=True)
    
    # Height restrictions
    max_height_ft = Column(Float, nullable=True)
    max_stories = Column(Integer, nullable=True)
    
    # Additional rules
    min_lot_size_sqft = Column(Float, nullable=True)
    min_lot_width_ft = Column(Float, nullable=True)
    min_lot_depth_ft = Column(Float, nullable=True)
    
    # Parking requirements
    min_parking_spaces = Column(Integer, nullable=True)
    
    # Additional constraints as JSON
    additional_rules = Column(JSON, nullable=True)
    
    # Source and validity
    source = Column(String(255), nullable=True)
    effective_date = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    parcel = relationship("Parcel", back_populates="zoning_rules")
    
    def __repr__(self):
        return f"<ZoningRule(id={self.id}, parcel_id={self.parcel_id}, zoning_code='{self.zoning_code}')>"


class DerivedBuildable(Base):
    """Derived buildable areas based on zoning rules and constraints"""
    
    __tablename__ = "derived_buildable"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4(), index=True)
    
    # Multi-tenant
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Parcel relationship
    parcel_id = Column(UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=False, index=True)
    
    # Buildable area calculation
    buildable_area = Column(Geometry("POLYGON", srid=4326), nullable=True, index=True)
    buildable_area_sqft = Column(Float, nullable=True)
    
    # Analysis metadata
    analysis_version = Column(String(50), nullable=True)
    calculation_method = Column(String(100), nullable=True)
    
    # Constraints considered
    constraints_applied = Column(JSON, nullable=True)  # List of constraints that were applied
    
    # Quality metrics
    confidence_score = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    parcel = relationship("Parcel", back_populates="derived_buildable")
    organization = relationship("Organization")
    
    def __repr__(self):
        return f"<DerivedBuildable(id={self.id}, parcel_id={self.parcel_id}, area_sqft={self.buildable_area_sqft})>"