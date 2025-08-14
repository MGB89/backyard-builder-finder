"""
Backyard analysis service for outdoor space evaluation
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from shapely.geometry import Polygon, Point, LineString, MultiPolygon
from shapely.ops import unary_union
import numpy as np

logger = logging.getLogger(__name__)


class BackyardAnalysisService:
    """Service for analyzing backyard and outdoor space characteristics"""
    
    def __init__(self):
        self.minimum_backyard_area = 400  # sq ft
        self.minimum_backyard_dimension = 20  # ft
        self.privacy_buffer_distance = 6  # ft from property lines
    
    def analyze_backyard(
        self,
        parcel_geometry: Dict[str, Any],
        building_footprints: List[Dict[str, Any]],
        proposed_building: Optional[Dict[str, Any]] = None,
        zoning_requirements: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze backyard space and outdoor areas
        
        Args:
            parcel_geometry: Parcel boundary geometry
            building_footprints: Existing building geometries
            proposed_building: Proposed building geometry (optional)
            zoning_requirements: Zoning requirements for outdoor space
            
        Returns:
            Dict[str, Any]: Backyard analysis results
        """
        try:
            # Convert geometries to Shapely objects
            parcel_polygon = self._create_polygon_from_geometry(parcel_geometry)
            
            if not parcel_polygon or not parcel_polygon.is_valid:
                return {
                    "success": False,
                    "error": "Invalid parcel geometry"
                }
            
            # Create building polygons
            existing_buildings = []
            for building in building_footprints:
                building_polygon = self._create_polygon_from_geometry(building.get("geometry", {}))
                if building_polygon and building_polygon.is_valid:
                    existing_buildings.append(building_polygon)
            
            # Add proposed building if provided
            all_buildings = existing_buildings.copy()
            if proposed_building:
                proposed_polygon = self._create_polygon_from_geometry(proposed_building.get("geometry", {}))
                if proposed_polygon and proposed_polygon.is_valid:
                    all_buildings.append(proposed_polygon)
            
            # Calculate outdoor spaces
            outdoor_areas = self._calculate_outdoor_areas(parcel_polygon, all_buildings)
            
            # Identify backyard areas
            backyard_areas = self._identify_backyard_areas(
                parcel_polygon,
                all_buildings,
                outdoor_areas
            )
            
            # Analyze usable outdoor space
            usable_space = self._analyze_usable_space(
                outdoor_areas,
                backyard_areas,
                parcel_polygon
            )
            
            # Check zoning compliance
            zoning_compliance = self._check_zoning_compliance(
                usable_space,
                zoning_requirements
            )
            
            # Generate privacy analysis
            privacy_analysis = self._analyze_privacy(
                backyard_areas,
                parcel_polygon,
                all_buildings
            )
            
            # Calculate landscaping potential
            landscaping_analysis = self._analyze_landscaping_potential(
                usable_space,
                parcel_polygon
            )
            
            return {
                "success": True,
                "parcel_area_sqft": parcel_polygon.area,
                "total_building_coverage_sqft": sum(b.area for b in all_buildings),
                "outdoor_areas": outdoor_areas,
                "backyard_areas": backyard_areas,
                "usable_space": usable_space,
                "privacy_analysis": privacy_analysis,
                "landscaping_analysis": landscaping_analysis,
                "zoning_compliance": zoning_compliance,
                "recommendations": self._generate_backyard_recommendations(
                    usable_space,
                    privacy_analysis,
                    zoning_compliance
                )
            }
        
        except Exception as e:
            logger.error(f"Backyard analysis error: {str(e)}")
            return {
                "success": False,
                "error": f"Backyard analysis failed: {str(e)}"
            }
    
    def _create_polygon_from_geometry(self, geometry: Dict[str, Any]) -> Optional[Polygon]:
        """Create Shapely polygon from geometry dictionary"""
        try:
            if geometry.get("type") == "Polygon":
                coordinates = geometry.get("coordinates", [])
                if coordinates and len(coordinates) > 0:
                    return Polygon(coordinates[0])
            
            elif geometry.get("type") == "polygon" and geometry.get("rings"):
                rings = geometry.get("rings", [])
                if rings:
                    return Polygon(rings[0])
            
            return None
        
        except Exception as e:
            logger.error(f"Error creating polygon: {str(e)}")
            return None
    
    def _calculate_outdoor_areas(
        self,
        parcel: Polygon,
        buildings: List[Polygon]
    ) -> Dict[str, Any]:
        """Calculate total outdoor areas by subtracting buildings from parcel"""
        try:
            # Union all buildings
            if buildings:
                building_union = unary_union(buildings)
                outdoor_space = parcel.difference(building_union)
            else:
                outdoor_space = parcel
            
            # Handle MultiPolygon result
            if isinstance(outdoor_space, MultiPolygon):
                outdoor_polygons = list(outdoor_space.geoms)
            else:
                outdoor_polygons = [outdoor_space] if outdoor_space.area > 0 else []
            
            total_outdoor_area = sum(poly.area for poly in outdoor_polygons)
            
            return {
                "total_area_sqft": total_outdoor_area,
                "polygons": [self._polygon_to_dict(poly) for poly in outdoor_polygons],
                "polygon_count": len(outdoor_polygons),
                "largest_area_sqft": max((poly.area for poly in outdoor_polygons), default=0)
            }
        
        except Exception as e:
            logger.error(f"Error calculating outdoor areas: {str(e)}")
            return {
                "total_area_sqft": 0,
                "polygons": [],
                "polygon_count": 0,
                "largest_area_sqft": 0
            }
    
    def _identify_backyard_areas(
        self,
        parcel: Polygon,
        buildings: List[Polygon],
        outdoor_areas: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Identify which outdoor areas constitute the backyard"""
        try:
            # Get parcel centroid and bounds
            centroid = parcel.centroid
            bounds = parcel.bounds  # (minx, miny, maxx, maxy)
            
            backyard_polygons = []
            
            # For each outdoor polygon, determine if it's likely a backyard
            for polygon_dict in outdoor_areas.get("polygons", []):
                polygon = self._create_polygon_from_geometry(polygon_dict)
                if not polygon:
                    continue
                
                poly_centroid = polygon.centroid
                
                # Simple heuristic: backyard is typically in the rear (north) portion
                # and larger outdoor spaces
                is_rear = poly_centroid.y > centroid.y
                is_substantial_size = polygon.area > self.minimum_backyard_area
                
                # Check if it's connected to the rear boundary
                rear_boundary = LineString([
                    (bounds[0], bounds[3]),  # Top-left
                    (bounds[2], bounds[3])   # Top-right
                ])
                
                # Buffer the rear boundary slightly to check connection
                rear_buffer = rear_boundary.buffer(5)  # 5 foot buffer
                is_connected_to_rear = polygon.intersects(rear_buffer)
                
                backyard_score = 0
                if is_rear:
                    backyard_score += 3
                if is_substantial_size:
                    backyard_score += 2
                if is_connected_to_rear:
                    backyard_score += 2
                
                # Consider it a backyard if score >= 4
                if backyard_score >= 4:
                    backyard_polygons.append({
                        "geometry": polygon_dict,
                        "area_sqft": polygon.area,
                        "score": backyard_score,
                        "characteristics": {
                            "is_rear": is_rear,
                            "is_substantial_size": is_substantial_size,
                            "is_connected_to_rear": is_connected_to_rear
                        }
                    })
            
            total_backyard_area = sum(p["area_sqft"] for p in backyard_polygons)
            
            return {
                "areas": backyard_polygons,
                "total_area_sqft": total_backyard_area,
                "count": len(backyard_polygons),
                "largest_area_sqft": max((p["area_sqft"] for p in backyard_polygons), default=0)
            }
        
        except Exception as e:
            logger.error(f"Error identifying backyard areas: {str(e)}")
            return {
                "areas": [],
                "total_area_sqft": 0,
                "count": 0,
                "largest_area_sqft": 0
            }
    
    def _analyze_usable_space(
        self,
        outdoor_areas: Dict[str, Any],
        backyard_areas: Dict[str, Any],
        parcel: Polygon
    ) -> Dict[str, Any]:
        """Analyze usable outdoor space characteristics"""
        try:
            usable_characteristics = []
            
            for backyard in backyard_areas.get("areas", []):
                polygon = self._create_polygon_from_geometry(backyard["geometry"])
                if not polygon:
                    continue
                
                # Calculate dimensions
                bounds = polygon.bounds
                width = bounds[2] - bounds[0]
                height = bounds[3] - bounds[1]
                min_dimension = min(width, height)
                max_dimension = max(width, height)
                
                # Analyze shape characteristics
                aspect_ratio = max_dimension / min_dimension if min_dimension > 0 else float('inf')
                
                # Check for different use potentials
                potential_uses = []
                
                if polygon.area >= 400 and min_dimension >= 20:
                    potential_uses.append("entertaining_space")
                
                if polygon.area >= 200 and min_dimension >= 15:
                    potential_uses.append("garden_space")
                
                if polygon.area >= 600 and min_dimension >= 25:
                    potential_uses.append("play_area")
                
                if polygon.area >= 300 and width >= 20:
                    potential_uses.append("pool_potential")
                
                if polygon.area >= 100:
                    potential_uses.append("storage_shed")
                
                # Calculate accessibility score
                accessibility_score = self._calculate_accessibility_score(polygon, parcel)
                
                usable_characteristics.append({
                    "area_sqft": polygon.area,
                    "dimensions": {
                        "width_ft": width,
                        "height_ft": height,
                        "min_dimension_ft": min_dimension,
                        "max_dimension_ft": max_dimension,
                        "aspect_ratio": aspect_ratio
                    },
                    "potential_uses": potential_uses,
                    "accessibility_score": accessibility_score,
                    "is_adequate_size": polygon.area >= self.minimum_backyard_area,
                    "is_adequate_dimension": min_dimension >= self.minimum_backyard_dimension
                })
            
            # Calculate overall metrics
            total_usable_area = sum(char["area_sqft"] for char in usable_characteristics)
            all_potential_uses = set()
            for char in usable_characteristics:
                all_potential_uses.update(char["potential_uses"])
            
            return {
                "total_usable_area_sqft": total_usable_area,
                "areas": usable_characteristics,
                "all_potential_uses": list(all_potential_uses),
                "adequacy": {
                    "meets_minimum_area": total_usable_area >= self.minimum_backyard_area,
                    "meets_minimum_dimension": any(
                        char["is_adequate_dimension"] for char in usable_characteristics
                    ),
                    "quality_score": self._calculate_quality_score(usable_characteristics)
                }
            }
        
        except Exception as e:
            logger.error(f"Error analyzing usable space: {str(e)}")
            return {
                "total_usable_area_sqft": 0,
                "areas": [],
                "all_potential_uses": [],
                "adequacy": {
                    "meets_minimum_area": False,
                    "meets_minimum_dimension": False,
                    "quality_score": 0
                }
            }
    
    def _analyze_privacy(
        self,
        backyard_areas: Dict[str, Any],
        parcel: Polygon,
        buildings: List[Polygon]
    ) -> Dict[str, Any]:
        """Analyze privacy characteristics of backyard areas"""
        try:
            privacy_scores = []
            
            for backyard in backyard_areas.get("areas", []):
                polygon = self._create_polygon_from_geometry(backyard["geometry"])
                if not polygon:
                    continue
                
                # Calculate distance from property boundaries
                parcel_boundary = parcel.boundary
                min_distance_to_boundary = polygon.distance(parcel_boundary)
                
                # Calculate screening potential from existing buildings
                building_screening = 0
                for building in buildings:
                    if polygon.distance(building) < 50:  # Within 50 feet
                        building_screening += 1
                
                # Calculate privacy score (0-10)
                privacy_score = min(10, (min_distance_to_boundary / self.privacy_buffer_distance) * 3 + building_screening * 2)
                
                # Determine privacy level
                if privacy_score >= 7:
                    privacy_level = "high"
                elif privacy_score >= 4:
                    privacy_level = "medium"
                else:
                    privacy_level = "low"
                
                privacy_scores.append({
                    "area_sqft": polygon.area,
                    "privacy_score": privacy_score,
                    "privacy_level": privacy_level,
                    "min_distance_to_boundary_ft": min_distance_to_boundary,
                    "building_screening_count": building_screening,
                    "recommendations": self._get_privacy_recommendations(privacy_score, min_distance_to_boundary)
                })
            
            # Calculate overall privacy
            avg_privacy_score = np.mean([p["privacy_score"] for p in privacy_scores]) if privacy_scores else 0
            
            return {
                "areas": privacy_scores,
                "overall_privacy_score": avg_privacy_score,
                "overall_privacy_level": self._get_privacy_level(avg_privacy_score),
                "privacy_enhancement_potential": self._assess_privacy_enhancement_potential(privacy_scores)
            }
        
        except Exception as e:
            logger.error(f"Error analyzing privacy: {str(e)}")
            return {
                "areas": [],
                "overall_privacy_score": 0,
                "overall_privacy_level": "unknown",
                "privacy_enhancement_potential": []
            }
    
    def _analyze_landscaping_potential(
        self,
        usable_space: Dict[str, Any],
        parcel: Polygon
    ) -> Dict[str, Any]:
        """Analyze landscaping and garden potential"""
        try:
            landscaping_zones = []
            
            for area in usable_space.get("areas", []):
                area_sqft = area["area_sqft"]
                dimensions = area["dimensions"]
                
                # Determine landscaping suitability
                landscaping_types = []
                
                if area_sqft >= 100:
                    landscaping_types.append("flower_beds")
                
                if area_sqft >= 200 and dimensions["min_dimension_ft"] >= 10:
                    landscaping_types.append("vegetable_garden")
                
                if area_sqft >= 300:
                    landscaping_types.append("trees_shrubs")
                
                if area_sqft >= 500 and dimensions["min_dimension_ft"] >= 20:
                    landscaping_types.append("lawn_area")
                
                if area_sqft >= 50:
                    landscaping_types.append("container_garden")
                
                # Calculate maintenance requirements
                maintenance_level = self._calculate_maintenance_level(area_sqft, landscaping_types)
                
                landscaping_zones.append({
                    "area_sqft": area_sqft,
                    "suitable_landscaping": landscaping_types,
                    "maintenance_level": maintenance_level,
                    "irrigation_needed": area_sqft > 200,
                    "soil_preparation_needed": True,  # Generally assumed
                    "estimated_cost_range": self._estimate_landscaping_cost(area_sqft, landscaping_types)
                })
            
            total_landscapable_area = sum(zone["area_sqft"] for zone in landscaping_zones)
            
            return {
                "zones": landscaping_zones,
                "total_landscapable_area_sqft": total_landscapable_area,
                "landscaping_potential_score": min(10, total_landscapable_area / 200),  # Score out of 10
                "recommended_approach": self._recommend_landscaping_approach(landscaping_zones)
            }
        
        except Exception as e:
            logger.error(f"Error analyzing landscaping potential: {str(e)}")
            return {
                "zones": [],
                "total_landscapable_area_sqft": 0,
                "landscaping_potential_score": 0,
                "recommended_approach": "Consult with landscape professional"
            }
    
    def _check_zoning_compliance(
        self,
        usable_space: Dict[str, Any],
        zoning_requirements: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Check compliance with zoning outdoor space requirements"""
        if not zoning_requirements:
            return {
                "compliance_checked": False,
                "note": "No zoning requirements provided"
            }
        
        try:
            total_outdoor_area = usable_space.get("total_usable_area_sqft", 0)
            
            # Check common requirements
            compliance_results = {}
            
            # Minimum outdoor space requirement
            min_outdoor_space = zoning_requirements.get("min_outdoor_space_sqft")
            if min_outdoor_space:
                compliance_results["min_outdoor_space"] = {
                    "required": min_outdoor_space,
                    "provided": total_outdoor_area,
                    "compliant": total_outdoor_area >= min_outdoor_space,
                    "deficit": max(0, min_outdoor_space - total_outdoor_area)
                }
            
            # Open space ratio requirement
            open_space_ratio = zoning_requirements.get("min_open_space_ratio")
            if open_space_ratio:
                # Would need total parcel area to calculate
                pass
            
            overall_compliant = all(
                result.get("compliant", True)
                for result in compliance_results.values()
            )
            
            return {
                "compliance_checked": True,
                "overall_compliant": overall_compliant,
                "requirements": compliance_results,
                "violations": [
                    key for key, result in compliance_results.items()
                    if not result.get("compliant", True)
                ]
            }
        
        except Exception as e:
            logger.error(f"Error checking zoning compliance: {str(e)}")
            return {
                "compliance_checked": False,
                "error": str(e)
            }
    
    def _calculate_accessibility_score(self, polygon: Polygon, parcel: Polygon) -> float:
        """Calculate accessibility score for outdoor area"""
        # Simple scoring based on distance from parcel center and shape
        parcel_centroid = parcel.centroid
        polygon_centroid = polygon.centroid
        
        distance_score = max(0, 10 - (polygon_centroid.distance(parcel_centroid) / 10))
        
        # Shape factor - more regular shapes are more accessible
        area = polygon.area
        perimeter = polygon.length
        shape_factor = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0
        shape_score = shape_factor * 10
        
        return min(10, (distance_score + shape_score) / 2)
    
    def _calculate_quality_score(self, usable_characteristics: List[Dict]) -> float:
        """Calculate overall quality score for backyard spaces"""
        if not usable_characteristics:
            return 0
        
        scores = []
        for char in usable_characteristics:
            area_score = min(10, char["area_sqft"] / 100)  # 1000 sq ft = 10 points
            use_score = len(char["potential_uses"]) * 2
            dimension_score = 10 if char["is_adequate_dimension"] else 5
            access_score = char["accessibility_score"]
            
            total_score = (area_score + use_score + dimension_score + access_score) / 4
            scores.append(total_score)
        
        return np.mean(scores)
    
    def _get_privacy_level(self, score: float) -> str:
        """Convert privacy score to level"""
        if score >= 7:
            return "high"
        elif score >= 4:
            return "medium"
        else:
            return "low"
    
    def _get_privacy_recommendations(self, score: float, distance: float) -> List[str]:
        """Get privacy enhancement recommendations"""
        recommendations = []
        
        if score < 4:
            recommendations.append("Consider installing privacy fencing")
            if distance < self.privacy_buffer_distance:
                recommendations.append("Plant screening vegetation along property lines")
        
        if score < 7:
            recommendations.append("Add landscape features for enhanced privacy")
            recommendations.append("Consider pergola or gazebo for defined outdoor space")
        
        return recommendations
    
    def _assess_privacy_enhancement_potential(self, privacy_scores: List[Dict]) -> List[str]:
        """Assess potential for privacy enhancements"""
        potential = []
        
        for area in privacy_scores:
            if area["privacy_level"] == "low":
                potential.append("High potential for privacy improvement through landscaping")
            elif area["privacy_level"] == "medium":
                potential.append("Moderate potential for privacy enhancement")
        
        return potential
    
    def _calculate_maintenance_level(self, area_sqft: float, landscaping_types: List[str]) -> str:
        """Calculate maintenance level for landscaping"""
        if "lawn_area" in landscaping_types or area_sqft > 1000:
            return "high"
        elif "vegetable_garden" in landscaping_types or area_sqft > 300:
            return "medium"
        else:
            return "low"
    
    def _estimate_landscaping_cost(self, area_sqft: float, landscaping_types: List[str]) -> Dict[str, float]:
        """Estimate landscaping costs"""
        # Rough cost estimates per square foot
        cost_factors = {
            "flower_beds": 15,
            "vegetable_garden": 10,
            "trees_shrubs": 20,
            "lawn_area": 8,
            "container_garden": 25
        }
        
        total_cost_low = 0
        total_cost_high = 0
        
        for landscape_type in landscaping_types:
            base_cost = cost_factors.get(landscape_type, 10)
            type_area = min(area_sqft, 200)  # Limit per type
            
            total_cost_low += type_area * base_cost * 0.8
            total_cost_high += type_area * base_cost * 1.2
        
        return {
            "low_estimate": total_cost_low,
            "high_estimate": total_cost_high
        }
    
    def _recommend_landscaping_approach(self, landscaping_zones: List[Dict]) -> str:
        """Recommend overall landscaping approach"""
        total_area = sum(zone["area_sqft"] for zone in landscaping_zones)
        
        if total_area < 200:
            return "Focus on container gardens and small flower beds"
        elif total_area < 500:
            return "Mixed approach with garden beds and small lawn area"
        elif total_area < 1000:
            return "Full landscaping with lawn, garden areas, and trees"
        else:
            return "Comprehensive landscape design with multiple zones and features"
    
    def _generate_backyard_recommendations(
        self,
        usable_space: Dict[str, Any],
        privacy_analysis: Dict[str, Any],
        zoning_compliance: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for backyard improvements"""
        recommendations = []
        
        # Area-based recommendations
        total_area = usable_space.get("total_usable_area_sqft", 0)
        
        if total_area < self.minimum_backyard_area:
            recommendations.append("Consider maximizing usable outdoor space through efficient design")
        
        # Privacy recommendations
        privacy_level = privacy_analysis.get("overall_privacy_level", "unknown")
        if privacy_level == "low":
            recommendations.append("Enhance privacy with fencing or landscaping")
        
        # Compliance recommendations
        if not zoning_compliance.get("overall_compliant", True):
            recommendations.append("Address zoning compliance issues for outdoor space requirements")
        
        # Use potential recommendations
        potential_uses = usable_space.get("all_potential_uses", [])
        if "pool_potential" in potential_uses:
            recommendations.append("Consider pool installation feasibility")
        if "garden_space" in potential_uses:
            recommendations.append("Excellent potential for gardening and landscaping")
        
        # General recommendations
        recommendations.append("Consult with landscape architect for optimal design")
        recommendations.append("Consider outdoor lighting for evening use")
        
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