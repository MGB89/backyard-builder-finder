"""Search schemas for API."""
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime


class AreaResolveRequest(BaseModel):
    """Request to resolve an area."""
    query: Optional[str] = Field(None, description="Text query (address, city, ZIP)")
    polygon: Optional[Dict[str, Any]] = Field(None, description="GeoJSON polygon")


class AreaResolveResponse(BaseModel):
    """Response with resolved area."""
    area_geom: str = Field(..., description="WKT geometry")
    normalized_place: str
    bbox: List[float]
    area_type: str


class SearchPreviewRequest(BaseModel):
    """Request to preview search."""
    area_geom: str = Field(..., description="WKT geometry")
    filters: Dict[str, Any] = Field(default_factory=dict)


class SearchPreviewResponse(BaseModel):
    """Search preview response."""
    estimated_parcels: int
    estimated_costs: Dict[str, Any]
    warnings: List[str]
    sample_results: List[Dict[str, Any]]


class UnitSpec(BaseModel):
    """Unit specification."""
    area_sqft: float
    width: Optional[float] = None
    length: Optional[float] = None
    aspect_ratio: Optional[float] = None
    allow_rotation: bool = True


class SearchExecuteRequest(BaseModel):
    """Request to execute search."""
    name: Optional[str] = None
    area_geom: str = Field(..., description="WKT geometry")
    filters: Dict[str, Any] = Field(default_factory=dict)
    unit: Optional[Dict[str, Any]] = None


class SearchExecuteResponse(BaseModel):
    """Search execution response."""
    job_id: str
    search_id: str
    status: str
    estimated_completion_time: int


class SearchResultsResponse(BaseModel):
    """Search results response."""
    search_id: str
    total_results: int
    page: int
    page_size: int
    results: List[Dict[str, Any]]