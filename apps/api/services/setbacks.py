"""
Setback analysis service for zoning compliance
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
import numpy as np

logger = logging.getLogger(__name__)


class SetbackAnalysisService:
    """Service for analyzing building setback requirements and compliance"""
    
    def __init__(self):
        self.default_setbacks = {
            "front": 25.0,
            "rear": 25.0,
            "side": 10.0,
            "corner_side": 15.0
        }
    
    def analyze_setbacks(
        self,
        parcel_geometry: Dict[str, Any],
        zoning_setbacks: Dict[str, float],
        proposed_building: Optional[Dict[str, Any]] = None,
        existing_buildings: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Analyze setback requirements and compliance
        
        Args:
            parcel_geometry: Parcel boundary geometry
            zoning_setbacks: Required setbacks by direction
            proposed_building: Proposed building geometry (optional)
            existing_buildings: Existing building geometries (optional)
            
        Returns:
            Dict[str, Any]: Setback analysis results
        """
        try:
            # Convert parcel geometry to Shapely polygon
            parcel_polygon = self._create_polygon_from_geometry(parcel_geometry)
            
            if not parcel_polygon or not parcel_polygon.is_valid:
                return {
                    "success": False,
                    "error": "Invalid parcel geometry"
                }
            
            # Determine parcel orientation and boundaries
            parcel_info = self._analyze_parcel_orientation(parcel_polygon)
            
            # Calculate setback lines
            setback_lines = self._calculate_setback_lines(
                parcel_polygon,
                zoning_setbacks,
                parcel_info
            )
            
            # Calculate buildable area
            buildable_area = self._calculate_buildable_area(
                parcel_polygon,
                setback_lines
            )
            
            # Analyze compliance for proposed building
            compliance_result = None
            if proposed_building:
                compliance_result = self._analyze_building_compliance(
                    proposed_building,
                    setback_lines,
                    parcel_info
                )
            
            # Analyze existing buildings
            existing_compliance = []
            if existing_buildings:
                for building in existing_buildings:
                    building_compliance = self._analyze_building_compliance(
                        building,
                        setback_lines,
                        parcel_info
                    )
                    existing_compliance.append(building_compliance)
            
            return {
                "success": True,
                "parcel_info": parcel_info,
                "required_setbacks": zoning_setbacks,
                "setback_lines": setback_lines,
                "buildable_area": {
                    "geometry": self._polygon_to_dict(buildable_area),
                    "area_sqft": buildable_area.area,
                    "area_acres": buildable_area.area / 43560
                },
                "proposed_compliance": compliance_result,
                "existing_compliance": existing_compliance,
                "recommendations": self._generate_setback_recommendations(
                    buildable_area,
                    compliance_result,
                    zoning_setbacks
                )
            }
        
        except Exception as e:
            logger.error(f"Setback analysis error: {str(e)}")
            return {
                "success": False,
                "error": f"Setback analysis failed: {str(e)}"
            }
    
    def _create_polygon_from_geometry(self, geometry: Dict[str, Any]) -> Optional[Polygon]:
        """Create Shapely polygon from geometry dictionary"""
        try:
            if geometry.get("type") == "Polygon":
                coordinates = geometry.get("coordinates", [])
                if coordinates and len(coordinates) > 0:
                    # Use exterior ring only for simplicity
                    exterior_ring = coordinates[0]
                    return Polygon(exterior_ring)
            
            elif geometry.get("type") == "polygon" and geometry.get("rings"):
                # ArcGIS format
                rings = geometry.get("rings", [])
                if rings:
                    return Polygon(rings[0])
            
            return None
        
        except Exception as e:
            logger.error(f"Error creating polygon: {str(e)}")
            return None
    
    def _analyze_parcel_orientation(self, parcel: Polygon) -> Dict[str, Any]:
        """Analyze parcel orientation and determine front, rear, and side boundaries"""
        # Get minimum rotated rectangle to determine orientation
        min_rect = parcel.minimum_rotated_rectangle
        
        # Get the coordinates of the minimum rectangle
        coords = list(min_rect.exterior.coords)
        
        # Calculate edge lengths and angles
        edges = []
        for i in range(len(coords) - 1):
            p1 = coords[i]
            p2 = coords[i + 1]
            length = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            angle = np.arctan2(p2[1] - p1[1], p2[0] - p1[0])
            edges.append({
                "start": p1,
                "end": p2,
                "length": length,
                "angle": np.degrees(angle),
                "midpoint": ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
            })
        
        # Determine front boundary (typically the longest edge facing the street)
        # For now, assume the southernmost edge is the front
        centroid = parcel.centroid
        
        # Find the boundary closest to the centroid's south
        front_edge = min(edges, key=lambda e: e["midpoint"][1])
        
        # Determine other boundaries relative to front
        parcel_info = {
            "centroid": [centroid.x, centroid.y],
            "area_sqft": parcel.area,
            "perimeter_ft": parcel.length,
            "front_edge": front_edge,
            "orientation": "determined_from_geometry",
            "is_corner_lot": False,  # Would need street data to determine
            "edges": edges
        }
        
        return parcel_info
    
    def _calculate_setback_lines(
        self,
        parcel: Polygon,
        setbacks: Dict[str, float],
        parcel_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate setback lines for each direction"""
        # Use negative buffer to create inward setbacks
        setback_polygons = {}
        
        for direction, distance in setbacks.items():
            if distance > 0:
                # Create buffer inward from parcel boundary
                setback_polygon = parcel.buffer(-distance / 3.28084)  # Convert feet to meters
                
                if setback_polygon.is_valid and not setback_polygon.is_empty:
                    setback_polygons[direction] = {
                        "distance_ft": distance,
                        "geometry": self._polygon_to_dict(setback_polygon),
                        "area_sqft": setback_polygon.area * 10.7639  # Convert sq meters to sq feet
                    }
                else:
                    setback_polygons[direction] = {
                        "distance_ft": distance,
                        "geometry": None,
                        "area_sqft": 0,
                        "note": "Setback distance too large for parcel"
                    }
        
        return setback_polygons
    
    def _calculate_buildable_area(
        self,
        parcel: Polygon,
        setback_lines: Dict[str, Any]
    ) -> Polygon:
        """Calculate the buildable area after applying all setbacks"""
        try:
            buildable_area = parcel
            
            # Apply each setback by intersecting with setback polygon
            for direction, setback_info in setback_lines.items():
                if setback_info.get("geometry"):
                    setback_polygon = self._create_polygon_from_geometry(setback_info["geometry"])
                    if setback_polygon and setback_polygon.is_valid:
                        buildable_area = buildable_area.intersection(setback_polygon)
            
            # Ensure result is valid
            if not buildable_area.is_valid:
                buildable_area = buildable_area.buffer(0)  # Fix invalid geometry
            
            return buildable_area if buildable_area.is_valid else Polygon()
        
        except Exception as e:
            logger.error(f"Error calculating buildable area: {str(e)}")
            return Polygon()
    
    def _analyze_building_compliance(
        self,
        building: Dict[str, Any],
        setback_lines: Dict[str, Any],
        parcel_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze building compliance with setback requirements"""
        try:
            building_polygon = self._create_polygon_from_geometry(building.get("geometry", {}))
            
            if not building_polygon or not building_polygon.is_valid:
                return {
                    "compliant": False,
                    "error": "Invalid building geometry"
                }
            
            compliance_details = {}
            overall_compliant = True
            violations = []
            
            # Check compliance with each setback
            for direction, setback_info in setback_lines.items():
                if setback_info.get("geometry"):
                    setback_polygon = self._create_polygon_from_geometry(setback_info["geometry"])
                    
                    if setback_polygon and setback_polygon.is_valid:
                        # Check if building is within setback area
                        intersection = building_polygon.intersection(setback_polygon)
                        intersection_area = intersection.area if intersection else 0
                        
                        # Building should be completely within the setback polygon
                        is_compliant = building_polygon.within(setback_polygon)
                        
                        if not is_compliant:
                            overall_compliant = False
                            violations.append(f"{direction.title()} setback violation")
                        
                        compliance_details[direction] = {
                            "compliant": is_compliant,
                            "required_distance_ft": setback_info["distance_ft"],
                            "intersection_area_sqft": intersection_area * 10.7639,  # Convert to sq ft
                            "violation_area_sqft": (building_polygon.area - intersection_area) * 10.7639 if not is_compliant else 0
                        }
            
            return {
                "compliant": overall_compliant,
                "building_area_sqft": building_polygon.area * 10.7639,
                "compliance_details": compliance_details,
                "violations": violations,
                "violation_count": len(violations)
            }
        
        except Exception as e:
            logger.error(f"Error analyzing building compliance: {str(e)}")
            return {
                "compliant": False,
                "error": f"Compliance analysis failed: {str(e)}"
            }
    
    def _generate_setback_recommendations(
        self,
        buildable_area: Polygon,
        compliance_result: Optional[Dict[str, Any]],
        required_setbacks: Dict[str, float]
    ) -> List[str]:
        """Generate recommendations for setback compliance"""
        recommendations = []
        
        if buildable_area.is_empty:
            recommendations.append("Parcel too small for any development with current setback requirements")
            recommendations.append("Consider applying for setback variance")
            return recommendations
        
        if buildable_area.area < 1000:  # Less than 1000 sq ft buildable
            recommendations.append("Limited buildable area due to setback requirements")
            recommendations.append("Consider compact building design")
        
        if compliance_result and not compliance_result.get("compliant"):
            violations = compliance_result.get("violations", [])
            for violation in violations:
                recommendations.append(f"Address {violation}")
            
            recommendations.append("Consider redesigning building to meet setback requirements")
            recommendations.append("Evaluate potential for setback variance application")
        
        # General recommendations
        recommendations.append("Verify setback requirements with local planning department")
        recommendations.append("Consider hiring a surveyor for precise boundary determination")
        
        return recommendations
    
    def _polygon_to_dict(self, polygon: Polygon) -> Dict[str, Any]:
        """Convert Shapely polygon to dictionary format"""
        if polygon.is_empty:
            return None
        
        exterior_coords = list(polygon.exterior.coords)
        
        return {
            "type": "Polygon",
            "coordinates": [exterior_coords]
        }
    
    def get_minimum_setbacks_for_area(
        self,
        parcel_geometry: Dict[str, Any],
        target_building_area: float
    ) -> Dict[str, Any]:
        """
        Calculate minimum setbacks needed to achieve target building area
        
        Args:
            parcel_geometry: Parcel boundary geometry
            target_building_area: Desired building area in sq ft
            
        Returns:
            Dict[str, Any]: Minimum setback analysis
        """
        try:
            parcel_polygon = self._create_polygon_from_geometry(parcel_geometry)
            
            if not parcel_polygon:
                return {
                    "success": False,
                    "error": "Invalid parcel geometry"
                }
            
            parcel_area = parcel_polygon.area * 10.7639  # Convert to sq ft
            
            if target_building_area >= parcel_area:
                return {
                    "success": False,
                    "error": "Target building area exceeds parcel area"
                }
            
            # Binary search for optimal setback
            min_setback = 0
            max_setback = min(parcel_polygon.bounds[2] - parcel_polygon.bounds[0],
                             parcel_polygon.bounds[3] - parcel_polygon.bounds[1]) / 2
            
            optimal_setback = None
            tolerance = 50  # 50 sq ft tolerance
            
            for _ in range(20):  # Limit iterations
                current_setback = (min_setback + max_setback) / 2
                
                # Apply uniform setback
                setbacks = {
                    "front": current_setback,
                    "rear": current_setback,
                    "side": current_setback,
                    "corner_side": current_setback
                }
                
                parcel_info = self._analyze_parcel_orientation(parcel_polygon)
                setback_lines = self._calculate_setback_lines(parcel_polygon, setbacks, parcel_info)
                buildable_area = self._calculate_buildable_area(parcel_polygon, setback_lines)
                
                buildable_area_sqft = buildable_area.area * 10.7639
                
                if abs(buildable_area_sqft - target_building_area) <= tolerance:
                    optimal_setback = current_setback
                    break
                elif buildable_area_sqft > target_building_area:
                    min_setback = current_setback
                else:
                    max_setback = current_setback
            
            return {
                "success": True,
                "target_building_area_sqft": target_building_area,
                "parcel_area_sqft": parcel_area,
                "optimal_uniform_setback_ft": optimal_setback,
                "achievable_area_sqft": buildable_area.area * 10.7639 if optimal_setback else 0,
                "coverage_percentage": (target_building_area / parcel_area) * 100
            }
        
        except Exception as e:
            logger.error(f"Error calculating minimum setbacks: {str(e)}")
            return {
                "success": False,
                "error": f"Minimum setback calculation failed: {str(e)}"
            }