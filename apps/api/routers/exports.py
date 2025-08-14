"""
Exports router for generating reports and data exports
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
import tempfile
import os
from datetime import datetime
import csv
import json

from core.database import get_db
from core.security import get_current_active_user
from models.user import User
from models.parcel import Parcel
from models.property_assessment import PropertyAssessment
from schemas.assessment import AssessmentReport, AssessmentReportResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/assessments/{assessment_id}/report", response_model=AssessmentReportResponse)
async def generate_assessment_report(
    assessment_id: int,
    report_request: AssessmentReport,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate assessment report in specified format
    """
    try:
        # Get assessment
        assessment = db.query(PropertyAssessment).filter(
            PropertyAssessment.id == assessment_id,
            PropertyAssessment.organization_id == current_user.organization_id
        ).first()
        
        if not assessment:
            raise HTTPException(
                status_code=404,
                detail="Assessment not found"
            )
        
        # Generate report ID
        import uuid
        report_id = str(uuid.uuid4())
        
        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"assessment_report_{assessment.assessment_id}_{timestamp}.{report_request.report_type}"
        
        # Create temporary file path
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)
        
        # Generate report based on type
        if report_request.report_type == "pdf":
            file_size = await _generate_pdf_report(assessment, file_path, report_request)
        elif report_request.report_type == "html":
            file_size = await _generate_html_report(assessment, file_path, report_request)
        elif report_request.report_type == "json":
            file_size = await _generate_json_report(assessment, file_path, report_request)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported report type"
            )
        
        # For this example, we'll create a placeholder file
        # In production, this would be a proper report generation process
        
        return AssessmentReportResponse(
            report_id=report_id,
            report_url=f"/api/v1/exports/download/{report_id}",
            report_type=report_request.report_type,
            file_size_bytes=file_size,
            generated_at=datetime.utcnow(),
            expires_at=datetime.utcnow().replace(hour=23, minute=59, second=59)  # End of day
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report generation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Report generation failed"
        )


@router.get("/download/{report_id}")
async def download_report(
    report_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Download generated report file
    """
    try:
        # In production, you would track reports in database
        # For now, this is a placeholder implementation
        
        # Create a simple text file as placeholder
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"report_{report_id}.txt")
        
        with open(temp_file, "w") as f:
            f.write(f"Report ID: {report_id}\n")
            f.write(f"Generated for: {current_user.username}\n")
            f.write(f"Generated at: {datetime.utcnow()}\n")
            f.write("\nThis is a placeholder report file.\n")
        
        return FileResponse(
            path=temp_file,
            filename=f"report_{report_id}.txt",
            media_type="application/octet-stream"
        )
    
    except Exception as e:
        logger.error(f"Report download error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Report download failed"
        )


@router.get("/parcels/csv")
async def export_parcels_csv(
    parcel_ids: Optional[List[int]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Export parcels to CSV format
    """
    try:
        # Build query
        query = db.query(Parcel).filter(
            Parcel.organization_id == current_user.organization_id,
            Parcel.is_active == True
        )
        
        # Filter by specific parcel IDs if provided
        if parcel_ids:
            query = query.filter(Parcel.id.in_(parcel_ids))
        
        parcels = query.all()
        
        if not parcels:
            raise HTTPException(
                status_code=404,
                detail="No parcels found for export"
            )
        
        # Create temporary CSV file
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"parcels_export_{timestamp}.csv"
        file_path = os.path.join(temp_dir, filename)
        
        # Write CSV data
        with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "parcel_id", "address", "city", "county", "state", "postal_code",
                "area_sqft", "area_acres", "zoning_code", "property_type",
                "owner_name", "assessed_value", "market_value", "tax_year",
                "building_count", "total_building_sqft", "year_built",
                "latitude", "longitude", "created_at", "updated_at"
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for parcel in parcels:
                writer.writerow({
                    "parcel_id": parcel.parcel_id,
                    "address": parcel.address,
                    "city": parcel.city,
                    "county": parcel.county,
                    "state": parcel.state,
                    "postal_code": parcel.postal_code,
                    "area_sqft": parcel.area_sqft,
                    "area_acres": parcel.area_acres,
                    "zoning_code": parcel.zoning_code,
                    "property_type": parcel.property_type,
                    "owner_name": parcel.owner_name,
                    "assessed_value": parcel.assessed_value,
                    "market_value": parcel.market_value,
                    "tax_year": parcel.tax_year,
                    "building_count": parcel.building_count,
                    "total_building_sqft": parcel.total_building_sqft,
                    "year_built": parcel.year_built,
                    "latitude": parcel.latitude,
                    "longitude": parcel.longitude,
                    "created_at": parcel.created_at.isoformat() if parcel.created_at else None,
                    "updated_at": parcel.updated_at.isoformat() if parcel.updated_at else None
                })
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="text/csv"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Parcel CSV export error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Parcel CSV export failed"
        )


