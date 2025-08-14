"""
Listing model for real estate listings
"""

from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base


class Listing(Base):
    """Real estate listings associated with parcels"""
    
    __tablename__ = "listings"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4(), index=True)
    
    # Parcel relationship
    parcel_id = Column(UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=False, index=True)
    
    # Listing identification
    mls_number = Column(String(100), nullable=True, unique=True, index=True)
    external_id = Column(String(255), nullable=True, index=True)
    listing_url = Column(String(500), nullable=True)
    
    # Basic listing information
    listing_type = Column(String(50), nullable=True, index=True)  # sale, rent, sold, etc.
    property_type = Column(String(100), nullable=True, index=True)
    property_subtype = Column(String(100), nullable=True)
    
    # Address (may differ from parcel address)
    address = Column(String(500), nullable=True, index=True)
    unit_number = Column(String(50), nullable=True)
    
    # Pricing
    list_price = Column(Float, nullable=True, index=True)
    sale_price = Column(Float, nullable=True, index=True)
    price_per_sqft = Column(Float, nullable=True)
    
    # Property details
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Float, nullable=True)  # Allow half baths
    total_rooms = Column(Integer, nullable=True)
    square_feet = Column(Float, nullable=True)
    lot_size_sqft = Column(Float, nullable=True)
    lot_size_acres = Column(Float, nullable=True)
    year_built = Column(Integer, nullable=True)
    
    # Listing dates
    list_date = Column(DateTime(timezone=True), nullable=True, index=True)
    sale_date = Column(DateTime(timezone=True), nullable=True, index=True)
    off_market_date = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    status = Column(String(50), nullable=True, index=True)  # active, pending, sold, etc.
    days_on_market = Column(Integer, nullable=True)
    
    # Agent/Broker information
    listing_agent_name = Column(String(255), nullable=True)
    listing_agent_phone = Column(String(50), nullable=True)
    listing_agent_email = Column(String(255), nullable=True)
    listing_broker = Column(String(255), nullable=True)
    
    # Description and features
    description = Column(Text, nullable=True)
    features = Column(JSON, nullable=True)  # Amenities, features, etc.
    
    # Photos and media
    photo_urls = Column(JSON, nullable=True)  # Array of photo URLs
    virtual_tour_url = Column(String(500), nullable=True)
    
    # Source information
    data_source = Column(String(100), nullable=True, index=True)
    source_updated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Internal tracking
    is_active = Column(Boolean, default=True, nullable=False)
    last_scraped_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional data
    raw_data = Column(JSON, nullable=True)  # Original listing data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    parcel = relationship("Parcel", back_populates="listings")
    
    def __repr__(self):
        return f"<Listing(id={self.id}, mls_number='{self.mls_number}', address='{self.address}')>"
    
    @property
    def is_for_sale(self):
        """Check if listing is currently for sale"""
        active_sale_statuses = ['active', 'pending', 'contingent']
        return self.status in active_sale_statuses and self.listing_type == 'sale'
    
    @property
    def is_sold(self):
        """Check if listing is sold"""
        return self.status == 'sold' and self.sale_date is not None
    
    @property
    def price_per_sqft_calculated(self):
        """Calculate price per square foot"""
        if self.list_price and self.square_feet:
            return round(self.list_price / self.square_feet, 2)
        return None