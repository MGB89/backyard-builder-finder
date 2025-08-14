"""
Fit test service for evaluating building placement and optimization
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from shapely.geometry import Polygon, Point, LineString
from shapely.affinity import translate, rotate, scale
from shapely.ops import unary_union
import numpy as np
from itertools import product

logger = logging.getLogger(__name__)


class FitTestService:
    """Service for testing building fit and optimizing placement on parcels"""
    
    def __init__(self):
        self.default_building_types = {
            "single_family": {"width": 30, "depth": 40, "area": 1200},
            "duplex": {"width": 40, "depth": 50, "area": 2000},
            "fourplex": {"width": 50, "depth": 60, "area": 3000},
            "apartment": {"width": 60, "depth": 80, "area": 4800},
            "commercial": {"width": 80, "depth": 100, "area": 8000}
        }
        
        self.placement_strategies = [
            "center_parcel", "front_setback", "rear_setback",
            "side_setback", "corner_placement", "maximize_yard"
        ]
    
    def test_building_fit(
        self,
        parcel_geometry: Dict[str, Any],
        building_specifications: Dict[str, Any],
        setback_requirements: Dict[str, float],
        existing_buildings: Optional[List[Dict[str, Any]]] = None,
        optimization_goals: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Test building fit and find optimal placement
        
        Args:
            parcel_geometry: Parcel boundary geometry
            building_specifications: Building dimensions and requirements
            setback_requirements: Required setbacks
            existing_buildings: Existing building geometries (optional)
            optimization_goals: Optimization objectives (optional)
            
        Returns:
            Dict[str, Any]: Fit test results and optimal placements
        """
        try:
            # Convert parcel geometry
            parcel_polygon = self._create_polygon_from_geometry(parcel_geometry)
            
            if not parcel_polygon or not parcel_polygon.is_valid:
                return {
                    "success": False,
                    "error": "Invalid parcel geometry"
                }
            
            # Process existing buildings
            existing_polygons = []
            if existing_buildings:
                for building in existing_buildings:
                    building_polygon = self._create_polygon_from_geometry(building.get("geometry", {}))
                    if building_polygon and building_polygon.is_valid:
                        existing_polygons.append(building_polygon)
            
            # Calculate buildable area
            buildable_area = self._calculate_buildable_area(
                parcel_polygon,
                setback_requirements,
                existing_polygons
            )
            
            # Create building footprint from specifications
            building_footprint = self._create_building_footprint(building_specifications)
            
            if not building_footprint:
                return {
                    "success": False,
                    "error": "Could not create building footprint from specifications"
                }
            
            # Test if building fits at all
            basic_fit_test = self._test_basic_fit(building_footprint, buildable_area)
            
            if not basic_fit_test["fits"]:
                return {
                    "success": True,
                    "fits": False,
                    "basic_fit_test": basic_fit_test,
                    "buildable_area": {
                        "geometry": self._polygon_to_dict(buildable_area),
                        "area_sqft": buildable_area.area
                    },
                    "recommendations": self._generate_fit_recommendations(
                        basic_fit_test, building_specifications, buildable_area
                    )
                }
            
            # Find optimal placements
            placement_results = self._find_optimal_placements(
                building_footprint,
                buildable_area,
                parcel_polygon,
                existing_polygons,
                optimization_goals or ["maximize_yard"]
            )
            
            # Evaluate each placement
            evaluated_placements = self._evaluate_placements(
                placement_results,
                parcel_polygon,
                setback_requirements,
                existing_polygons,
                optimization_goals
            )
            
            # Select best placement
            best_placement = max(
                evaluated_placements,
                key=lambda p: p["overall_score"]
            ) if evaluated_placements else None
            
            return {
                "success": True,
                "fits": True,
                "building_specifications": building_specifications,
                "buildable_area": {
                    "geometry": self._polygon_to_dict(buildable_area),
                    "area_sqft": buildable_area.area
                },
                "placement_options": evaluated_placements,
                "recommended_placement": best_placement,
                "placement_count": len(evaluated_placements),
                "optimization_summary": self._generate_optimization_summary(evaluated_placements),
                "recommendations": self._generate_placement_recommendations(
                    best_placement, evaluated_placements
                )
            }
        
        except Exception as e:
            logger.error(f"Fit test error: {str(e)}")
            return {
                "success": False,
                "error": f"Fit test failed: {str(e)}"
            }
    
    def test_multiple_buildings(
        self,
        parcel_geometry: Dict[str, Any],
        building_list: List[Dict[str, Any]],
        setback_requirements: Dict[str, float],
        spacing_requirements: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Test fit for multiple buildings on a single parcel
        
        Args:
            parcel_geometry: Parcel boundary geometry
            building_list: List of building specifications
            setback_requirements: Required setbacks
            spacing_requirements: Required spacing between buildings
            
        Returns:
            Dict[str, Any]: Multi-building fit test results
        """
        try:
            parcel_polygon = self._create_polygon_from_geometry(parcel_geometry)
            
            if not parcel_polygon or not parcel_polygon.is_valid:
                return {
                    "success": False,
                    "error": "Invalid parcel geometry"
                }
            
            # Calculate buildable area
            buildable_area = self._calculate_buildable_area(
                parcel_polygon,
                setback_requirements,
                []
            )
            
            # Create building footprints
            building_footprints = []
            for i, building_spec in enumerate(building_list):
                footprint = self._create_building_footprint(building_spec)
                if footprint:
                    building_footprints.append({
                        "id": f"building_{i}",
                        "footprint": footprint,
                        "specifications": building_spec
                    })
            
            if not building_footprints:
                return {
                    "success": False,
                    "error": "No valid building footprints created"
                }
            
            # Test combinations of placements
            placement_combinations = self._find_multi_building_placements(
                building_footprints,
                buildable_area,
                spacing_requirements or {"min_distance": 10}
            )
            
            # Evaluate each combination
            evaluated_combinations = []
            for combination in placement_combinations:
                evaluation = self._evaluate_multi_building_placement(
                    combination,
                    buildable_area,
                    parcel_polygon,
                    spacing_requirements
                )
                evaluated_combinations.append(evaluation)
            
            # Select best combination
            best_combination = max(
                evaluated_combinations,
                key=lambda c: c["overall_score"]
            ) if evaluated_combinations else None
            
            return {
                "success": True,
                "building_count": len(building_list),
                "buildable_area_sqft": self._convert_area_to_sqft(buildable_area.area),
                "placement_combinations": evaluated_combinations,
                "recommended_combination": best_combination,
                "fits_all_buildings": best_combination is not None,
                "total_building_area_sqft": sum(
                    building["specifications"].get("area", 0) for building in building_footprints
                ) if best_combination else 0
            }
        
        except Exception as e:
            logger.error(f"Multi-building fit test error: {str(e)}")
            return {
                "success": False,
                "error": f"Multi-building fit test failed: {str(e)}"
            }
    
    def optimize_building_size(
        self,
        parcel_geometry: Dict[str, Any],
        setback_requirements: Dict[str, float],
        max_coverage_ratio: float = 0.4,
        min_building_area: float = 800,
        existing_buildings: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Optimize building size to maximize area within constraints
        
        Args:
            parcel_geometry: Parcel boundary geometry
            setback_requirements: Required setbacks
            max_coverage_ratio: Maximum lot coverage ratio
            min_building_area: Minimum building area
            existing_buildings: Existing buildings (optional)
            
        Returns:
            Dict[str, Any]: Optimized building size results
        """
        try:
            parcel_polygon = self._create_polygon_from_geometry(parcel_geometry)
            
            if not parcel_polygon or not parcel_polygon.is_valid:
                return {
                    "success": False,
                    "error": "Invalid parcel geometry"
                }
            
            # Process existing buildings
            existing_polygons = []
            existing_area = 0
            if existing_buildings:
                for building in existing_buildings:
                    building_polygon = self._create_polygon_from_geometry(building.get("geometry", {}))
                    if building_polygon and building_polygon.is_valid:
                        existing_polygons.append(building_polygon)
                        existing_area += building_polygon.area
            
            # Calculate buildable area
            buildable_area = self._calculate_buildable_area(
                parcel_polygon,
                setback_requirements,
                existing_polygons
            )
            
            # Calculate maximum allowable building area
            parcel_area = parcel_polygon.area
            max_total_building_area = parcel_area * max_coverage_ratio
            max_new_building_area = max_total_building_area - existing_area
            
            if max_new_building_area < min_building_area:
                return {
                    "success": True,
                    "optimized": False,
                    "reason": "Coverage limit prevents minimum building size",
                    "max_allowable_area_sqft": max_new_building_area,
                    "min_required_area_sqft": min_building_area,
                    "existing_coverage_sqft": existing_area,
                    "max_coverage_ratio": max_coverage_ratio
                }
            
            # Find optimal building dimensions
            optimal_dimensions = self._find_optimal_dimensions(
                buildable_area,
                min(max_new_building_area, buildable_area.area * 0.8)  # Leave some margin
            )
            
            if not optimal_dimensions:
                return {
                    "success": True,
                    "optimized": False,
                    "reason": "Cannot fit minimum building in buildable area",
                    "buildable_area_sqft": buildable_area.area,
                    "min_required_area_sqft": min_building_area
                }
            
            # Create optimized building footprint
            optimized_building = self._create_building_footprint({
                "width": optimal_dimensions["width"],
                "depth": optimal_dimensions["depth"],
                "area": optimal_dimensions["area"]
            })
            
            # Find best placement for optimized building
            placement_result = self._find_optimal_placements(
                optimized_building,
                buildable_area,
                parcel_polygon,
                existing_polygons,
                ["maximize_area"]
            )
            
            best_placement = None
            if placement_result:
                evaluated = self._evaluate_placements(
                    placement_result,
                    parcel_polygon,
                    setback_requirements,
                    existing_polygons,
                    ["maximize_area"]
                )
                best_placement = max(evaluated, key=lambda p: p["overall_score"]) if evaluated else None
            
            return {
                "success": True,
                "optimized": True,
                "parcel_area_sqft": parcel_area,
                "buildable_area_sqft": self._convert_area_to_sqft(buildable_area.area),
                "max_coverage_ratio": max_coverage_ratio,
                "existing_building_area_sqft": existing_area,
                "max_new_building_area_sqft": max_new_building_area,
                "optimized_dimensions": optimal_dimensions,
                "optimized_placement": best_placement,
                "coverage_utilization": (optimal_dimensions["area"] + existing_area) / parcel_area,
                "buildable_area_utilization": optimal_dimensions["area"] / self._convert_area_to_sqft(buildable_area.area) if buildable_area.area > 0 else 0
            }
        
        except Exception as e:
            logger.error(f"Building optimization error: {str(e)}")
            return {
                "success": False,
                "error": f"Building optimization failed: {str(e)}"
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
    
    def _calculate_buildable_area(
        self,
        parcel: Polygon,
        setbacks: Dict[str, float],
        existing_buildings: List[Polygon]
    ) -> Polygon:
        """Calculate buildable area considering setbacks and existing buildings"""
        try:
            # Apply setbacks (simplified - uniform buffer)
            max_setback = max(setbacks.values()) if setbacks else 25
            buildable_area = parcel.buffer(-max_setback / 3.28084)  # Convert feet to meters
            
            # Remove existing buildings
            if existing_buildings:
                existing_union = unary_union(existing_buildings)
                buildable_area = buildable_area.difference(existing_union)
            
            # Ensure valid geometry
            if not buildable_area.is_valid:
                buildable_area = buildable_area.buffer(0)
            
            return buildable_area if buildable_area.is_valid else Polygon()
        
        except Exception as e:
            logger.error(f"Error calculating buildable area: {str(e)}")
            return Polygon()
    
    def _create_building_footprint(self, specifications: Dict[str, Any]) -> Optional[Polygon]:
        """Create building footprint from specifications"""
        try:
            width = specifications.get("width")
            depth = specifications.get("depth")
            area = specifications.get("area")
            
            # If width and depth provided, use them
            if width and depth:
                return self._create_rectangular_footprint(width, depth)
            
            # If only area provided, create square
            elif area:
                side_length = np.sqrt(area)
                return self._create_rectangular_footprint(side_length, side_length)
            
            # Use building type defaults
            building_type = specifications.get("type", "single_family")
            if building_type in self.default_building_types:
                defaults = self.default_building_types[building_type]
                return self._create_rectangular_footprint(defaults["width"], defaults["depth"])
            
            return None
        
        except Exception as e:
            logger.error(f"Error creating building footprint: {str(e)}")
            return None
    
    def _create_rectangular_footprint(self, width: float, depth: float) -> Polygon:
        """Create rectangular building footprint"""
        # Create rectangle centered at origin
        coords = [
            (-width/2, -depth/2),
            (width/2, -depth/2),
            (width/2, depth/2),
            (-width/2, depth/2),
            (-width/2, -depth/2)
        ]
        return Polygon(coords)
    
    def _test_basic_fit(self, building: Polygon, buildable_area: Polygon) -> Dict[str, Any]:
        """Test if building can fit in buildable area"""
        try:
            building_area = building.area
            buildable_area_value = buildable_area.area
            
            # Test if building area fits
            area_fits = building_area <= buildable_area_value
            
            # Test if building geometry fits
            geometry_fits = False
            if area_fits and not buildable_area.is_empty:
                # Try placing building at centroid
                centroid = buildable_area.centroid
                positioned_building = translate(building, centroid.x, centroid.y)
                geometry_fits = buildable_area.contains(positioned_building)
            
            return {
                "fits": area_fits and geometry_fits,
                "area_fits": area_fits,
                "geometry_fits": geometry_fits,
                "building_area_sqft": building_area,
                "buildable_area_sqft": buildable_area_value,
                "area_utilization": building_area / buildable_area_value if buildable_area_value > 0 else 0
            }
        
        except Exception as e:
            logger.error(f"Error in basic fit test: {str(e)}")
            return {
                "fits": False,
                "error": str(e)
            }
    
    def _find_optimal_placements(
        self,
        building: Polygon,
        buildable_area: Polygon,
        parcel: Polygon,
        existing_buildings: List[Polygon],
        optimization_goals: List[str]
    ) -> List[Dict[str, Any]]:
        """Find optimal building placements"""
        try:
            placements = []
            
            if buildable_area.is_empty:
                return placements
            
            # Get buildable area bounds
            bounds = buildable_area.bounds
            
            # Generate placement grid
            grid_spacing = 10  # 10-foot grid
            x_positions = np.arange(bounds[0], bounds[2], grid_spacing)
            y_positions = np.arange(bounds[1], bounds[3], grid_spacing)
            
            # Test each position
            for x, y in product(x_positions, y_positions):
                test_position = Point(x, y)
                
                # Check if position is within buildable area
                if not buildable_area.contains(test_position):
                    continue
                
                # Position building at this point
                positioned_building = translate(building, x, y)
                
                # Check if building fits completely in buildable area
                if buildable_area.contains(positioned_building):
                    # Check clearance from existing buildings
                    min_clearance = float('inf')
                    for existing in existing_buildings:
                        clearance = positioned_building.distance(existing)
                        min_clearance = min(min_clearance, clearance)
                    
                    placement = {
                        "position": {"x": x, "y": y},
                        "geometry": self._polygon_to_dict(positioned_building),
                        "building_area_sqft": positioned_building.area,
                        "min_clearance_ft": min_clearance if existing_buildings else None,
                        "distance_to_parcel_center": test_position.distance(parcel.centroid)
                    }
                    
                    placements.append(placement)
            
            return placements
        
        except Exception as e:
            logger.error(f"Error finding optimal placements: {str(e)}")
            return []
    
    def _evaluate_placements(
        self,
        placements: List[Dict[str, Any]],
        parcel: Polygon,
        setbacks: Dict[str, float],
        existing_buildings: List[Polygon],
        optimization_goals: List[str]
    ) -> List[Dict[str, Any]]:
        """Evaluate and score building placements"""
        evaluated = []
        
        for placement in placements:
            building_geom = self._create_polygon_from_geometry(placement["geometry"])
            
            if not building_geom:
                continue
            
            scores = {}
            
            # Calculate various metrics
            if "maximize_yard" in optimization_goals:
                scores["yard_space"] = self._calculate_yard_space_score(building_geom, parcel)
            
            if "minimize_setback_variance" in optimization_goals:
                scores["setback_compliance"] = self._calculate_setback_score(building_geom, parcel, setbacks)
            
            if "maximize_privacy" in optimization_goals:
                scores["privacy"] = self._calculate_privacy_score(building_geom, parcel, existing_buildings)
            
            if "center_placement" in optimization_goals:
                scores["centrality"] = self._calculate_centrality_score(building_geom, parcel)
            
            if "maximize_area" in optimization_goals:
                scores["area_utilization"] = placement["building_area_sqft"] / parcel.area
            
            # Calculate overall score
            overall_score = np.mean(list(scores.values())) if scores else 0
            
            evaluated_placement = placement.copy()
            evaluated_placement.update({
                "scores": scores,
                "overall_score": overall_score,
                "ranking_factors": optimization_goals
            })
            
            evaluated.append(evaluated_placement)
        
        # Sort by overall score
        return sorted(evaluated, key=lambda p: p["overall_score"], reverse=True)
    
    def _find_multi_building_placements(
        self,
        buildings: List[Dict[str, Any]],
        buildable_area: Polygon,
        spacing_requirements: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Find valid placements for multiple buildings"""
        # Simplified implementation - would need more sophisticated algorithm for real use
        combinations = []
        
        if len(buildings) <= 2:  # Only handle simple cases for now
            min_spacing = spacing_requirements.get("min_distance", 10)
            
            # Try different arrangements
            for building1 in buildings:
                for building2 in buildings[1:]:
                    if building1 == building2:
                        continue
                    
                    # Try side-by-side placement
                    footprint1 = building1["footprint"]
                    footprint2 = building2["footprint"]
                    
                    # Simple placement: second building to the right of first
                    bounds1 = footprint1.bounds
                    offset_x = bounds1[2] + min_spacing + footprint2.bounds[2] - footprint2.bounds[0]
                    
                    positioned1 = translate(footprint1, 0, 0)  # Keep at origin
                    positioned2 = translate(footprint2, offset_x, 0)
                    
                    # Check if both fit in buildable area
                    if (buildable_area.contains(positioned1) and 
                        buildable_area.contains(positioned2)):
                        
                        combination = {
                            "buildings": [
                                {
                                    "id": building1["id"],
                                    "geometry": self._polygon_to_dict(positioned1),
                                    "specifications": building1["specifications"]
                                },
                                {
                                    "id": building2["id"],
                                    "geometry": self._polygon_to_dict(positioned2),
                                    "specifications": building2["specifications"]
                                }
                            ],
                            "total_area_sqft": positioned1.area + positioned2.area,
                            "spacing_maintained": True
                        }
                        combinations.append(combination)
        
        return combinations
    
    def _evaluate_multi_building_placement(
        self,
        combination: Dict[str, Any],
        buildable_area: Polygon,
        parcel: Polygon,
        spacing_requirements: Optional[Dict[str, float]]
    ) -> Dict[str, Any]:
        """Evaluate multi-building placement combination"""
        try:
            total_area = combination["total_area_sqft"]
            building_count = len(combination["buildings"])
            
            # Calculate efficiency score
            efficiency_score = total_area / buildable_area.area if buildable_area.area > 0 else 0
            
            # Calculate layout score (simplified)
            layout_score = 1.0 / building_count  # Prefer fewer buildings for simplicity
            
            # Overall score
            overall_score = (efficiency_score + layout_score) / 2
            
            evaluated = combination.copy()
            evaluated.update({
                "efficiency_score": efficiency_score,
                "layout_score": layout_score,
                "overall_score": overall_score,
                "coverage_ratio": total_area / parcel.area
            })
            
            return evaluated
        
        except Exception as e:
            logger.error(f"Error evaluating multi-building placement: {str(e)}")
            return combination
    
    def _find_optimal_dimensions(self, buildable_area: Polygon, target_area: float) -> Optional[Dict[str, Any]]:
        """Find optimal building dimensions for target area"""
        try:
            if buildable_area.is_empty or target_area <= 0:
                return None
            
            # Get buildable area bounds
            bounds = buildable_area.bounds
            max_width = bounds[2] - bounds[0]
            max_depth = bounds[3] - bounds[1]
            
            # Try different aspect ratios
            aspect_ratios = [0.5, 0.75, 1.0, 1.33, 2.0]
            best_fit = None
            best_score = 0
            
            for ratio in aspect_ratios:
                # Calculate dimensions for this ratio
                if ratio <= 1:  # Width <= Depth
                    width = np.sqrt(target_area * ratio)
                    depth = target_area / width
                else:  # Width > Depth
                    depth = np.sqrt(target_area / ratio)
                    width = target_area / depth
                
                # Check if dimensions fit in buildable area
                if width <= max_width and depth <= max_depth:
                    # Create test building
                    test_building = self._create_rectangular_footprint(width, depth)
                    centroid = buildable_area.centroid
                    positioned_building = translate(test_building, centroid.x, centroid.y)
                    
                    # Check if it fits
                    if buildable_area.contains(positioned_building):
                        # Score based on how well it uses the space
                        efficiency = target_area / buildable_area.area
                        shape_score = min(ratio, 1/ratio)  # Prefer more square shapes
                        total_score = efficiency * shape_score
                        
                        if total_score > best_score:
                            best_score = total_score
                            best_fit = {
                                "width": width,
                                "depth": depth,
                                "area": target_area,
                                "aspect_ratio": ratio,
                                "efficiency": efficiency,
                                "shape_score": shape_score,
                                "total_score": total_score
                            }
            
            return best_fit
        
        except Exception as e:
            logger.error(f"Error finding optimal dimensions: {str(e)}")
            return None
    
    def _calculate_yard_space_score(self, building: Polygon, parcel: Polygon) -> float:
        """Calculate score based on remaining yard space"""
        try:
            remaining_area = parcel.difference(building).area
            return min(1.0, remaining_area / (parcel.area * 0.6))  # Score based on 60% yard space ideal
        except:
            return 0.0
    
    def _calculate_setback_score(
        self,
        building: Polygon,
        parcel: Polygon,
        setbacks: Dict[str, float]
    ) -> float:
        """Calculate setback compliance score"""
        try:
            # Simplified - measure distance to parcel boundary
            distance = building.distance(parcel.boundary)
            required_setback = min(setbacks.values()) if setbacks else 25
            return min(1.0, distance / required_setback)
        except:
            return 0.0
    
    def _calculate_privacy_score(
        self,
        building: Polygon,
        parcel: Polygon,
        existing_buildings: List[Polygon]
    ) -> float:
        """Calculate privacy score based on distance from existing buildings"""
        try:
            if not existing_buildings:
                return 1.0
            
            min_distance = min(building.distance(existing) for existing in existing_buildings)
            return min(1.0, min_distance / 50)  # 50 feet for good privacy
        except:
            return 0.5
    
    def _calculate_centrality_score(self, building: Polygon, parcel: Polygon) -> float:
        """Calculate score based on how centered the building is"""
        try:
            building_centroid = building.centroid
            parcel_centroid = parcel.centroid
            distance = building_centroid.distance(parcel_centroid)
            max_distance = max(parcel.bounds[2] - parcel.bounds[0], parcel.bounds[3] - parcel.bounds[1]) / 2
            return max(0.0, 1.0 - (distance / max_distance))
        except:
            return 0.5
    
    def _generate_fit_recommendations(
        self,
        basic_fit_test: Dict[str, Any],
        building_specs: Dict[str, Any],
        buildable_area: Polygon
    ) -> List[str]:
        """Generate recommendations when building doesn't fit"""
        recommendations = []
        
        if not basic_fit_test.get("area_fits"):
            recommendations.append("Reduce building size to fit within buildable area")
            recommendations.append("Consider multi-story construction to maintain floor area")
        
        if not basic_fit_test.get("geometry_fits"):
            recommendations.append("Modify building shape to better fit buildable area")
            recommendations.append("Consider L-shaped or custom building design")
        
        buildable_area_sqft = buildable_area.area
        if buildable_area_sqft < 1000:
            recommendations.append("Very limited buildable area - consider setback variance")
        
        recommendations.append("Consult with architect for custom design solutions")
        
        return recommendations
    
    def _generate_placement_recommendations(
        self,
        best_placement: Optional[Dict[str, Any]],
        all_placements: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate placement recommendations"""
        recommendations = []
        
        if not best_placement:
            recommendations.append("No suitable placement found with current constraints")
            return recommendations
        
        score = best_placement.get("overall_score", 0)
        
        if score >= 0.8:
            recommendations.append("Excellent placement option identified")
        elif score >= 0.6:
            recommendations.append("Good placement option with minor trade-offs")
        else:
            recommendations.append("Placement possible but may require compromises")
        
        if len(all_placements) > 5:
            recommendations.append("Multiple placement options available for consideration")
        elif len(all_placements) == 1:
            recommendations.append("Limited placement options - consider design modifications")
        
        recommendations.append("Review placement with site planning professional")
        
        return recommendations
    
    def _generate_optimization_summary(self, placements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate optimization summary"""
        if not placements:
            return {"total_options": 0, "average_score": 0}
        
        scores = [p.get("overall_score", 0) for p in placements]
        
        return {
            "total_options": len(placements),
            "average_score": np.mean(scores),
            "best_score": max(scores),
            "score_range": max(scores) - min(scores),
            "high_quality_options": len([s for s in scores if s >= 0.7])
        }
    
    def _polygon_to_dict(self, polygon: Polygon) -> Optional[Dict[str, Any]]:
        """Convert Shapely polygon to dictionary format"""
        if polygon.is_empty:
            return None
        
        exterior_coords = list(polygon.exterior.coords)
        
        return {
            "type": "Polygon",
            "coordinates": [exterior_coords]
        }