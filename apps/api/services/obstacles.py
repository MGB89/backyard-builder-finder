"""
Obstacle detection and analysis service for development constraints
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from functools import lru_cache
import json
import hashlib
from shapely.geometry import Polygon, Point, LineString, MultiPolygon
from shapely.ops import unary_union, transform
from shapely.validation import make_valid
from pyproj import Transformer
import numpy as np

logger = logging.getLogger(__name__)


class ObstacleAnalysisService:
    """Service for detecting and analyzing development obstacles and constraints"""
    
    def __init__(self):
        self.obstacle_types = {
            "natural": ["trees", "water_bodies", "wetlands", "steep_slopes", "rock_outcrops"],
            "infrastructure": ["utility_lines", "septic_systems", "wells", "driveways", "walkways"],
            "regulatory": ["easements", "setbacks", "buffer_zones", "protected_areas"],
            "existing_structures": ["buildings", "sheds", "pools", "decks", "fences"]
        }
        
        self.buffer_distances = {
            "utility_lines": 10,  # feet
            "septic_systems": 50,
            "wells": 25,
            "trees": 15,
            "water_bodies": 25,
            "wetlands": 100,
            "steep_slopes": 20
        }
        
        # Cache for coordinate transformations
        self._transformer_cache = {}
        # WGS84 (lat/lon) to Web Mercator for area calculations
        self.to_mercator = self._get_transformer("EPSG:4326", "EPSG:3857")
        self.from_mercator = self._get_transformer("EPSG:3857", "EPSG:4326")
    
    def analyze_obstacles(
        self,
        parcel_geometry: Dict[str, Any],
        existing_features: List[Dict[str, Any]],
        proposed_development: Optional[Dict[str, Any]] = None,
        environmental_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze obstacles and constraints for development
        
        Args:
            parcel_geometry: Parcel boundary geometry
            existing_features: List of existing features and obstacles
            proposed_development: Proposed development geometry (optional)
            environmental_data: Environmental constraint data (optional)
            
        Returns:
            Dict[str, Any]: Obstacle analysis results
        """
        try:
            # Convert parcel geometry
            parcel_polygon = self._create_polygon_from_geometry(parcel_geometry)
            
            if not parcel_polygon or not parcel_polygon.is_valid:
                return {
                    "success": False,
                    "error": "Invalid parcel geometry"
                }
            
            # Process existing features
            obstacle_inventory = self._process_existing_features(existing_features, parcel_polygon)
            
            # Add environmental constraints
            if environmental_data:
                environmental_constraints = self._process_environmental_data(environmental_data, parcel_polygon)
                obstacle_inventory.update(environmental_constraints)
            
            # Calculate constraint zones
            constraint_zones = self._calculate_constraint_zones(obstacle_inventory, parcel_polygon)
            
            # Calculate developable area
            developable_area = self._calculate_developable_area(parcel_polygon, constraint_zones)
            
            # Analyze proposed development conflicts
            conflict_analysis = None
            if proposed_development:
                conflict_analysis = self._analyze_development_conflicts(
                    proposed_development,
                    obstacle_inventory,
                    constraint_zones
                )
            
            # Generate mitigation strategies
            mitigation_strategies = self._generate_mitigation_strategies(
                obstacle_inventory,
                conflict_analysis
            )
            
            # Calculate development feasibility
            feasibility_assessment = self._assess_development_feasibility(
                developable_area,
                parcel_polygon,
                obstacle_inventory
            )
            
            return {
                "success": True,
                "parcel_area_sqft": self._convert_area_to_sqft(parcel_polygon.area),
                "obstacle_inventory": obstacle_inventory,
                "constraint_zones": constraint_zones,
                "developable_area": developable_area,
                "conflict_analysis": conflict_analysis,
                "mitigation_strategies": mitigation_strategies,
                "feasibility_assessment": feasibility_assessment,
                "recommendations": self._generate_obstacle_recommendations(
                    obstacle_inventory,
                    developable_area,
                    conflict_analysis
                )
            }
        
        except Exception as e:
            logger.error(f"Obstacle analysis error: {str(e)}")
            return {
                "success": False,
                "error": f"Obstacle analysis failed: {str(e)}"
            }
    
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
    
    def _process_existing_features(
        self,
        features: List[Dict[str, Any]],
        parcel: Polygon
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Process existing features into obstacle inventory"""
        obstacle_inventory = {}
        
        for category in self.obstacle_types:
            obstacle_inventory[category] = []
        
        for feature in features:
            feature_type = feature.get("type", "unknown").lower()
            geometry = feature.get("geometry")
            
            if not geometry:
                continue
            
            # Determine obstacle category
            category = self._categorize_obstacle(feature_type)
            
            # Create geometry object
            obstacle_geometry = self._create_polygon_from_geometry(geometry)
            if not obstacle_geometry:
                # Try as point if polygon creation fails
                coords = self._extract_coordinates(geometry)
                if coords:
                    obstacle_geometry = Point(coords[0])
            
            if obstacle_geometry:
                # Calculate buffer zone if applicable (convert feet to meters)
                buffer_distance = self.buffer_distances.get(feature_type, 0)
                buffer_distance_m = buffer_distance * 0.3048  # Convert feet to meters
                constraint_zone = obstacle_geometry.buffer(buffer_distance_m) if buffer_distance > 0 else obstacle_geometry
                
                obstacle_info = {
                    "id": feature.get("id", f"{feature_type}_{len(obstacle_inventory[category])}"),
                    "type": feature_type,
                    "geometry": self._geometry_to_dict(obstacle_geometry),
                    "constraint_zone": self._geometry_to_dict(constraint_zone),
                    "buffer_distance_ft": buffer_distance,
                    "area_sqft": self._convert_area_to_sqft(obstacle_geometry.area) if hasattr(obstacle_geometry, 'area') else 0,
                    "severity": feature.get("severity", "medium"),
                    "removable": feature.get("removable", False),
                    "mitigation_cost": feature.get("mitigation_cost"),
                    "attributes": feature.get("attributes", {})
                }
                
                obstacle_inventory[category].append(obstacle_info)
        
        return obstacle_inventory
    
    def _process_environmental_data(
        self,
        environmental_data: Dict[str, Any],
        parcel: Polygon
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Process environmental constraint data"""
        environmental_obstacles = {"natural": [], "regulatory": []}
        
        # Process different environmental constraints
        constraints = [
            ("flood_zone", "regulatory", 0, "high"),
            ("wetlands", "natural", 100, "high"),
            ("steep_slopes", "natural", 20, "medium"),
            ("soil_constraints", "natural", 0, "medium"),
            ("endangered_species_habitat", "regulatory", 200, "high")
        ]
        
        for constraint_type, category, buffer_dist, severity in constraints:
            if constraint_type in environmental_data:
                constraint_geometry = self._create_polygon_from_geometry(
                    environmental_data[constraint_type]
                )
                
                if constraint_geometry:
                    constraint_zone = constraint_geometry.buffer(buffer_dist) if buffer_dist > 0 else constraint_geometry
                    
                    obstacle_info = {
                        "id": f"env_{constraint_type}",
                        "type": constraint_type,
                        "geometry": self._geometry_to_dict(constraint_geometry),
                        "constraint_zone": self._geometry_to_dict(constraint_zone),
                        "buffer_distance_ft": buffer_dist,
                        "area_sqft": self._convert_area_to_sqft(constraint_geometry.area),
                        "severity": severity,
                        "removable": False,
                        "mitigation_cost": None,
                        "attributes": environmental_data.get(f"{constraint_type}_attributes", {})
                    }
                    
                    environmental_obstacles[category].append(obstacle_info)
        
        return environmental_obstacles
    
    def _calculate_constraint_zones(
        self,
        obstacle_inventory: Dict[str, List[Dict[str, Any]]],
        parcel: Polygon
    ) -> Dict[str, Any]:
        """Calculate combined constraint zones"""
        try:
            all_constraints = []
            constraint_by_severity = {"high": [], "medium": [], "low": []}
            
            # Collect all constraint zones
            for category, obstacles in obstacle_inventory.items():
                for obstacle in obstacles:
                    constraint_geom = self._create_polygon_from_geometry(
                        obstacle["constraint_zone"]
                    )
                    
                    if constraint_geom and constraint_geom.is_valid:
                        # Intersect with parcel boundary
                        parcel_constraint = constraint_geom.intersection(parcel)
                        
                        if not parcel_constraint.is_empty:
                            all_constraints.append(parcel_constraint)
                            
                            severity = obstacle.get("severity", "medium")
                            constraint_by_severity[severity].append(parcel_constraint)
            
            # Union constraints by severity
            severity_zones = {}
            for severity, constraints in constraint_by_severity.items():
                if constraints:
                    union_geom = unary_union(constraints)
                    severity_zones[severity] = {
                        "geometry": self._geometry_to_dict(union_geom),
                        "area_sqft": self._convert_area_to_sqft(union_geom.area),
                        "count": len(constraints)
                    }
                else:
                    severity_zones[severity] = {
                        "geometry": None,
                        "area_sqft": 0,
                        "count": 0
                    }
            
            # Union all constraints
            total_constrained_area = unary_union(all_constraints) if all_constraints else Polygon()
            
            return {
                "total_constrained_area": {
                    "geometry": self._geometry_to_dict(total_constrained_area),
                    "area_sqft": self._convert_area_to_sqft(total_constrained_area.area),
                    "percentage_of_parcel": (total_constrained_area.area / parcel.area) * 100
                },
                "by_severity": severity_zones,
                "total_obstacles": sum(len(obstacles) for obstacles in obstacle_inventory.values())
            }
        
        except Exception as e:
            logger.error(f"Error calculating constraint zones: {str(e)}")
            return {
                "total_constrained_area": {"geometry": None, "area_sqft": 0, "percentage_of_parcel": 0},
                "by_severity": {"high": {}, "medium": {}, "low": {}},
                "total_obstacles": 0
            }
    
    def _calculate_developable_area(
        self,
        parcel: Polygon,
        constraint_zones: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate developable area after removing constraints"""
        try:
            total_constrained = constraint_zones["total_constrained_area"]
            constrained_geometry = self._create_polygon_from_geometry(total_constrained["geometry"])
            
            if constrained_geometry and constrained_geometry.is_valid:
                developable_geometry = parcel.difference(constrained_geometry)
            else:
                developable_geometry = parcel
            
            # Handle MultiPolygon result
            if isinstance(developable_geometry, MultiPolygon):
                developable_polygons = list(developable_geometry.geoms)
            else:
                developable_polygons = [developable_geometry] if developable_geometry.area > 0 else []
            
            # Find largest contiguous area
            largest_area = max(developable_polygons, key=lambda p: p.area) if developable_polygons else Polygon()
            
            return {
                "total_area_sqft": self._convert_area_to_sqft(developable_geometry.area),
                "percentage_of_parcel": (developable_geometry.area / parcel.area) * 100,
                "geometry": self._geometry_to_dict(developable_geometry),
                "contiguous_areas": [
                    {
                        "geometry": self._geometry_to_dict(poly),
                        "area_sqft": self._convert_area_to_sqft(poly.area)
                    }
                    for poly in developable_polygons
                ],
                "largest_contiguous_area_sqft": self._convert_area_to_sqft(largest_area.area),
                "fragmentation_score": len(developable_polygons) / max(1, self._convert_area_to_sqft(developable_geometry.area) / 1000)
            }
        
        except Exception as e:
            logger.error(f"Error calculating developable area: {str(e)}")
            return {
                "total_area_sqft": 0,
                "percentage_of_parcel": 0,
                "geometry": None,
                "contiguous_areas": [],
                "largest_contiguous_area_sqft": 0,
                "fragmentation_score": 0
            }
    
    def _analyze_development_conflicts(
        self,
        proposed_development: Dict[str, Any],
        obstacle_inventory: Dict[str, List[Dict[str, Any]]],
        constraint_zones: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze conflicts between proposed development and obstacles"""
        try:
            proposed_geometry = self._create_polygon_from_geometry(
                proposed_development.get("geometry", {})
            )
            
            if not proposed_geometry or not proposed_geometry.is_valid:
                return {
                    "conflict_detected": False,
                    "error": "Invalid proposed development geometry"
                }
            
            conflicts = []
            total_conflict_area = 0
            
            # Check conflicts with each obstacle
            for category, obstacles in obstacle_inventory.items():
                for obstacle in obstacles:
                    constraint_geom = self._create_polygon_from_geometry(
                        obstacle["constraint_zone"]
                    )
                    
                    if constraint_geom and constraint_geom.is_valid:
                        intersection = proposed_geometry.intersection(constraint_geom)
                        
                        if not intersection.is_empty:
                            conflict_area = intersection.area
                            total_conflict_area += conflict_area
                            
                            conflicts.append({
                                "obstacle_id": obstacle["id"],
                                "obstacle_type": obstacle["type"],
                                "category": category,
                                "severity": obstacle["severity"],
                                "conflict_area_sqft": self._convert_area_to_sqft(conflict_area),
                                "conflict_percentage": (conflict_area / proposed_geometry.area) * 100,
                                "mitigation_required": obstacle["severity"] in ["high", "medium"],
                                "estimated_mitigation_cost": obstacle.get("mitigation_cost"),
                                "removable": obstacle.get("removable", False)
                            })
            
            # Categorize conflicts by severity
            high_severity_conflicts = [c for c in conflicts if c["severity"] == "high"]
            medium_severity_conflicts = [c for c in conflicts if c["severity"] == "medium"]
            low_severity_conflicts = [c for c in conflicts if c["severity"] == "low"]
            
            return {
                "conflict_detected": len(conflicts) > 0,
                "total_conflicts": len(conflicts),
                "total_conflict_area_sqft": self._convert_area_to_sqft(total_conflict_area),
                "conflict_percentage": (total_conflict_area / proposed_geometry.area) * 100,
                "conflicts": conflicts,
                "by_severity": {
                    "high": high_severity_conflicts,
                    "medium": medium_severity_conflicts,
                    "low": low_severity_conflicts
                },
                "development_feasibility": self._assess_conflict_feasibility(conflicts),
                "required_mitigations": [c for c in conflicts if c["mitigation_required"]]
            }
        
        except Exception as e:
            logger.error(f"Error analyzing development conflicts: {str(e)}")
            return {
                "conflict_detected": False,
                "error": f"Conflict analysis failed: {str(e)}"
            }
    
    def _generate_mitigation_strategies(
        self,
        obstacle_inventory: Dict[str, List[Dict[str, Any]]],
        conflict_analysis: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate mitigation strategies for obstacles"""
        strategies = []
        
        # General mitigation strategies by obstacle type
        mitigation_options = {
            "trees": {
                "strategy": "Tree preservation or removal",
                "options": ["Relocate development", "Tree removal with permits", "Design around existing trees"],
                "cost_range": "$500-$5000 per tree"
            },
            "utility_lines": {
                "strategy": "Utility relocation or protection",
                "options": ["Underground relocation", "Overhead clearance", "Protective barriers"],
                "cost_range": "$10,000-$50,000"
            },
            "wetlands": {
                "strategy": "Wetland mitigation banking",
                "options": ["Avoid impact", "Mitigation banking", "Wetland creation"],
                "cost_range": "$50,000-$200,000"
            },
            "steep_slopes": {
                "strategy": "Slope stabilization",
                "options": ["Retaining walls", "Terracing", "Slope modification"],
                "cost_range": "$100-$500 per sq ft"
            },
            "septic_systems": {
                "strategy": "System relocation or upgrade",
                "options": ["System relocation", "Connection to sewer", "System upgrade"],
                "cost_range": "$15,000-$40,000"
            }
        }
        
        # Add strategies based on conflicts
        if conflict_analysis and conflict_analysis.get("conflict_detected"):
            for conflict in conflict_analysis.get("conflicts", []):
                obstacle_type = conflict["obstacle_type"]
                
                if obstacle_type in mitigation_options:
                    strategy_info = mitigation_options[obstacle_type].copy()
                    strategy_info.update({
                        "obstacle_id": conflict["obstacle_id"],
                        "conflict_area_sqft": conflict["conflict_area_sqft"],
                        "severity": conflict["severity"],
                        "required": conflict["mitigation_required"]
                    })
                    strategies.append(strategy_info)
        
        # Add general strategies for all obstacles
        for category, obstacles in obstacle_inventory.items():
            for obstacle in obstacles:
                obstacle_type = obstacle["type"]
                
                if obstacle_type in mitigation_options and not any(
                    s.get("obstacle_id") == obstacle["id"] for s in strategies
                ):
                    strategy_info = mitigation_options[obstacle_type].copy()
                    strategy_info.update({
                        "obstacle_id": obstacle["id"],
                        "severity": obstacle["severity"],
                        "required": False  # Not in conflict, so optional
                    })
                    strategies.append(strategy_info)
        
        return strategies
    
    def _assess_development_feasibility(
        self,
        developable_area: Dict[str, Any],
        parcel: Polygon,
        obstacle_inventory: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Assess overall development feasibility"""
        try:
            total_obstacles = sum(len(obstacles) for obstacles in obstacle_inventory.values())
            developable_percentage = developable_area.get("percentage_of_parcel", 0)
            largest_contiguous = developable_area.get("largest_contiguous_area_sqft", 0)
            fragmentation = developable_area.get("fragmentation_score", 0)
            
            # Calculate feasibility score (0-10)
            area_score = min(10, developable_percentage / 10)  # 100% = 10 points
            contiguous_score = min(10, largest_contiguous / 2000)  # 20,000 sq ft = 10 points
            obstacle_score = max(0, 10 - total_obstacles)  # Fewer obstacles = higher score
            fragmentation_score = max(0, 10 - fragmentation * 2)  # Less fragmentation = higher score
            
            overall_score = (area_score + contiguous_score + obstacle_score + fragmentation_score) / 4
            
            # Determine feasibility level
            if overall_score >= 7:
                feasibility_level = "high"
            elif overall_score >= 4:
                feasibility_level = "medium"
            else:
                feasibility_level = "low"
            
            # Identify limiting factors
            limiting_factors = []
            if developable_percentage < 50:
                limiting_factors.append("Limited developable area")
            if largest_contiguous < 5000:
                limiting_factors.append("Insufficient contiguous space")
            if total_obstacles > 5:
                limiting_factors.append("High obstacle density")
            if fragmentation > 3:
                limiting_factors.append("Highly fragmented developable areas")
            
            return {
                "overall_score": overall_score,
                "feasibility_level": feasibility_level,
                "developable_percentage": developable_percentage,
                "largest_contiguous_area_sqft": largest_contiguous,
                "total_obstacles": total_obstacles,
                "fragmentation_score": fragmentation,
                "limiting_factors": limiting_factors,
                "development_recommendations": self._get_feasibility_recommendations(
                    feasibility_level, limiting_factors
                )
            }
        
        except Exception as e:
            logger.error(f"Error assessing feasibility: {str(e)}")
            return {
                "overall_score": 0,
                "feasibility_level": "unknown",
                "error": str(e)
            }
    
    def _categorize_obstacle(self, obstacle_type: str) -> str:
        """Categorize obstacle into appropriate category"""
        for category, types in self.obstacle_types.items():
            if obstacle_type in types:
                return category
        return "existing_structures"  # Default category
    
    def _extract_coordinates(self, geometry: Dict[str, Any]) -> Optional[List[Tuple[float, float]]]:
        """Extract coordinates from geometry"""
        try:
            if geometry.get("type") == "Point":
                coords = geometry.get("coordinates", [])
                return [tuple(coords)] if len(coords) >= 2 else None
            
            elif geometry.get("type") == "Polygon":
                coords = geometry.get("coordinates", [])
                return coords[0] if coords else None
            
            return None
        
        except Exception:
            return None
    
    def _convert_area_to_sqft(self, area_sq_meters: float) -> float:
        """Convert square meters to square feet"""
        return area_sq_meters * 10.7639

    def _convert_length_to_ft(self, length_meters: float) -> float:
        """Convert meters to feet"""
        return length_meters * 3.28084

    @lru_cache(maxsize=128)
    def _geometry_to_dict_cached(self, geometry_wkt: str) -> Dict[str, Any]:
        """Cached geometry to dict conversion"""
        from shapely import wkt
        geometry = wkt.loads(geometry_wkt)
        return self._geometry_to_dict(geometry)

    def _geometry_to_dict(self, geometry) -> Optional[Dict[str, Any]]:
        """Convert Shapely geometry to dictionary in WGS84"""
        try:
            if hasattr(geometry, 'is_empty') and geometry.is_empty:
                return None
            
            if hasattr(geometry, 'geom_type'):
                # Transform back to WGS84 for output
                geometry_wgs84 = transform(self.from_mercator.transform, geometry)
                
                if geometry_wgs84.geom_type == 'Point':
                    return {
                        "type": "Point",
                        "coordinates": [geometry_wgs84.x, geometry_wgs84.y],
                        "crs": "EPSG:4326"
                    }
                elif geometry_wgs84.geom_type == 'Polygon':
                    coords = [list(geometry_wgs84.exterior.coords)]
                    if geometry_wgs84.interiors:
                        coords.extend([list(interior.coords) for interior in geometry_wgs84.interiors])
                    return {
                        "type": "Polygon",
                        "coordinates": coords,
                        "crs": "EPSG:4326"
                    }
                elif geometry_wgs84.geom_type == 'MultiPolygon':
                    coords = []
                    for poly in geometry_wgs84.geoms:
                        poly_coords = [list(poly.exterior.coords)]
                        if poly.interiors:
                            poly_coords.extend([list(interior.coords) for interior in poly.interiors])
                        coords.append(poly_coords)
                    return {
                        "type": "MultiPolygon",
                        "coordinates": coords,
                        "crs": "EPSG:4326"
                    }
            
            return None
        
        except Exception as e:
            logger.error(f"Error converting geometry: {str(e)}")
            return None
    
    def _assess_conflict_feasibility(self, conflicts: List[Dict[str, Any]]) -> str:
        """Assess feasibility based on conflicts"""
        if not conflicts:
            return "high"
        
        high_severity = len([c for c in conflicts if c["severity"] == "high"])
        total_conflict_percentage = sum(c["conflict_percentage"] for c in conflicts)
        
        if high_severity > 0 or total_conflict_percentage > 50:
            return "low"
        elif total_conflict_percentage > 25:
            return "medium"
        else:
            return "high"
    
    def _get_feasibility_recommendations(
        self,
        feasibility_level: str,
        limiting_factors: List[str]
    ) -> List[str]:
        """Get recommendations based on feasibility assessment"""
        recommendations = []
        
        if feasibility_level == "low":
            recommendations.append("Consider alternative development approaches")
            recommendations.append("Evaluate potential for obstacle mitigation")
            recommendations.append("Consult with environmental and planning professionals")
        
        elif feasibility_level == "medium":
            recommendations.append("Focus development on largest contiguous areas")
            recommendations.append("Plan mitigation strategies for major obstacles")
        
        else:  # high feasibility
            recommendations.append("Proceed with detailed development planning")
            recommendations.append("Optimize layout to maximize developable area")
        
        # Specific recommendations for limiting factors
        for factor in limiting_factors:
            if "Limited developable area" in factor:
                recommendations.append("Consider compact or multi-story development")
            elif "Insufficient contiguous space" in factor:
                recommendations.append("Evaluate options for obstacle removal or relocation")
            elif "High obstacle density" in factor:
                recommendations.append("Prioritize obstacle mitigation efforts")
            elif "fragmented" in factor:
                recommendations.append("Consider phased development approach")
        
        return recommendations
    
    def _generate_obstacle_recommendations(
        self,
        obstacle_inventory: Dict[str, List[Dict[str, Any]]],
        developable_area: Dict[str, Any],
        conflict_analysis: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Generate general recommendations for obstacle management"""
        recommendations = []
        
        total_obstacles = sum(len(obstacles) for obstacles in obstacle_inventory.values())
        
        if total_obstacles == 0:
            recommendations.append("No significant obstacles detected - proceed with development planning")
        else:
            recommendations.append(f"Identified {total_obstacles} potential obstacles requiring evaluation")
        
        if developable_area.get("percentage_of_parcel", 0) < 50:
            recommendations.append("Limited developable area - consider obstacle mitigation strategies")
        
        if conflict_analysis and conflict_analysis.get("conflict_detected"):
            high_conflicts = len(conflict_analysis.get("by_severity", {}).get("high", []))
            if high_conflicts > 0:
                recommendations.append(f"Address {high_conflicts} high-severity conflicts before proceeding")
        
        # Category-specific recommendations
        if obstacle_inventory.get("regulatory"):
            recommendations.append("Verify regulatory compliance requirements with local authorities")
        
        if obstacle_inventory.get("natural"):
            recommendations.append("Consider environmental impact mitigation measures")
        
        if obstacle_inventory.get("infrastructure"):
            recommendations.append("Coordinate with utility companies for infrastructure modifications")
        
        recommendations.append("Conduct detailed site survey to verify obstacle locations and characteristics")
        recommendations.append("Consult with qualified professionals for obstacle-specific mitigation strategies")
        
        return recommendations