"""
Search router for property and listing searches
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from core.database import get_db
from core.security import get_current_active_user
from models.user import User
from models.parcel import Parcel
from models.listing import Listing
from models.organization import Organization
from schemas.parcel import ParcelSearch, ParcelSearchResponse, ParcelSummary
from connectors.geocode import GeocodeConnector
from connectors.boundaries import BoundariesConnector

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/parcels", response_model=ParcelSearchResponse)
async def search_parcels(
    search_params: ParcelSearch = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Search parcels with various criteria
    """
    try:
        # Start with base query filtered by organization
        query = db.query(Parcel).filter(
            Parcel.organization_id == current_user.organization_id,
            Parcel.is_active == True
        )
        
        # Apply filters based on search parameters
        if search_params.parcel_id:
            query = query.filter(Parcel.parcel_id.ilike(f"%{search_params.parcel_id}%"))
        
        if search_params.address:
            query = query.filter(Parcel.address.ilike(f"%{search_params.address}%"))
        
        if search_params.city:
            query = query.filter(Parcel.city.ilike(f"%{search_params.city}%"))
        
        if search_params.county:
            query = query.filter(Parcel.county.ilike(f"%{search_params.county}%"))
        
        if search_params.state:
            query = query.filter(Parcel.state.ilike(f"%{search_params.state}%"))
        
        if search_params.postal_code:
            query = query.filter(Parcel.postal_code == search_params.postal_code)
        
        if search_params.property_type:
            query = query.filter(Parcel.property_type == search_params.property_type)
        
        if search_params.zoning_code:
            query = query.filter(Parcel.zoning_code.ilike(f"%{search_params.zoning_code}%"))
        
        # Geographic bounds filtering
        if all([search_params.min_latitude, search_params.max_latitude,
                search_params.min_longitude, search_params.max_longitude]):
            query = query.filter(
                Parcel.latitude.between(search_params.min_latitude, search_params.max_latitude),
                Parcel.longitude.between(search_params.min_longitude, search_params.max_longitude)
            )
        
        # Area filtering
        if search_params.min_area_sqft:
            query = query.filter(Parcel.area_sqft >= search_params.min_area_sqft)
        
        if search_params.max_area_sqft:
            query = query.filter(Parcel.area_sqft <= search_params.max_area_sqft)
        
        # Value filtering
        if search_params.min_assessed_value:
            query = query.filter(Parcel.assessed_value >= search_params.min_assessed_value)
        
        if search_params.max_assessed_value:
            query = query.filter(Parcel.assessed_value <= search_params.max_assessed_value)
        
        # General text search
        if search_params.query:
            search_term = f"%{search_params.query}%"
            query = query.filter(
                (Parcel.parcel_id.ilike(search_term)) |
                (Parcel.address.ilike(search_term)) |
                (Parcel.owner_name.ilike(search_term)) |
                (Parcel.city.ilike(search_term))
            )
        
        # Get total count before pagination
        total = query.count()
        
        # Apply sorting
        if search_params.sort_by == "parcel_id":
            if search_params.sort_order == "desc":
                query = query.order_by(Parcel.parcel_id.desc())
            else:
                query = query.order_by(Parcel.parcel_id.asc())
        elif search_params.sort_by == "address":
            if search_params.sort_order == "desc":
                query = query.order_by(Parcel.address.desc())
            else:
                query = query.order_by(Parcel.address.asc())
        elif search_params.sort_by == "area_sqft":
            if search_params.sort_order == "desc":
                query = query.order_by(Parcel.area_sqft.desc())
            else:
                query = query.order_by(Parcel.area_sqft.asc())
        elif search_params.sort_by == "assessed_value":
            if search_params.sort_order == "desc":
                query = query.order_by(Parcel.assessed_value.desc())
            else:
                query = query.order_by(Parcel.assessed_value.asc())
        else:
            # Default sort by id
            if search_params.sort_order == "desc":
                query = query.order_by(Parcel.id.desc())
            else:
                query = query.order_by(Parcel.id.asc())
        
        # Apply pagination
        parcels = query.offset(search_params.skip).limit(search_params.limit).all()
        
        # Convert to summary format
        results = [ParcelSummary.from_orm(parcel) for parcel in parcels]
        
        return ParcelSearchResponse(
            total=total,
            skip=search_params.skip,
            limit=search_params.limit,
            results=results
        )
    
    except Exception as e:
        logger.error(f"Parcel search error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Parcel search failed"
        )


