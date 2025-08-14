"""
Property assessment schemas for request/response models
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AssessmentType(str, Enum):
    """Assessment type enumeration"""
    ZONING = "zoning"
    DEVELOPMENT = "development"
    FEASIBILITY = "feasibility"
    SETBACK = "setback"
    COMPREHENSIVE = "comprehensive"


class AssessmentStatus(str, Enum):
    """Assessment status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevel(str, Enum):
    """Risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AssessmentBase(BaseModel):
    """Base assessment model"""
    assessment_name: Optional[str] = Field(None, max_length=200)
    assessment_type: AssessmentType
    purpose: Optional[str] = None
    
    # Development scenario
    proposed_use: Optional[str] = Field(None, max_length=200)
    proposed_units: Optional[int] = Field(None, ge=1)
    proposed_sqft: Optional[float] = Field(None, gt=0)
    proposed_stories: Optional[int] = Field(None, ge=1, le=50)
    proposed_height_ft: Optional[float] = Field(None, gt=0, le=1000)


class AssessmentCreate(AssessmentBase):
    """Assessment creation model"""
    parcel_id: int
    requested_by: Optional[str] = Field(None, max_length=200)
    client_reference: Optional[str] = Field(None, max_length=100)


class AssessmentUpdate(BaseModel):
    """Assessment update model"""
    assessment_name: Optional[str] = Field(None, max_length=200)
    purpose: Optional[str] = None
    status: Optional[AssessmentStatus] = None
    
    # Update scenario
    proposed_use: Optional[str] = Field(None, max_length=200)
    proposed_units: Optional[int] = Field(None, ge=1)
    proposed_sqft: Optional[float] = Field(None, gt=0)
    proposed_stories: Optional[int] = Field(None, ge=1, le=50)
    proposed_height_ft: Optional[float] = Field(None, gt=0, le=1000)


class SetbackRequirements(BaseModel):
    """Setback requirements model"""
    front: Optional[float] = Field(None, description="Front setback in feet")
    rear: Optional[float] = Field(None, description="Rear setback in feet")
    side: Optional[float] = Field(None, description="Side setback in feet")
    corner_side: Optional[float] = Field(None, description="Corner side setback in feet")


class ComplianceResult(BaseModel):
    """Compliance result model"""
    compliant: bool
    required_value: Optional[float] = None
    proposed_value: Optional[float] = None
    variance_needed: Optional[float] = None
    notes: Optional[str] = None


class ZoningAnalysis(BaseModel):
    """Zoning analysis results"""
    zoning_code: Optional[str]
    zoning_description: Optional[str]
    
    # Compliance checks
    use_permitted: Optional[str] = Field(None, description="permitted, conditional, prohibited, or unknown")
    setback_compliance: Optional[ComplianceResult] = None
    height_compliance: Optional[ComplianceResult] = None
    density_compliance: Optional[ComplianceResult] = None
    coverage_compliance: Optional[ComplianceResult] = None
    far_compliance: Optional[ComplianceResult] = None
    parking_compliance: Optional[ComplianceResult] = None
    
    # Maximum allowable development
    max_units: Optional[int] = None
    max_sqft: Optional[float] = None
    max_stories: Optional[int] = None
    max_height_ft: Optional[float] = None
    buildable_area_sqft: Optional[float] = None


class FinancialAnalysis(BaseModel):
    """Financial analysis results"""
    estimated_development_cost: Optional[float] = None
    estimated_permit_fees: Optional[float] = None
    estimated_impact_fees: Optional[float] = None
    estimated_total_cost: Optional[float] = None
    estimated_market_value: Optional[float] = None
    estimated_rent: Optional[float] = None
    roi_estimate: Optional[float] = None


class MarketAnalysis(BaseModel):
    """Market analysis results"""
    comparable_sales: Optional[List[Dict[str, Any]]] = None
    average_sale_price_sqft: Optional[float] = None
    median_sale_price: Optional[float] = None
    average_rent_sqft: Optional[float] = None
    median_rent: Optional[float] = None
    market_trends: Optional[str] = None
    absorption_rate: Optional[float] = None


class RiskAssessment(BaseModel):
    """Risk assessment results"""
    risk_level: Optional[RiskLevel] = None
    risk_factors: Optional[List[str]] = None
    mitigation_strategies: Optional[List[str]] = None
    probability_of_approval: Optional[float] = Field(None, ge=0, le=1)


class AssessmentResponse(AssessmentBase):
    """Assessment response model"""
    id: int
    assessment_id: str
    organization_id: int
    parcel_id: int
    
    requested_by: Optional[str]
    client_reference: Optional[str]
    status: AssessmentStatus
    progress_percentage: int
    
    # Analysis results
    development_feasible: Optional[bool] = None
    zoning_compliant: Optional[bool] = None
    
    # Detailed analysis
    zoning_analysis: Optional[ZoningAnalysis] = None
    financial_analysis: Optional[FinancialAnalysis] = None
    market_analysis: Optional[MarketAnalysis] = None
    risk_assessment: Optional[RiskAssessment] = None
    
    # Recommendations
    recommendations: Optional[List[str]] = None
    alternative_scenarios: Optional[List[Dict[str, Any]]] = None
    next_steps: Optional[List[str]] = None
    
    # Processing info
    processing_time_seconds: Optional[float] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    data_quality: Optional[str] = None
    limitations: Optional[str] = None
    
    # Report
    report_generated: bool
    report_url: Optional[str] = None
    summary: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    
    # Computed properties
    is_completed: bool
    is_compliant: Optional[bool] = None
    
    class Config:
        from_attributes = True


class AssessmentSummary(BaseModel):
    """Assessment summary model for list views"""
    id: int
    assessment_id: str
    assessment_name: Optional[str]
    assessment_type: AssessmentType
    parcel_id: int
    status: AssessmentStatus
    development_feasible: Optional[bool]
    zoning_compliant: Optional[bool]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class AssessmentSearch(BaseModel):
    """Assessment search criteria"""
    assessment_type: Optional[AssessmentType] = None
    status: Optional[AssessmentStatus] = None
    parcel_id: Optional[int] = None
    requested_by: Optional[str] = None
    
    # Date filters
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    completed_after: Optional[datetime] = None
    completed_before: Optional[datetime] = None
    
    # Results filters
    development_feasible: Optional[bool] = None
    zoning_compliant: Optional[bool] = None
    
    # Pagination
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)
    
    # Sorting
    sort_by: Optional[str] = Field("created_at")
    sort_order: Optional[str] = Field("desc", regex="^(asc|desc)$")


class AssessmentSearchResponse(BaseModel):
    """Assessment search response model"""
    total: int
    skip: int
    limit: int
    results: List[AssessmentSummary]


class AssessmentReport(BaseModel):
    """Assessment report model"""
    assessment_id: str
    report_type: str = Field(..., regex="^(pdf|html|json)$")
    include_maps: bool = Field(True, description="Include maps in report")
    include_photos: bool = Field(False, description="Include property photos")
    custom_sections: Optional[List[str]] = Field(None, description="Custom report sections to include")


class AssessmentReportResponse(BaseModel):
    """Assessment report response model"""
    report_id: str
    report_url: str
    report_type: str
    file_size_bytes: int
    generated_at: datetime
    expires_at: Optional[datetime] = None


class BatchAssessmentRequest(BaseModel):
    """Batch assessment request model"""
    parcel_ids: List[int] = Field(..., min_items=1, max_items=100)
    assessment_type: AssessmentType
    assessment_name: Optional[str] = None
    
    # Common scenario for all assessments
    proposed_use: Optional[str] = None
    proposed_units: Optional[int] = None
    proposed_sqft: Optional[float] = None
    proposed_stories: Optional[int] = None
    proposed_height_ft: Optional[float] = None
    
    # Processing options
    run_parallel: bool = Field(True, description="Run assessments in parallel")
    generate_reports: bool = Field(False, description="Generate PDF reports automatically")


class BatchAssessmentResponse(BaseModel):
    """Batch assessment response model"""
    batch_id: str
    total_assessments: int
    status: str
    created_assessments: List[str]  # List of assessment IDs
    failed_assessments: List[Dict[str, str]]  # List of failures with reasons
    estimated_completion_time: Optional[int] = Field(None, description="Estimated completion time in seconds")
    created_at: datetime


class ComplianceCheck(BaseModel):
    """Individual compliance check model"""
    check_name: str
    compliant: Optional[bool] = None
    required_value: Optional[float] = None
    actual_value: Optional[float] = None
    variance_amount: Optional[float] = None
    notes: Optional[str] = None


class ComplianceSummary(BaseModel):
    """Compliance summary model"""
    overall_compliant: Optional[bool] = None
    total_checks: int
    passing_checks: int
    failing_checks: int
    unknown_checks: int
    
    checks: List[ComplianceCheck]
    violations: List[str]
    warnings: List[str]
    recommendations: List[str]