@router.get("/assessments/csv")
async def export_assessments_csv(
    assessment_ids: Optional[List[int]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Export assessments to CSV format
    """
    try:
        # Build query
        query = db.query(PropertyAssessment).filter(
            PropertyAssessment.organization_id == current_user.organization_id
        )
        
        # Filter by specific assessment IDs if provided
        if assessment_ids:
            query = query.filter(PropertyAssessment.id.in_(assessment_ids))
        
        assessments = query.all()
        
        if not assessments:
            raise HTTPException(
                status_code=404,
                detail="No assessments found for export"
            )
        
        # Create temporary CSV file
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"assessments_export_{timestamp}.csv"
        file_path = os.path.join(temp_dir, filename)
        
        # Write CSV data
        with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "assessment_id", "assessment_name", "assessment_type", "parcel_id",
                "status", "development_feasible", "zoning_compliant",
                "proposed_use", "proposed_units", "proposed_sqft",
                "max_buildable_sqft", "max_units", "buildable_area_sqft",
                "confidence_score", "processing_time_seconds",
                "created_at", "completed_at"
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for assessment in assessments:
                writer.writerow({
                    "assessment_id": assessment.assessment_id,
                    "assessment_name": assessment.assessment_name,
                    "assessment_type": assessment.assessment_type,
                    "parcel_id": assessment.parcel_id,
                    "status": assessment.status,
                    "development_feasible": assessment.development_feasible,
                    "zoning_compliant": assessment.zoning_compliant,
                    "proposed_use": assessment.proposed_use,
                    "proposed_units": assessment.proposed_units,
                    "proposed_sqft": assessment.proposed_sqft,
                    "max_buildable_sqft": assessment.max_buildable_sqft,
                    "max_units": assessment.max_units,
                    "buildable_area_sqft": assessment.buildable_area_sqft,
                    "confidence_score": assessment.confidence_score,
                    "processing_time_seconds": assessment.processing_time_seconds,
                    "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
                    "completed_at": assessment.completed_at.isoformat() if assessment.completed_at else None
                })
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="text/csv"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Assessment CSV export error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Assessment CSV export failed"
        )


@router.get("/geojson/parcels")
async def export_parcels_geojson(
    parcel_ids: Optional[List[int]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Export parcels to GeoJSON format
    """
    try:
        # Build query
        query = db.query(Parcel).filter(
            Parcel.organization_id == current_user.organization_id,
            Parcel.is_active == True
        )
        
        # Filter by specific parcel IDs if provided
        if parcel_ids:
            query = query.filter(Parcel.id.in_(parcel_ids))
        
        parcels = query.all()
        
        if not parcels:
            raise HTTPException(
                status_code=404,
                detail="No parcels found for export"
            )
        
        # Build GeoJSON structure
        features = []
        for parcel in parcels:
            # Create feature geometry (placeholder - would use actual geometry)
            geometry = None
            if parcel.latitude and parcel.longitude:
                geometry = {
                    "type": "Point",
                    "coordinates": [parcel.longitude, parcel.latitude]
                }
            
            feature = {
                "type": "Feature",
                "properties": {
                    "parcel_id": parcel.parcel_id,
                    "address": parcel.address,
                    "city": parcel.city,
                    "state": parcel.state,
                    "area_sqft": parcel.area_sqft,
                    "zoning_code": parcel.zoning_code,
                    "property_type": parcel.property_type,
                    "assessed_value": parcel.assessed_value
                },
                "geometry": geometry
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # Create temporary GeoJSON file
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"parcels_export_{timestamp}.geojson"
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(geojson, f, indent=2)
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/geo+json"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GeoJSON export error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="GeoJSON export failed"
        )


# Helper functions for report generation

async def _generate_pdf_report(assessment: PropertyAssessment, file_path: str, report_request: AssessmentReport) -> int:
    """Generate PDF report (placeholder implementation)"""
    # This would use a PDF generation library like ReportLab
    # For now, create a simple text file
    
    content = f"""
Property Assessment Report
Assessment ID: {assessment.assessment_id}
Assessment Type: {assessment.assessment_type}
Status: {assessment.status}
Parcel ID: {assessment.parcel_id}

Development Feasible: {assessment.development_feasible}
Zoning Compliant: {assessment.zoning_compliant}

Proposed Development:
- Use: {assessment.proposed_use}
- Units: {assessment.proposed_units}
- Square Feet: {assessment.proposed_sqft}

Analysis Results:
- Max Buildable Sq Ft: {assessment.max_buildable_sqft}
- Max Units: {assessment.max_units}
- Buildable Area: {assessment.buildable_area_sqft}

Confidence Score: {assessment.confidence_score}
Processing Time: {assessment.processing_time_seconds} seconds

Generated: {datetime.utcnow()}
"""
    
    with open(file_path, "w") as f:
        f.write(content)
    
    return len(content.encode('utf-8'))


async def _generate_html_report(assessment: PropertyAssessment, file_path: str, report_request: AssessmentReport) -> int:
    """Generate HTML report"""
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Property Assessment Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; }}
        .section {{ margin: 20px 0; }}
        .label {{ font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Property Assessment Report</h1>
        <p><span class="label">Assessment ID:</span> {assessment.assessment_id}</p>
        <p><span class="label">Generated:</span> {datetime.utcnow()}</p>
    </div>
    
    <div class="section">
        <h2>Assessment Details</h2>
        <p><span class="label">Type:</span> {assessment.assessment_type}</p>
        <p><span class="label">Status:</span> {assessment.status}</p>
        <p><span class="label">Parcel ID:</span> {assessment.parcel_id}</p>
    </div>
    
    <div class="section">
        <h2>Analysis Results</h2>
        <p><span class="label">Development Feasible:</span> {assessment.development_feasible}</p>
        <p><span class="label">Zoning Compliant:</span> {assessment.zoning_compliant}</p>
        <p><span class="label">Max Buildable Sq Ft:</span> {assessment.max_buildable_sqft}</p>
        <p><span class="label">Confidence Score:</span> {assessment.confidence_score}</p>
    </div>
</body>
</html>
"""
    
    with open(file_path, "w") as f:
        f.write(html_content)
    
    return len(html_content.encode('utf-8'))


async def _generate_json_report(assessment: PropertyAssessment, file_path: str, report_request: AssessmentReport) -> int:
    """Generate JSON report"""
    report_data = {
        "assessment_id": assessment.assessment_id,
        "assessment_type": assessment.assessment_type,
        "status": assessment.status,
        "parcel_id": assessment.parcel_id,
        "development_feasible": assessment.development_feasible,
        "zoning_compliant": assessment.zoning_compliant,
        "proposed_development": {
            "use": assessment.proposed_use,
            "units": assessment.proposed_units,
            "sqft": assessment.proposed_sqft
        },
        "analysis_results": {
            "max_buildable_sqft": assessment.max_buildable_sqft,
            "max_units": assessment.max_units,
            "buildable_area_sqft": assessment.buildable_area_sqft
        },
        "confidence_score": assessment.confidence_score,
        "processing_time_seconds": assessment.processing_time_seconds,
        "generated_at": datetime.utcnow().isoformat()
    }
    
    with open(file_path, "w") as f:
        json.dump(report_data, f, indent=2)
    
    json_str = json.dumps(report_data, indent=2)
    return len(json_str.encode('utf-8'))