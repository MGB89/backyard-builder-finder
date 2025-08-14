"""
Parcel model for property parcel data management
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


class Parcel(Base):
    """Parcel model for property parcels"""
    
    __tablename__ = "parcels"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4(), index=True)
    
    # Parcel identification
    parcel_id = Column(String(100), nullable=False, index=True)  # APN/Parcel ID
    parcel_number = Column(String(100), nullable=True, index=True)
    county_parcel_id = Column(String(100), nullable=True, index=True)
    
    # Location information
    address = Column(String(500), nullable=True, index=True)
    street_number = Column(String(20), nullable=True)
    street_name = Column(String(200), nullable=True)
    unit_number = Column(String(50), nullable=True)
    city = Column(String(100), nullable=True, index=True)
    county = Column(String(100), nullable=True, index=True)
    state = Column(String(50), nullable=True, index=True)
    postal_code = Column(String(20), nullable=True, index=True)
    
    # Geographic data
    geometry = Column(Geometry("POLYGON", srid=4326), nullable=True, index=True)
    centroid = Column(Geometry("POINT", srid=4326), nullable=True, index=True)
    latitude = Column(Float, nullable=True, index=True)
    longitude = Column(Float, nullable=True, index=True)
    
    # Parcel dimensions and characteristics
    area_sqft = Column(Float, nullable=True)
    area_acres = Column(Float, nullable=True)
    frontage_ft = Column(Float, nullable=True)
    depth_ft = Column(Float, nullable=True)
    
    # Zoning information
    zoning_code = Column(String(50), nullable=True, index=True)
    zoning_description = Column(Text, nullable=True)
    land_use_code = Column(String(50), nullable=True)
    land_use_description = Column(Text, nullable=True)
    
    # Property characteristics
    property_type = Column(String(100), nullable=True)
    property_subtype = Column(String(100), nullable=True)
    lot_type = Column(String(50), nullable=True)
    corner_lot = Column(Boolean, default=False)
    
    # Ownership information
    owner_name = Column(String(500), nullable=True)
    owner_address = Column(Text, nullable=True)
    owner_type = Column(String(50), nullable=True)  # individual, corporation, trust, etc.
    
    # Assessment and tax information
    assessed_value = Column(Float, nullable=True)
    market_value = Column(Float, nullable=True)
    tax_year = Column(Integer, nullable=True)
    annual_taxes = Column(Float, nullable=True)
    
    # Building information
    building_count = Column(Integer, default=0)
    total_building_sqft = Column(Float, nullable=True)
    year_built = Column(Integer, nullable=True)
    
    # Utilities and infrastructure
    water_available = Column(Boolean, nullable=True)
    sewer_available = Column(Boolean, nullable=True)
    electric_available = Column(Boolean, nullable=True)
    gas_available = Column(Boolean, nullable=True)
    
    # Development constraints
    flood_zone = Column(String(50), nullable=True)
    wetlands = Column(Boolean, nullable=True)
    steep_slopes = Column(Boolean, nullable=True)
    environmental_constraints = Column(Text, nullable=True)
    
    # Data source and quality
    data_source = Column(String(100), nullable=True)
    data_quality = Column(String(50), default="unknown")  # high, medium, low, unknown
    last_verified = Column(DateTime(timezone=True), nullable=True)
    
    # Additional attributes
    attributes = Column(JSON, nullable=True, default={})
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    footprints = relationship("Footprint", back_populates="parcel", cascade="all, delete-orphan")
    zoning_rules = relationship("ZoningRule", back_populates="parcel", cascade="all, delete-orphan")
    derived_buildable = relationship("DerivedBuildable", back_populates="parcel", cascade="all, delete-orphan")
    cv_artifacts = relationship("CvArtifact", back_populates="parcel", cascade="all, delete-orphan")
    listings = relationship("Listing", back_populates="parcel", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Parcel(id={self.id}, parcel_id='{self.parcel_id}', address='{self.address}')>"
    
    @property
    def full_address(self):
        """Get formatted full address"""
        parts = []
        if self.street_number:
            parts.append(self.street_number)
        if self.street_name:
            parts.append(self.street_name)
        if self.unit_number:
            parts.append(f"Unit {self.unit_number}")
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.postal_code:
            parts.append(self.postal_code)
        
        return " ".join(parts) if parts else self.address
    
    @property
    def coordinates(self):
        """Get latitude/longitude as tuple"""
        if self.latitude and self.longitude:
            return (self.latitude, self.longitude)
        return None