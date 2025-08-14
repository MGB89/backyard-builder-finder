"""
Parcel schemas for request/response models
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from enum import Enum


class DataQuality(str, Enum):
    """Data quality enumeration"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class PropertyType(str, Enum):
    """Property type enumeration"""
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    AGRICULTURAL = "agricultural"
    MIXED_USE = "mixed_use"
    VACANT = "vacant"
    OTHER = "other"


class ParcelBase(BaseModel):
    """Base parcel model"""
    parcel_id: str = Field(..., min_length=1, max_length=100)
    parcel_number: Optional[str] = Field(None, max_length=100)
    county_parcel_id: Optional[str] = Field(None, max_length=100)
    
    # Location
    address: Optional[str] = Field(None, max_length=500)
    street_number: Optional[str] = Field(None, max_length=20)
    street_name: Optional[str] = Field(None, max_length=200)
    unit_number: Optional[str] = Field(None, max_length=50)
    city: Optional[str] = Field(None, max_length=100)
    county: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    postal_code: Optional[str] = Field(None, max_length=20)
    
    # Coordinates
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    
    # Dimensions
    area_sqft: Optional[float] = Field(None, gt=0)
    area_acres: Optional[float] = Field(None, gt=0)
    frontage_ft: Optional[float] = Field(None, gt=0)
    depth_ft: Optional[float] = Field(None, gt=0)
    
    # Zoning
    zoning_code: Optional[str] = Field(None, max_length=50)
    zoning_description: Optional[str] = None
    land_use_code: Optional[str] = Field(None, max_length=50)
    land_use_description: Optional[str] = None
    
    # Property characteristics
    property_type: Optional[PropertyType] = None
    property_subtype: Optional[str] = Field(None, max_length=100)
    corner_lot: Optional[bool] = False


class ParcelCreate(ParcelBase):
    """Parcel creation model"""
    organization_id: int
    
    # Additional creation fields
    owner_name: Optional[str] = Field(None, max_length=500)
    assessed_value: Optional[float] = Field(None, ge=0)
    market_value: Optional[float] = Field(None, ge=0)
    tax_year: Optional[int] = Field(None, ge=1900, le=2100)
    data_source: Optional[str] = Field(None, max_length=100)


class ParcelUpdate(BaseModel):
    """Parcel update model"""
    parcel_number: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    county: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    postal_code: Optional[str] = Field(None, max_length=20)
    
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    
    area_sqft: Optional[float] = Field(None, gt=0)
    area_acres: Optional[float] = Field(None, gt=0)
    
    zoning_code: Optional[str] = Field(None, max_length=50)
    property_type: Optional[PropertyType] = None
    
    owner_name: Optional[str] = Field(None, max_length=500)
    assessed_value: Optional[float] = Field(None, ge=0)
    market_value: Optional[float] = Field(None, ge=0)
    
    is_active: Optional[bool] = None


class ParcelResponse(ParcelBase):
    """Parcel response model"""
    id: int
    organization_id: int
    
    # Extended fields
    owner_name: Optional[str]
    assessed_value: Optional[float]
    market_value: Optional[float]
    tax_year: Optional[int]
    annual_taxes: Optional[float]
    
    building_count: int
    total_building_sqft: Optional[float]
    year_built: Optional[int]
    
    data_source: Optional[str]
    data_quality: DataQuality
    last_verified: Optional[datetime]
    
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    # Computed properties
    full_address: Optional[str]
    coordinates: Optional[Tuple[float, float]]
    
    class Config:
        from_attributes = True


class ParcelSummary(BaseModel):
    """Parcel summary model for list views"""
    id: int
    parcel_id: str
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    area_sqft: Optional[float]
    area_acres: Optional[float]
    zoning_code: Optional[str]
    property_type: Optional[PropertyType]
    assessed_value: Optional[float]
    building_count: int
    
    class Config:
        from_attributes = True


