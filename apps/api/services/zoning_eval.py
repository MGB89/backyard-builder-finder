"""
Zoning evaluation service for compliance analysis
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from functools import lru_cache
import json
import hashlib
from datetime import datetime
from shapely.geometry import Polygon
from shapely.ops import transform
from shapely.validation import make_valid
from pyproj import Transformer

logger = logging.getLogger(__name__)


class ZoningEvaluationService:
    """Service for evaluating zoning compliance and requirements"""
    
    def __init__(self):
        self.standard_zoning_categories = {
            "residential": ["R-1", "R-2", "R-3", "R-4", "RM", "RH"],
            "commercial": ["C-1", "C-2", "C-3", "CC", "CN", "CR"],
            "industrial": ["I-1", "I-2", "I-3", "IG", "IL", "IH"],
            "mixed_use": ["MU", "MX", "TOD", "PUD"],
            "agricultural": ["A", "AG", "A-1", "A-2"],
            "open_space": ["OS", "P", "R", "ROS"]
        }
        
        self.compliance_checks = [
            "use_permitted", "density", "height", "setbacks", 
            "lot_coverage", "far", "parking", "landscaping"
        ]
        
        # Cache for coordinate transformations
        self._transformer_cache = {}
        # WGS84 (lat/lon) to Web Mercator for area calculations
        self.to_mercator = self._get_transformer("EPSG:4326", "EPSG:3857")
        self.from_mercator = self._get_transformer("EPSG:3857", "EPSG:4326")
        
        # Cache for zoning compliance results
        self._compliance_cache = {}
    
    def evaluate_zoning_compliance(
        self,
        parcel_data: Dict[str, Any],
        zoning_district: Dict[str, Any],
        proposed_development: Dict[str, Any],
        existing_conditions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate zoning compliance for proposed development
        
        Args:
            parcel_data: Parcel information and geometry
            zoning_district: Zoning district regulations
            proposed_development: Proposed development specifications
            existing_conditions: Current site conditions (optional)
            
        Returns:
            Dict[str, Any]: Comprehensive zoning compliance evaluation
        """
        try:
            # Extract key information and handle geometry
            parcel_area = parcel_data.get("area_sqft", 0)
            if parcel_area == 0 and "geometry" in parcel_data:
                # Calculate area from geometry if not provided
                parcel_polygon = self._create_polygon_from_geometry(parcel_data["geometry"])
                if parcel_polygon:
                    parcel_area = self._convert_area_to_sqft(parcel_polygon.area)
            
            zoning_code = zoning_district.get("code", "Unknown")
            
            # Create cache key for this evaluation
            cache_key = self._create_cache_key(parcel_data, zoning_district, proposed_development)
            
            # Perform individual compliance checks
            compliance_results = {}
            
            # Use permitted check
            use_compliance = self._check_use_permitted(
                proposed_development.get("use_type"),
                zoning_district
            )
            compliance_results["use_permitted"] = use_compliance
            
            # Density check
            density_compliance = self._check_density_compliance(
                proposed_development,
                zoning_district,
                parcel_area
            )
            compliance_results["density"] = density_compliance
            
            # Height restrictions
            height_compliance = self._check_height_compliance(
                proposed_development,
                zoning_district
            )
            compliance_results["height"] = height_compliance
            
            # Setback requirements
            setback_compliance = self._check_setback_compliance(
                proposed_development,
                zoning_district,
                parcel_data
            )
            compliance_results["setbacks"] = setback_compliance
            
            # Lot coverage
            coverage_compliance = self._check_lot_coverage(
                proposed_development,
                zoning_district,
                parcel_area
            )
            compliance_results["lot_coverage"] = coverage_compliance
            
            # Floor Area Ratio (FAR)
            far_compliance = self._check_far_compliance(
                proposed_development,
                zoning_district,
                parcel_area
            )
            compliance_results["far"] = far_compliance
            
            # Parking requirements
            parking_compliance = self._check_parking_requirements(
                proposed_development,
                zoning_district
            )
            compliance_results["parking"] = parking_compliance
            
            # Landscaping requirements
            landscaping_compliance = self._check_landscaping_requirements(
                proposed_development,
                zoning_district,
                parcel_area
            )
            compliance_results["landscaping"] = landscaping_compliance
            
            # Calculate overall compliance
            overall_assessment = self._calculate_overall_compliance(compliance_results)
            
            # Generate recommendations
            recommendations = self._generate_compliance_recommendations(
                compliance_results,
                overall_assessment
            )
            
            # Check for special requirements
            special_requirements = self._check_special_requirements(
                zoning_district,
                proposed_development,
                parcel_data
            )
            
            result = {
                "success": True,
                "zoning_code": zoning_code,
                "zoning_category": self._categorize_zoning(zoning_code),
                "overall_compliant": overall_assessment["overall_compliant"],
                "compliance_score": overall_assessment["compliance_score"],
                "compliance_details": compliance_results,
                "special_requirements": special_requirements,
                "recommendations": recommendations,
                "violations": overall_assessment["violations"],
                "warnings": overall_assessment["warnings"],
                "parcel_area_sqft": parcel_area,
                "evaluation_date": datetime.utcnow().isoformat()
            }
            
            # Cache the result
            self._compliance_cache[cache_key] = result
            return result
        
        except Exception as e:
            logger.error(f"Zoning evaluation error: {str(e)}")
            return {
                "success": False,
                "error": f"Zoning evaluation failed: {str(e)}"
            }
    
    def _check_use_permitted(
        self,
        proposed_use: str,
        zoning_district: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if proposed use is permitted in zoning district"""
        try:
            permitted_uses = zoning_district.get("permitted_uses", [])
            conditional_uses = zoning_district.get("conditional_uses", [])
            prohibited_uses = zoning_district.get("prohibited_uses", [])
            
            # Normalize use type for comparison
            use_lower = proposed_use.lower() if proposed_use else ""
            
            # Check if use is explicitly prohibited
            for prohibited in prohibited_uses:
                if use_lower in prohibited.lower():
                    return {
                        "compliant": False,
                        "status": "prohibited",
                        "message": f"Use '{proposed_use}' is prohibited in this zoning district"
                    }
            
            # Check if use is permitted by right
            for permitted in permitted_uses:
                if use_lower in permitted.lower():
                    return {
                        "compliant": True,
                        "status": "permitted",
                        "message": f"Use '{proposed_use}' is permitted by right"
                    }
            
            # Check if use requires conditional use permit
            for conditional in conditional_uses:
                if use_lower in conditional.lower():
                    return {
                        "compliant": True,
                        "status": "conditional",
                        "message": f"Use '{proposed_use}' requires conditional use permit",
                        "permit_required": "Conditional Use Permit"
                    }
            
            # Use not found in any category
            return {
                "compliant": False,
                "status": "not_listed",
                "message": f"Use '{proposed_use}' is not specifically listed in zoning regulations",
                "recommendation": "Consult with planning department for use determination"
            }
        
        except Exception as e:
            logger.error(f"Error checking use permission: {str(e)}")
            return {
                "compliant": False,
                "error": str(e)
            }
    
    def _check_density_compliance(
        self,
        proposed_development: Dict[str, Any],
        zoning_district: Dict[str, Any],
        parcel_area: float
    ) -> Dict[str, Any]:
        """Check density compliance"""
        try:
            proposed_units = proposed_development.get("units", 0)
            max_density = zoning_district.get("max_density_units_acre")
            min_lot_size = zoning_district.get("min_lot_size_sqft")
            
            parcel_acres = parcel_area / 43560 if parcel_area > 0 else 0
            
            compliance_result = {
                "compliant": True,
                "proposed_units": proposed_units,
                "parcel_area_sqft": parcel_area,
                "parcel_acres": parcel_acres
            }
            
            # Check maximum density
            if max_density and parcel_acres > 0:
                max_allowed_units = max_density * parcel_acres
                proposed_density = proposed_units / parcel_acres if parcel_acres > 0 else 0
                
                compliance_result.update({
                    "max_density_units_acre": max_density,
                    "proposed_density_units_acre": proposed_density,
                    "max_allowed_units": max_allowed_units,
                    "density_compliant": proposed_units <= max_allowed_units
                })
                
                if proposed_units > max_allowed_units:
                    compliance_result["compliant"] = False
                    compliance_result["violation"] = f"Proposed {proposed_units} units exceeds maximum of {max_allowed_units:.1f} units"
            
            # Check minimum lot size per unit
            if min_lot_size and proposed_units > 0:
                required_area = min_lot_size * proposed_units
                lot_size_compliant = parcel_area >= required_area
                
                compliance_result.update({
                    "min_lot_size_sqft": min_lot_size,
                    "required_area_sqft": required_area,
                    "lot_size_compliant": lot_size_compliant
                })
                
                if not lot_size_compliant:
                    compliance_result["compliant"] = False
                    compliance_result["violation"] = f"Parcel too small: {parcel_area:,.0f} sq ft available, {required_area:,.0f} sq ft required"
            
            return compliance_result
        
        except Exception as e:
            logger.error(f"Error checking density compliance: {str(e)}")
            return {
                "compliant": False,
                "error": str(e)
            }
    
    def _check_height_compliance(
        self,
        proposed_development: Dict[str, Any],
        zoning_district: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check height restrictions compliance"""
        try:
            proposed_height = proposed_development.get("height_ft")
            proposed_stories = proposed_development.get("stories")
            
            max_height = zoning_district.get("max_building_height_ft")
            max_stories = zoning_district.get("max_stories")
            
            compliance_result = {
                "compliant": True,
                "proposed_height_ft": proposed_height,
                "proposed_stories": proposed_stories
            }
            
            # Check maximum height
            if max_height and proposed_height:
                height_compliant = proposed_height <= max_height
                compliance_result.update({
                    "max_height_ft": max_height,
                    "height_compliant": height_compliant,
                    "height_variance_ft": proposed_height - max_height if not height_compliant else 0
                })
                
                if not height_compliant:
                    compliance_result["compliant"] = False
                    compliance_result["violation"] = f"Proposed height {proposed_height} ft exceeds maximum of {max_height} ft"
            
            # Check maximum stories
            if max_stories and proposed_stories:
                stories_compliant = proposed_stories <= max_stories
                compliance_result.update({
                    "max_stories": max_stories,
                    "stories_compliant": stories_compliant
                })
                
                if not stories_compliant:
                    compliance_result["compliant"] = False
                    compliance_result["violation"] = f"Proposed {proposed_stories} stories exceeds maximum of {max_stories} stories"
            
            return compliance_result
        
        except Exception as e:
            logger.error(f"Error checking height compliance: {str(e)}")
            return {
                "compliant": False,
                "error": str(e)
            }
    
    def _check_setback_compliance(
        self,
        proposed_development: Dict[str, Any],
        zoning_district: Dict[str, Any],
        parcel_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check setback requirements compliance"""
        try:
            # Get required setbacks
            required_setbacks = {
                "front": zoning_district.get("min_building_setback_front_ft"),
                "rear": zoning_district.get("min_building_setback_rear_ft"),
                "side": zoning_district.get("min_building_setback_side_ft"),
                "corner_side": zoning_district.get("min_building_setback_corner_side_ft")
            }
            
            # Get proposed setbacks (if available)
            proposed_setbacks = proposed_development.get("setbacks", {})
            
            compliance_result = {
                "compliant": True,
                "required_setbacks": required_setbacks,
                "proposed_setbacks": proposed_setbacks,
                "setback_compliance": {}
            }
            
            violations = []
            
            for direction, required in required_setbacks.items():
                if required is not None:
                    proposed = proposed_setbacks.get(direction)
                    
                    if proposed is not None:
                        compliant = proposed >= required
                        compliance_result["setback_compliance"][direction] = {
                            "required_ft": required,
                            "proposed_ft": proposed,
                            "compliant": compliant,
                            "variance_ft": required - proposed if not compliant else 0
                        }
                        
                        if not compliant:
                            violations.append(f"{direction.title()} setback: {proposed} ft provided, {required} ft required")
                            compliance_result["compliant"] = False
                    else:
                        compliance_result["setback_compliance"][direction] = {
                            "required_ft": required,
                            "proposed_ft": None,
                            "compliant": None,
                            "note": "Proposed setback not specified"
                        }
            
            if violations:
                compliance_result["violations"] = violations
            
            return compliance_result
        
        except Exception as e:
            logger.error(f"Error checking setback compliance: {str(e)}")
            return {
                "compliant": False,
                "error": str(e)
            }
    
    def _check_lot_coverage(
        self,
        proposed_development: Dict[str, Any],
        zoning_district: Dict[str, Any],
        parcel_area: float
    ) -> Dict[str, Any]:
        """Check lot coverage compliance"""
        try:
            proposed_coverage_sqft = proposed_development.get("building_area_sqft", 0)
            max_coverage_percent = zoning_district.get("max_lot_coverage")
            
            compliance_result = {
                "compliant": True,
                "proposed_coverage_sqft": proposed_coverage_sqft,
                "parcel_area_sqft": parcel_area
            }
            
            if parcel_area > 0:
                proposed_coverage_percent = (proposed_coverage_sqft / parcel_area) * 100
                compliance_result["proposed_coverage_percent"] = proposed_coverage_percent
                
                if max_coverage_percent:
                    max_coverage_sqft = (max_coverage_percent / 100) * parcel_area
                    coverage_compliant = proposed_coverage_sqft <= max_coverage_sqft
                    
                    compliance_result.update({
                        "max_coverage_percent": max_coverage_percent,
                        "max_coverage_sqft": max_coverage_sqft,
                        "coverage_compliant": coverage_compliant,
                        "excess_coverage_sqft": max(0, proposed_coverage_sqft - max_coverage_sqft)
                    })
                    
                    if not coverage_compliant:
                        compliance_result["compliant"] = False
                        compliance_result["violation"] = f"Lot coverage {proposed_coverage_percent:.1f}% exceeds maximum of {max_coverage_percent}%"
            
            return compliance_result
        
        except Exception as e:
            logger.error(f"Error checking lot coverage: {str(e)}")
            return {
                "compliant": False,
                "error": str(e)
            }
    
    def _check_far_compliance(
        self,
        proposed_development: Dict[str, Any],
        zoning_district: Dict[str, Any],
        parcel_area: float
    ) -> Dict[str, Any]:
        """Check Floor Area Ratio (FAR) compliance"""
        try:
            proposed_floor_area = proposed_development.get("total_floor_area_sqft")
            max_far = zoning_district.get("max_floor_area_ratio")
            
            compliance_result = {
                "compliant": True,
                "proposed_floor_area_sqft": proposed_floor_area,
                "parcel_area_sqft": parcel_area
            }
            
            if proposed_floor_area and parcel_area > 0:
                proposed_far = proposed_floor_area / parcel_area
                compliance_result["proposed_far"] = proposed_far
                
                if max_far:
                    max_floor_area = max_far * parcel_area
                    far_compliant = proposed_floor_area <= max_floor_area
                    
                    compliance_result.update({
                        "max_far": max_far,
                        "max_floor_area_sqft": max_floor_area,
                        "far_compliant": far_compliant,
                        "excess_floor_area_sqft": max(0, proposed_floor_area - max_floor_area)
                    })
                    
                    if not far_compliant:
                        compliance_result["compliant"] = False
                        compliance_result["violation"] = f"FAR {proposed_far:.2f} exceeds maximum of {max_far:.2f}"
            
            return compliance_result
        
        except Exception as e:
            logger.error(f"Error checking FAR compliance: {str(e)}")
            return {
                "compliant": False,
                "error": str(e)
            }
    
    def _check_parking_requirements(
        self,
        proposed_development: Dict[str, Any],
        zoning_district: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check parking requirements compliance"""
        try:
            proposed_units = proposed_development.get("units", 0)
            proposed_parking = proposed_development.get("parking_spaces", 0)
            
            # Get parking requirements
            parking_per_unit = zoning_district.get("min_parking_spaces_per_unit")
            parking_requirements = zoning_district.get("parking_requirements")
            
            compliance_result = {
                "compliant": True,
                "proposed_units": proposed_units,
                "proposed_parking_spaces": proposed_parking
            }
            
            if parking_per_unit and proposed_units > 0:
                required_parking = parking_per_unit * proposed_units
                parking_compliant = proposed_parking >= required_parking
                
                compliance_result.update({
                    "parking_per_unit": parking_per_unit,
                    "required_parking_spaces": required_parking,
                    "parking_compliant": parking_compliant,
                    "parking_deficit": max(0, required_parking - proposed_parking)
                })
                
                if not parking_compliant:
                    compliance_result["compliant"] = False
                    compliance_result["violation"] = f"Parking deficit: {proposed_parking} spaces provided, {required_parking} required"
            
            if parking_requirements:
                compliance_result["parking_requirements"] = parking_requirements
            
            return compliance_result
        
        except Exception as e:
            logger.error(f"Error checking parking requirements: {str(e)}")
            return {
                "compliant": False,
                "error": str(e)
            }
    
    def _check_landscaping_requirements(
        self,
        proposed_development: Dict[str, Any],
        zoning_district: Dict[str, Any],
        parcel_area: float
    ) -> Dict[str, Any]:
        """Check landscaping requirements compliance"""
        try:
            proposed_landscaping = proposed_development.get("landscaped_area_sqft", 0)
            landscaping_requirements = zoning_district.get("landscape_requirements")
            
            compliance_result = {
                "compliant": True,
                "proposed_landscaping_sqft": proposed_landscaping,
                "parcel_area_sqft": parcel_area
            }
            
            # Check if landscaping requirements exist
            if landscaping_requirements and parcel_area > 0:
                # This would be expanded based on specific requirements
                # For now, assume a minimum percentage requirement
                min_landscape_percent = 20  # Default 20% if not specified
                
                required_landscaping = (min_landscape_percent / 100) * parcel_area
                landscaping_compliant = proposed_landscaping >= required_landscaping
                
                compliance_result.update({
                    "min_landscape_percent": min_landscape_percent,
                    "required_landscaping_sqft": required_landscaping,
                    "landscaping_compliant": landscaping_compliant,
                    "landscaping_deficit_sqft": max(0, required_landscaping - proposed_landscaping)
                })
                
                if not landscaping_compliant:
                    compliance_result["compliant"] = False
                    compliance_result["violation"] = f"Insufficient landscaping: {proposed_landscaping:,.0f} sq ft provided, {required_landscaping:,.0f} sq ft required"
            
            return compliance_result
        
        except Exception as e:
            logger.error(f"Error checking landscaping requirements: {str(e)}")
            return {
                "compliant": False,
                "error": str(e)
            }
    
    def _calculate_overall_compliance(self, compliance_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall compliance assessment"""
        try:
            total_checks = len(compliance_results)
            compliant_checks = sum(1 for result in compliance_results.values() if result.get("compliant", False))
            
            compliance_score = compliant_checks / total_checks if total_checks > 0 else 0
            overall_compliant = compliance_score == 1.0
            
            # Collect violations and warnings
            violations = []
            warnings = []
            
            for check_name, result in compliance_results.items():
                if not result.get("compliant", True):
                    violation = result.get("violation") or result.get("violations") or f"{check_name} non-compliance"
                    if isinstance(violation, list):
                        violations.extend(violation)
                    else:
                        violations.append(violation)
                
                # Check for warnings (conditional permits, etc.)
                if result.get("status") == "conditional":
                    warnings.append(f"{check_name}: {result.get('message', 'Conditional approval required')}")
            
            return {
                "overall_compliant": overall_compliant,
                "compliance_score": compliance_score,
                "total_checks": total_checks,
                "compliant_checks": compliant_checks,
                "violations": violations,
                "warnings": warnings
            }
        
        except Exception as e:
            logger.error(f"Error calculating overall compliance: {str(e)}")
            return {
                "overall_compliant": False,
                "compliance_score": 0,
                "error": str(e)
            }
    
    def _check_special_requirements(
        self,
        zoning_district: Dict[str, Any],
        proposed_development: Dict[str, Any],
        parcel_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check for special zoning requirements"""
        special_requirements = []
        
        # Historic district requirements
        if zoning_district.get("historic_district"):
            special_requirements.append({
                "type": "historic_district",
                "requirement": "Historic preservation review required",
                "impact": "Additional approval process and design restrictions"
            })
        
        # Flood overlay requirements
        if zoning_district.get("flood_overlay"):
            special_requirements.append({
                "type": "flood_overlay",
                "requirement": "Flood zone compliance required",
                "impact": "Elevation requirements and flood-resistant construction"
            })
        
        # Environmental overlay
        overlay_districts = zoning_district.get("overlay_districts", [])
        for overlay in overlay_districts:
            if "environmental" in overlay.lower():
                special_requirements.append({
                    "type": "environmental_overlay",
                    "requirement": f"Environmental compliance for {overlay}",
                    "impact": "Environmental impact assessment may be required"
                })
        
        # Conditional use permit requirements
        permits_required = []
        for check_name, result in proposed_development.items():
            if isinstance(result, dict) and result.get("permit_required"):
                permits_required.append(result["permit_required"])
        
        if permits_required:
            special_requirements.append({
                "type": "conditional_permits",
                "requirement": f"Permits required: {', '.join(permits_required)}",
                "impact": "Additional approval process and public hearing required"
            })
        
        return special_requirements
    
    def _generate_compliance_recommendations(
        self,
        compliance_results: Dict[str, Dict[str, Any]],
        overall_assessment: Dict[str, Any]
    ) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []
        
        if overall_assessment["overall_compliant"]:
            recommendations.append("Proposed development meets all zoning requirements")
            recommendations.append("Proceed with detailed design and permit application")
        else:
            recommendations.append("Address zoning violations before proceeding")
            
            # Specific recommendations for each violation
            for check_name, result in compliance_results.items():
                if not result.get("compliant", True):
                    if check_name == "use_permitted" and result.get("status") == "conditional":
                        recommendations.append("Apply for conditional use permit")
                    elif check_name == "density":
                        recommendations.append("Reduce number of units or increase lot size")
                    elif check_name == "height":
                        recommendations.append("Reduce building height or apply for height variance")
                    elif check_name == "setbacks":
                        recommendations.append("Modify building placement to meet setback requirements")
                    elif check_name == "lot_coverage":
                        recommendations.append("Reduce building footprint to meet coverage limits")
                    elif check_name == "far":
                        recommendations.append("Reduce total floor area or consider design modifications")
                    elif check_name == "parking":
                        recommendations.append("Increase parking spaces or apply for parking reduction")
                    elif check_name == "landscaping":
                        recommendations.append("Increase landscaped area to meet requirements")
        
        # General recommendations
        if overall_assessment["compliance_score"] < 1.0:
            recommendations.append("Consider consulting with a land use attorney")
            recommendations.append("Schedule pre-application meeting with planning department")
        
        recommendations.append("Verify current zoning regulations before final design")
        
        return recommendations
    
    def _categorize_zoning(self, zoning_code: str) -> str:
        """Categorize zoning code into general category"""
        code_upper = zoning_code.upper()
        
        for category, codes in self.standard_zoning_categories.items():
            for code in codes:
                if code in code_upper:
                    return category
        
        return "other"
    
    def _get_transformer(self, from_crs: str, to_crs: str) -> Transformer:
        """Get cached transformer for coordinate conversions"""
        key = f"{from_crs}_{to_crs}"
        if key not in self._transformer_cache:
            self._transformer_cache[key] = Transformer.from_crs(from_crs, to_crs, always_xy=True)
        return self._transformer_cache[key]
    
    def _create_polygon_from_geometry(self, geometry: Dict[str, Any]) -> Optional[Polygon]:
        """Create Shapely polygon from geometry dictionary with proper SRID handling"""
        try:
            polygon = None
            
            if geometry.get("type") == "Polygon":
                coordinates = geometry.get("coordinates", [])
                if coordinates and len(coordinates) > 0:
                    # Use exterior ring, handle holes if present
                    exterior_ring = coordinates[0]
                    holes = coordinates[1:] if len(coordinates) > 1 else None
                    polygon = Polygon(exterior_ring, holes)
            
            elif geometry.get("type") == "polygon" and geometry.get("rings"):
                # ArcGIS format
                rings = geometry.get("rings", [])
                if rings:
                    polygon = Polygon(rings[0])
            
            elif "coordinates" in geometry:
                # Try to handle various coordinate formats
                coords = geometry["coordinates"]
                if isinstance(coords, list) and len(coords) > 2:
                    polygon = Polygon(coords)
            
            if polygon and not polygon.is_valid:
                polygon = make_valid(polygon)
                logger.warning("Fixed invalid polygon geometry")
            
            # Assume input is in WGS84 (EPSG:4326) and transform to Web Mercator for calculations
            if polygon and polygon.is_valid:
                polygon = transform(self.to_mercator.transform, polygon)
            
            return polygon
        
        except Exception as e:
            logger.error(f"Error creating polygon: {str(e)}")
            return None
    
    def _convert_area_to_sqft(self, area_sq_meters: float) -> float:
        """Convert square meters to square feet"""
        return area_sq_meters * 10.7639
    
    def _create_cache_key(self, parcel_data: Dict[str, Any], zoning_district: Dict[str, Any], proposed_development: Dict[str, Any]) -> str:
        """Create cache key for compliance evaluation"""
        # Create a hash from the key parameters
        key_data = {
            "parcel_area": parcel_data.get("area_sqft", 0),
            "zoning_code": zoning_district.get("code"),
            "zoning_rules": {
                "max_density": zoning_district.get("max_density_units_acre"),
                "max_height": zoning_district.get("max_building_height_ft"),
                "max_coverage": zoning_district.get("max_lot_coverage"),
                "max_far": zoning_district.get("max_floor_area_ratio")
            },
            "proposed": {
                "units": proposed_development.get("units"),
                "height": proposed_development.get("height_ft"),
                "area": proposed_development.get("building_area_sqft"),
                "use_type": proposed_development.get("use_type")
            }
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    @lru_cache(maxsize=256)
    def get_cached_compliance_check(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached compliance check result"""
        return self._compliance_cache.get(cache_key)
    
    def clear_compliance_cache(self):
        """Clear the compliance cache"""
        self._compliance_cache.clear()
        self.get_cached_compliance_check.cache_clear()
    
    def get_zoning_summary(self, zoning_district: Dict[str, Any]) -> Dict[str, Any]:
        """Get a summary of zoning district regulations"""
        try:
            zoning_code = zoning_district.get("code", "Unknown")
            category = self._categorize_zoning(zoning_code)
            
            # Extract key regulations
            key_regulations = {
                "use_restrictions": {
                    "permitted_uses": zoning_district.get("permitted_uses", []),
                    "conditional_uses": zoning_district.get("conditional_uses", []),
                    "prohibited_uses": zoning_district.get("prohibited_uses", [])
                },
                "dimensional_standards": {
                    "max_height_ft": zoning_district.get("max_building_height_ft"),
                    "max_stories": zoning_district.get("max_stories"),
                    "max_lot_coverage_percent": zoning_district.get("max_lot_coverage"),
                    "max_far": zoning_district.get("max_floor_area_ratio"),
                    "max_density_units_acre": zoning_district.get("max_density_units_acre")
                },
                "setback_requirements": {
                    "front_ft": zoning_district.get("min_building_setback_front_ft"),
                    "rear_ft": zoning_district.get("min_building_setback_rear_ft"),
                    "side_ft": zoning_district.get("min_building_setback_side_ft"),
                    "corner_side_ft": zoning_district.get("min_building_setback_corner_side_ft")
                },
                "parking_requirements": {
                    "spaces_per_unit": zoning_district.get("min_parking_spaces_per_unit"),
                    "general_requirements": zoning_district.get("parking_requirements")
                }
            }
            
            # Calculate development potential metrics
            potential_metrics = self._calculate_development_potential(key_regulations)
            
            return {
                "success": True,
                "zoning_code": zoning_code,
                "category": category,
                "key_regulations": key_regulations,
                "development_potential": potential_metrics,
                "restrictiveness_score": self._calculate_restrictiveness_score(key_regulations),
                "summary_generated": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error generating zoning summary: {str(e)}")
            return {
                "success": False,
                "error": f"Zoning summary generation failed: {str(e)}"
            }
    
    def _calculate_development_potential(self, regulations: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate development potential based on zoning regulations"""
        dimensional = regulations.get("dimensional_standards", {})
        
        # Estimate development capacity for a typical parcel (1 acre = 43,560 sq ft)
        typical_parcel_sqft = 43560
        
        potential = {
            "typical_parcel_analysis": {
                "parcel_size_sqft": typical_parcel_sqft,
                "parcel_size_acres": 1.0
            }
        }
        
        # Maximum units based on density
        max_density = dimensional.get("max_density_units_acre")
        if max_density:
            potential["max_units_by_density"] = max_density
        
        # Maximum building area based on lot coverage
        max_coverage = dimensional.get("max_lot_coverage_percent")
        if max_coverage:
            max_building_area = typical_parcel_sqft * (max_coverage / 100)
            potential["max_building_area_sqft"] = max_building_area
        
        # Maximum floor area based on FAR
        max_far = dimensional.get("max_far")
        if max_far:
            max_floor_area = typical_parcel_sqft * max_far
            potential["max_floor_area_sqft"] = max_floor_area
            
            # Estimate possible stories
            if max_coverage and max_building_area > 0:
                possible_stories = max_floor_area / max_building_area
                potential["possible_stories_by_far"] = round(possible_stories, 1)
        
        return potential
    
    def _calculate_restrictiveness_score(self, regulations: Dict[str, Any]) -> float:
        """Calculate a restrictiveness score (0-10, higher = more restrictive)"""
        score = 0
        factors = 0
        
        dimensional = regulations.get("dimensional_standards", {})
        setbacks = regulations.get("setback_requirements", {})
        
        # Height restrictions (more restrictive if lower)
        max_height = dimensional.get("max_height_ft")
        if max_height:
            if max_height < 25:
                score += 3
            elif max_height < 35:
                score += 2
            elif max_height < 50:
                score += 1
            factors += 1
        
        # Lot coverage restrictions
        max_coverage = dimensional.get("max_lot_coverage_percent")
        if max_coverage:
            if max_coverage < 30:
                score += 3
            elif max_coverage < 50:
                score += 2
            elif max_coverage < 70:
                score += 1
            factors += 1
        
        # Setback requirements
        total_setbacks = sum(v for v in setbacks.values() if v is not None)
        if total_setbacks > 0:
            if total_setbacks > 100:
                score += 3
            elif total_setbacks > 60:
                score += 2
            elif total_setbacks > 30:
                score += 1
            factors += 1
        
        # FAR restrictions
        max_far = dimensional.get("max_far")
        if max_far:
            if max_far < 0.5:
                score += 3
            elif max_far < 1.0:
                score += 2
            elif max_far < 2.0:
                score += 1
            factors += 1
        
        return (score / max(factors, 1)) if factors > 0 else 0