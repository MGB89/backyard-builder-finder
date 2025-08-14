"""
Parcels router for parcel management and property analysis
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from core.database import get_db
from core.security import get_current_active_user
from models.user import User
from models.parcel import Parcel
from models.building_footprint import BuildingFootprint
from models.zoning_district import ZoningDistrict
from schemas.parcel import (
    ParcelCreate, ParcelUpdate, ParcelResponse, ParcelWithGeometry,
    ParcelImport, ParcelImportResponse
)
from services.setbacks import SetbackAnalysisService
from services.backyard import BackyardAnalysisService
from services.obstacles import ObstacleAnalysisService
from services.fit_test import FitTestService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=ParcelResponse)
async def create_parcel(
    parcel_data: ParcelCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new parcel
    """
    try:
        # Check if parcel ID already exists in organization
        existing_parcel = db.query(Parcel).filter(
            Parcel.organization_id == parcel_data.organization_id,
            Parcel.parcel_id == parcel_data.parcel_id
        ).first()
        
        if existing_parcel:
            raise HTTPException(
                status_code=400,
                detail="Parcel ID already exists in organization"
            )
        
        # Verify user has access to organization
        if (current_user.organization_id != parcel_data.organization_id and 
            current_user.role != "admin"):
            raise HTTPException(
                status_code=403,
                detail="Access denied to this organization"
            )
        
        # Create parcel
        parcel = Parcel(**parcel_data.dict())
        db.add(parcel)
        db.commit()
        db.refresh(parcel)
        
        return ParcelResponse.from_orm(parcel)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Parcel creation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Parcel creation failed"
        )


@router.get("/{parcel_id}", response_model=ParcelResponse)
async def get_parcel(
    parcel_id: int,
    include_geometry: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get parcel by ID
    """
    try:
        parcel = db.query(Parcel).filter(
            Parcel.id == parcel_id,
            Parcel.organization_id == current_user.organization_id
        ).first()
        
        if not parcel:
            raise HTTPException(
                status_code=404,
                detail="Parcel not found"
            )
        
        if include_geometry:
            return ParcelWithGeometry.from_orm(parcel)
        else:
            return ParcelResponse.from_orm(parcel)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get parcel error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve parcel"
        )


@router.put("/{parcel_id}", response_model=ParcelResponse)
async def update_parcel(
    parcel_id: int,
    parcel_update: ParcelUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update parcel information
    """
    try:
        parcel = db.query(Parcel).filter(
            Parcel.id == parcel_id,
            Parcel.organization_id == current_user.organization_id
        ).first()
        
        if not parcel:
            raise HTTPException(
                status_code=404,
                detail="Parcel not found"
            )
        
        # Update parcel fields
        for field, value in parcel_update.dict(exclude_unset=True).items():
            if hasattr(parcel, field):
                setattr(parcel, field, value)
        
        db.commit()
        db.refresh(parcel)
        
        return ParcelResponse.from_orm(parcel)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Parcel update error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Parcel update failed"
        )