@router.get("/listings")
async def search_listings(
    query: Optional[str] = Query(None, description="General search query"),
    city: Optional[str] = Query(None, description="City filter"),
    state: Optional[str] = Query(None, description="State filter"),
    property_type: Optional[str] = Query(None, description="Property type filter"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    min_bedrooms: Optional[int] = Query(None, description="Minimum bedrooms"),
    max_bedrooms: Optional[int] = Query(None, description="Maximum bedrooms"),
    status: Optional[str] = Query("active", description="Listing status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Search real estate listings
    """
    try:
        # Base query for listings
        query_builder = db.query(Listing).filter(Listing.is_active == True)
        
        # Apply filters
        if query:
            search_term = f"%{query}%"
            query_builder = query_builder.filter(
                (Listing.address.ilike(search_term)) |
                (Listing.city.ilike(search_term)) |
                (Listing.mls_number.ilike(search_term))
            )
        
        if city:
            query_builder = query_builder.filter(Listing.city.ilike(f"%{city}%"))
        
        if state:
            query_builder = query_builder.filter(Listing.state.ilike(f"%{state}%"))
        
        if property_type:
            query_builder = query_builder.filter(Listing.property_type.ilike(f"%{property_type}%"))
        
        if status:
            query_builder = query_builder.filter(Listing.status == status)
        
        # Price filtering
        if min_price:
            query_builder = query_builder.filter(
                (Listing.list_price >= min_price) | (Listing.monthly_rent >= min_price)
            )
        
        if max_price:
            query_builder = query_builder.filter(
                (Listing.list_price <= max_price) | (Listing.monthly_rent <= max_price)
            )
        
        # Bedroom filtering
        if min_bedrooms:
            query_builder = query_builder.filter(Listing.bedrooms >= min_bedrooms)
        
        if max_bedrooms:
            query_builder = query_builder.filter(Listing.bedrooms <= max_bedrooms)
        
        # Get total count
        total = query_builder.count()
        
        # Apply pagination and get results
        listings = query_builder.order_by(Listing.list_date.desc()).offset(skip).limit(limit).all()
        
        # Convert to response format
        results = []
        for listing in listings:
            listing_data = {
                "id": listing.id,
                "mls_number": listing.mls_number,
                "address": listing.address,
                "city": listing.city,
                "state": listing.state,
                "postal_code": listing.postal_code,
                "property_type": listing.property_type,
                "status": listing.status,
                "list_price": listing.list_price,
                "monthly_rent": listing.monthly_rent,
                "bedrooms": listing.bedrooms,
                "bathrooms": listing.bathrooms,
                "living_area_sqft": listing.living_area_sqft,
                "lot_size_sqft": listing.lot_size_sqft,
                "year_built": listing.year_built,
                "days_on_market": listing.days_on_market,
                "list_date": listing.list_date,
                "source": listing.source
            }
            results.append(listing_data)
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "results": results
        }
    
    except Exception as e:
        logger.error(f"Listing search error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Listing search failed"
        )


@router.get("/geocode")
async def geocode_address(
    address: str = Query(..., description="Address to geocode"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Geocode an address to coordinates
    """
    try:
        async with GeocodeConnector() as geocoder:
            result = await geocoder.geocode(address)
            
            if result.success:
                return {
                    "success": True,
                    "address": address,
                    "coordinates": {
                        "latitude": result.data["latitude"],
                        "longitude": result.data["longitude"]
                    },
                    "formatted_address": result.data.get("formatted_address"),
                    "provider": result.data.get("provider")
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Geocoding failed: {result.error}"
                )
    
    except Exception as e:
        logger.error(f"Geocoding error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Geocoding failed"
        )


@router.get("/reverse-geocode")
async def reverse_geocode(
    latitude: float = Query(..., description="Latitude coordinate"),
    longitude: float = Query(..., description="Longitude coordinate"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Reverse geocode coordinates to address
    """
    try:
        async with GeocodeConnector() as geocoder:
            result = await geocoder.reverse_geocode(latitude, longitude)
            
            if result.success:
                return {
                    "success": True,
                    "coordinates": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "address": result.data.get("formatted_address"),
                    "results": result.data.get("results", []),
                    "provider": result.data.get("provider")
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Reverse geocoding failed: {result.error}"
                )
    
    except Exception as e:
        logger.error(f"Reverse geocoding error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Reverse geocoding failed"
        )


@router.get("/boundaries")
async def get_boundaries(
    latitude: float = Query(..., description="Latitude coordinate"),
    longitude: float = Query(..., description="Longitude coordinate"),
    boundary_types: Optional[List[str]] = Query(None, description="Types of boundaries to retrieve"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get administrative boundaries for a location
    """
    try:
        async with BoundariesConnector() as boundaries:
            result = await boundaries.get_administrative_boundaries(
                latitude, longitude, boundary_types
            )
            
            if result.success:
                return {
                    "success": True,
                    "coordinates": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "boundaries": result.data
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Boundary lookup failed: {result.error}"
                )
    
    except Exception as e:
        logger.error(f"Boundary lookup error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Boundary lookup failed"
        )


@router.get("/nearby")
async def find_nearby_properties(
    latitude: float = Query(..., description="Center latitude"),
    longitude: float = Query(..., description="Center longitude"),
    radius_miles: float = Query(1.0, description="Search radius in miles"),
    property_types: Optional[List[str]] = Query(None, description="Property types to include"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Find nearby properties within a radius
    """
    try:
        # Convert miles to approximate degree difference (rough calculation)
        degree_radius = radius_miles / 69.0  # Approximately 69 miles per degree
        
        # Build query for nearby parcels
        nearby_parcels = db.query(Parcel).filter(
            Parcel.organization_id == current_user.organization_id,
            Parcel.is_active == True,
            Parcel.latitude.between(latitude - degree_radius, latitude + degree_radius),
            Parcel.longitude.between(longitude - degree_radius, longitude + degree_radius)
        )
        
        # Filter by property types if specified
        if property_types:
            nearby_parcels = nearby_parcels.filter(Parcel.property_type.in_(property_types))
        
        # Limit results
        parcels = nearby_parcels.limit(limit).all()
        
        # Calculate actual distances and sort
        results = []
        for parcel in parcels:
            if parcel.latitude and parcel.longitude:
                # Simple distance calculation (not precise for large distances)
                lat_diff = parcel.latitude - latitude
                lon_diff = parcel.longitude - longitude
                distance_degrees = (lat_diff**2 + lon_diff**2)**0.5
                distance_miles = distance_degrees * 69.0
                
                if distance_miles <= radius_miles:
                    results.append({
                        "parcel": ParcelSummary.from_orm(parcel),
                        "distance_miles": round(distance_miles, 2),
                        "coordinates": {
                            "latitude": parcel.latitude,
                            "longitude": parcel.longitude
                        }
                    })
        
        # Sort by distance
        results.sort(key=lambda x: x["distance_miles"])
        
        return {
            "center": {
                "latitude": latitude,
                "longitude": longitude
            },
            "radius_miles": radius_miles,
            "total_found": len(results),
            "properties": results
        }
    
    except Exception as e:
        logger.error(f"Nearby search error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Nearby property search failed"
        )