class ParcelSearch(BaseModel):
    """Parcel search criteria"""
    query: Optional[str] = Field(None, description="General search query")
    parcel_id: Optional[str] = Field(None, description="Parcel ID search")
    address: Optional[str] = Field(None, description="Address search")
    city: Optional[str] = Field(None, description="City filter")
    county: Optional[str] = Field(None, description="County filter")
    state: Optional[str] = Field(None, description="State filter")
    postal_code: Optional[str] = Field(None, description="Postal code filter")
    
    # Geographic bounds
    min_latitude: Optional[float] = Field(None, ge=-90, le=90)
    max_latitude: Optional[float] = Field(None, ge=-90, le=90)
    min_longitude: Optional[float] = Field(None, ge=-180, le=180)
    max_longitude: Optional[float] = Field(None, ge=-180, le=180)
    
    # Property filters
    property_type: Optional[PropertyType] = None
    zoning_code: Optional[str] = None
    min_area_sqft: Optional[float] = Field(None, gt=0)
    max_area_sqft: Optional[float] = Field(None, gt=0)
    min_assessed_value: Optional[float] = Field(None, ge=0)
    max_assessed_value: Optional[float] = Field(None, ge=0)
    
    # Pagination
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=1000, description="Number of records to return")
    
    # Sorting
    sort_by: Optional[str] = Field("id", description="Field to sort by")
    sort_order: Optional[str] = Field("asc", regex="^(asc|desc)$", description="Sort order")
    
    @validator("max_latitude")
    def validate_latitude_range(cls, v, values):
        if v is not None and values.get("min_latitude") is not None:
            if v <= values["min_latitude"]:
                raise ValueError("max_latitude must be greater than min_latitude")
        return v
    
    @validator("max_longitude")
    def validate_longitude_range(cls, v, values):
        if v is not None and values.get("min_longitude") is not None:
            if v <= values["min_longitude"]:
                raise ValueError("max_longitude must be greater than min_longitude")
        return v
    
    @validator("max_area_sqft")
    def validate_area_range(cls, v, values):
        if v is not None and values.get("min_area_sqft") is not None:
            if v <= values["min_area_sqft"]:
                raise ValueError("max_area_sqft must be greater than min_area_sqft")
        return v
    
    @validator("max_assessed_value")
    def validate_value_range(cls, v, values):
        if v is not None and values.get("min_assessed_value") is not None:
            if v <= values["min_assessed_value"]:
                raise ValueError("max_assessed_value must be greater than min_assessed_value")
        return v


class ParcelSearchResponse(BaseModel):
    """Parcel search response model"""
    total: int
    skip: int
    limit: int
    results: List[ParcelSummary]
    
    class Config:
        from_attributes = True


class ParcelImport(BaseModel):
    """Parcel import model"""
    file_url: Optional[str] = Field(None, description="URL to import file")
    file_format: str = Field(..., regex="^(csv|json|geojson|shapefile)$")
    data_source: str = Field(..., max_length=100)
    organization_id: int
    
    # Field mapping
    field_mapping: Optional[Dict[str, str]] = Field(
        None,
        description="Mapping of file fields to parcel attributes"
    )
    
    # Import options
    overwrite_existing: bool = Field(False, description="Overwrite existing parcels")
    validate_geometry: bool = Field(True, description="Validate geometric data")
    geocode_addresses: bool = Field(False, description="Geocode addresses if missing coordinates")


class ParcelImportResponse(BaseModel):
    """Parcel import response model"""
    import_id: str
    status: str
    total_records: int
    processed_records: int
    successful_imports: int
    failed_imports: int
    errors: List[str]
    created_at: datetime


class ParcelGeometry(BaseModel):
    """Parcel geometry model"""
    type: str = Field(..., regex="^(Polygon|MultiPolygon)$")
    coordinates: List[Any]
    
    class Config:
        schema_extra = {
            "example": {
                "type": "Polygon",
                "coordinates": [[
                    [-122.4194, 37.7749],
                    [-122.4194, 37.7751],
                    [-122.4192, 37.7751],
                    [-122.4192, 37.7749],
                    [-122.4194, 37.7749]
                ]]
            }
        }


class ParcelWithGeometry(ParcelResponse):
    """Parcel response with geometry data"""
    geometry: Optional[ParcelGeometry] = None
    centroid: Optional[Dict[str, float]] = None