@router.delete("/{parcel_id}")
async def delete_parcel(
    parcel_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete parcel (soft delete)
    """
    try:
        parcel = db.query(Parcel).filter(
            Parcel.id == parcel_id,
            Parcel.organization_id == current_user.organization_id
        ).first()
        
        if not parcel:
            raise HTTPException(
                status_code=404,
                detail="Parcel not found"
            )
        
        # Soft delete
        parcel.is_active = False
        db.commit()
        
        return {"message": "Parcel deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Parcel deletion error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Parcel deletion failed"
        )


@router.get("/{parcel_id}/buildings")
async def get_parcel_buildings(
    parcel_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get building footprints for a parcel
    """
    try:
        # Verify parcel access
        parcel = db.query(Parcel).filter(
            Parcel.id == parcel_id,
            Parcel.organization_id == current_user.organization_id
        ).first()
        
        if not parcel:
            raise HTTPException(
                status_code=404,
                detail="Parcel not found"
            )
        
        # Get building footprints
        buildings = db.query(BuildingFootprint).filter(
            BuildingFootprint.parcel_id == parcel_id
        ).all()
        
        building_data = []
        for building in buildings:
            building_info = {
                "id": building.id,
                "building_id": building.building_id,
                "building_name": building.building_name,
                "building_type": building.building_type,
                "area_sqft": building.area_sqft,
                "height_ft": building.height_ft,
                "stories": building.stories,
                "year_built": building.year_built,
                "condition": building.condition,
                "is_primary_structure": building.is_primary_structure,
                "data_source": building.data_source,
                "created_at": building.created_at
            }
            building_data.append(building_info)
        
        return {
            "parcel_id": parcel_id,
            "building_count": len(building_data),
            "total_building_area_sqft": sum(b.get("area_sqft", 0) for b in building_data),
            "buildings": building_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get parcel buildings error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve parcel buildings"
        )


@router.post("/{parcel_id}/analyze/setbacks")
async def analyze_parcel_setbacks(
    parcel_id: int,
    zoning_setbacks: dict,
    proposed_building: Optional[dict] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Analyze setback requirements for a parcel
    """
    try:
        # Get parcel
        parcel = db.query(Parcel).filter(
            Parcel.id == parcel_id,
            Parcel.organization_id == current_user.organization_id
        ).first()
        
        if not parcel:
            raise HTTPException(
                status_code=404,
                detail="Parcel not found"
            )
        
        # Get existing buildings
        buildings = db.query(BuildingFootprint).filter(
            BuildingFootprint.parcel_id == parcel_id
        ).all()
        
        existing_buildings = []
        for building in buildings:
            if building.geometry:
                existing_buildings.append({
                    "id": building.id,
                    "geometry": building.geometry
                })
        
        # Create parcel geometry dict
        parcel_geometry = {
            "type": "polygon",
            "rings": [[]]  # Would need actual geometry data
        }
        
        # Perform setback analysis
        setback_service = SetbackAnalysisService()
        analysis_result = setback_service.analyze_setbacks(
            parcel_geometry=parcel_geometry,
            zoning_setbacks=zoning_setbacks,
            proposed_building=proposed_building,
            existing_buildings=existing_buildings
        )
        
        return analysis_result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Setback analysis error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Setback analysis failed"
        )


@router.post("/{parcel_id}/analyze/backyard")
async def analyze_parcel_backyard(
    parcel_id: int,
    proposed_building: Optional[dict] = None,
    zoning_requirements: Optional[dict] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Analyze backyard and outdoor space for a parcel
    """
    try:
        # Get parcel
        parcel = db.query(Parcel).filter(
            Parcel.id == parcel_id,
            Parcel.organization_id == current_user.organization_id
        ).first()
        
        if not parcel:
            raise HTTPException(
                status_code=404,
                detail="Parcel not found"
            )
        
        # Get existing buildings
        buildings = db.query(BuildingFootprint).filter(
            BuildingFootprint.parcel_id == parcel_id
        ).all()
        
        building_footprints = []
        for building in buildings:
            if building.geometry:
                building_footprints.append({
                    "id": building.id,
                    "geometry": building.geometry
                })
        
        # Create parcel geometry dict
        parcel_geometry = {
            "type": "polygon",
            "rings": [[]]  # Would need actual geometry data
        }
        
        # Perform backyard analysis
        backyard_service = BackyardAnalysisService()
        analysis_result = backyard_service.analyze_backyard(
            parcel_geometry=parcel_geometry,
            building_footprints=building_footprints,
            proposed_building=proposed_building,
            zoning_requirements=zoning_requirements
        )
        
        return analysis_result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backyard analysis error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Backyard analysis failed"
        )


@router.post("/{parcel_id}/analyze/obstacles")
async def analyze_parcel_obstacles(
    parcel_id: int,
    existing_features: List[dict],
    proposed_development: Optional[dict] = None,
    environmental_data: Optional[dict] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Analyze development obstacles and constraints for a parcel
    """
    try:
        # Get parcel
        parcel = db.query(Parcel).filter(
            Parcel.id == parcel_id,
            Parcel.organization_id == current_user.organization_id
        ).first()
        
        if not parcel:
            raise HTTPException(
                status_code=404,
                detail="Parcel not found"
            )
        
        # Create parcel geometry dict
        parcel_geometry = {
            "type": "polygon",
            "rings": [[]]  # Would need actual geometry data
        }
        
        # Perform obstacle analysis
        obstacle_service = ObstacleAnalysisService()
        analysis_result = obstacle_service.analyze_obstacles(
            parcel_geometry=parcel_geometry,
            existing_features=existing_features,
            proposed_development=proposed_development,
            environmental_data=environmental_data
        )
        
        return analysis_result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Obstacle analysis error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Obstacle analysis failed"
        )


@router.post("/{parcel_id}/analyze/fit-test")
async def test_building_fit(
    parcel_id: int,
    building_specifications: dict,
    setback_requirements: dict,
    optimization_goals: Optional[List[str]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Test building fit and find optimal placement on parcel
    """
    try:
        # Get parcel
        parcel = db.query(Parcel).filter(
            Parcel.id == parcel_id,
            Parcel.organization_id == current_user.organization_id
        ).first()
        
        if not parcel:
            raise HTTPException(
                status_code=404,
                detail="Parcel not found"
            )
        
        # Get existing buildings
        buildings = db.query(BuildingFootprint).filter(
            BuildingFootprint.parcel_id == parcel_id
        ).all()
        
        existing_buildings = []
        for building in buildings:
            if building.geometry:
                existing_buildings.append({
                    "id": building.id,
                    "geometry": building.geometry
                })
        
        # Create parcel geometry dict
        parcel_geometry = {
            "type": "polygon",
            "rings": [[]]  # Would need actual geometry data
        }
        
        # Perform fit test
        fit_service = FitTestService()
        fit_result = fit_service.test_building_fit(
            parcel_geometry=parcel_geometry,
            building_specifications=building_specifications,
            setback_requirements=setback_requirements,
            existing_buildings=existing_buildings,
            optimization_goals=optimization_goals
        )
        
        return fit_result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fit test error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Building fit test failed"
        )


@router.get("/{parcel_id}/zoning")
async def get_parcel_zoning(
    parcel_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get zoning information for a parcel
    """
    try:
        # Get parcel
        parcel = db.query(Parcel).filter(
            Parcel.id == parcel_id,
            Parcel.organization_id == current_user.organization_id
        ).first()
        
        if not parcel:
            raise HTTPException(
                status_code=404,
                detail="Parcel not found"
            )
        
        zoning_info = {
            "parcel_id": parcel_id,
            "zoning_code": parcel.zoning_code,
            "zoning_description": parcel.zoning_description,
            "land_use_code": parcel.land_use_code,
            "land_use_description": parcel.land_use_description
        }
        
        # Get detailed zoning district information if available
        if parcel.zoning_code:
            zoning_district = db.query(ZoningDistrict).filter(
                ZoningDistrict.code == parcel.zoning_code
            ).first()
            
            if zoning_district:
                zoning_info["zoning_district"] = {
                    "id": zoning_district.id,
                    "name": zoning_district.name,
                    "description": zoning_district.description,
                    "category": zoning_district.category,
                    "jurisdiction": zoning_district.jurisdiction,
                    "setback_requirements": zoning_district.get_setback_requirements(),
                    "max_height_ft": zoning_district.max_building_height_ft,
                    "max_stories": zoning_district.max_stories,
                    "max_lot_coverage": zoning_district.max_lot_coverage,
                    "max_far": zoning_district.max_floor_area_ratio,
                    "max_density": zoning_district.max_density_units_acre,
                    "permitted_uses": zoning_district.permitted_uses,
                    "conditional_uses": zoning_district.conditional_uses,
                    "prohibited_uses": zoning_district.prohibited_uses
                }
        
        return zoning_info
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get parcel zoning error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve parcel zoning information"
        )


@router.post("/import", response_model=ParcelImportResponse)
async def import_parcels(
    import_data: ParcelImport,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Import parcels from file (placeholder implementation)
    """
    try:
        # Verify user has access to organization
        if (current_user.organization_id != import_data.organization_id and 
            current_user.role != "admin"):
            raise HTTPException(
                status_code=403,
                detail="Access denied to this organization"
            )
        
        # This would implement actual file processing logic
        # For now, return a placeholder response
        
        import uuid
        from datetime import datetime
        
        import_id = str(uuid.uuid4())
        
        return ParcelImportResponse(
            import_id=import_id,
            status="queued",
            total_records=0,
            processed_records=0,
            successful_imports=0,
            failed_imports=0,
            errors=[],
            created_at=datetime.utcnow()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Parcel import error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Parcel import failed"
        )