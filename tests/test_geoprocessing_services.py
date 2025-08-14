"""
Test suite for geoprocessing services
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    import pytest
except ImportError:
    pytest = None

from apps.api.services.setbacks import SetbackAnalysisService
from apps.api.services.backyard import BackyardAnalysisService
from apps.api.services.obstacles import ObstacleAnalysisService
from apps.api.services.fit_test import FitTestService
from apps.api.services.zoning_eval import ZoningEvaluationService
from apps.api.services.rules_parser import RulesParserService


class TestGeoprocessingServices:
    """Test class for all geoprocessing services"""
    
    def setup_method(self):
        """Set up test data"""
        # Sample parcel geometry (WGS84 coordinates)
        self.sample_parcel = {
            "type": "Polygon",
            "coordinates": [[
                [-122.4194, 37.7749],  # San Francisco coordinates
                [-122.4194, 37.7739],
                [-122.4184, 37.7739],
                [-122.4184, 37.7749],
                [-122.4194, 37.7749]
            ]]
        }
        
        # Sample setback requirements
        self.sample_setbacks = {
            "front": 25.0,
            "rear": 20.0,
            "side": 10.0,
            "corner_side": 15.0
        }
        
        # Sample building
        self.sample_building = {
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-122.4192, 37.7747],
                    [-122.4192, 37.7742],
                    [-122.4187, 37.7742],
                    [-122.4187, 37.7747],
                    [-122.4192, 37.7747]
                ]]
            },
            "area": 1200
        }
        
        # Sample zoning district
        self.sample_zoning = {
            "code": "R-1",
            "max_density_units_acre": 8,
            "max_building_height_ft": 35,
            "max_lot_coverage": 40,
            "max_floor_area_ratio": 0.6,
            "min_building_setback_front_ft": 25,
            "min_building_setback_rear_ft": 20,
            "min_building_setback_side_ft": 10,
            "min_parking_spaces_per_unit": 2,
            "permitted_uses": ["single family dwelling", "accessory dwelling unit"],
            "conditional_uses": ["home occupation", "daycare"],
            "prohibited_uses": ["commercial", "industrial"]
        }
    
    def test_setback_analysis_service(self):
        """Test setback analysis service"""
        service = SetbackAnalysisService()
        
        result = service.analyze_setbacks(
            parcel_geometry=self.sample_parcel,
            zoning_setbacks=self.sample_setbacks,
            proposed_building=self.sample_building
        )
        
        assert result["success"] is True
        assert "buildable_area" in result
        assert "parcel_info" in result
        assert "setback_lines" in result
        assert result["buildable_area"]["area_sqft"] > 0
        print(f"✓ Setback Analysis: Buildable area = {result['buildable_area']['area_sqft']:.0f} sq ft")
    
    def test_backyard_analysis_service(self):
        """Test backyard analysis service"""
        service = BackyardAnalysisService()
        
        result = service.analyze_backyard(
            parcel_geometry=self.sample_parcel,
            building_footprints=[self.sample_building],
            zoning_requirements={"min_outdoor_space_sqft": 1000}
        )
        
        assert result["success"] is True
        assert "outdoor_areas" in result
        assert "backyard_areas" in result
        assert "usable_space" in result
        assert result["parcel_area_sqft"] > 0
        print(f"✓ Backyard Analysis: Total outdoor area = {result['outdoor_areas']['total_area_sqft']:.0f} sq ft")
    
    def test_obstacle_analysis_service(self):
        """Test obstacle analysis service"""
        service = ObstacleAnalysisService()
        
        # Sample obstacles
        obstacles = [
            {
                "id": "tree_1",
                "type": "trees",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-122.4191, 37.7746],
                        [-122.4191, 37.7744],
                        [-122.4189, 37.7744],
                        [-122.4189, 37.7746],
                        [-122.4191, 37.7746]
                    ]]
                },
                "severity": "medium",
                "removable": True
            }
        ]
        
        result = service.analyze_obstacles(
            parcel_geometry=self.sample_parcel,
            existing_features=obstacles,
            proposed_development=self.sample_building
        )
        
        assert result["success"] is True
        assert "obstacle_inventory" in result
        assert "constraint_zones" in result
        assert "developable_area" in result
        assert result["parcel_area_sqft"] > 0
        print(f"✓ Obstacle Analysis: Developable area = {result['developable_area']['total_area_sqft']:.0f} sq ft")
    
    def test_fit_test_service(self):
        """Test building fit test service"""
        service = FitTestService()
        
        building_specs = {
            "width": 30,
            "depth": 40,
            "area": 1200,
            "type": "single_family"
        }
        
        result = service.test_building_fit(
            parcel_geometry=self.sample_parcel,
            building_specifications=building_specs,
            setback_requirements=self.sample_setbacks
        )
        
        assert result["success"] is True
        if result["fits"]:
            assert "placement_options" in result
            assert "recommended_placement" in result
            print(f"✓ Fit Test: Building fits with {len(result['placement_options'])} placement options")
        else:
            assert "recommendations" in result
            print(f"✓ Fit Test: Building doesn't fit, {len(result['recommendations'])} recommendations provided")
    
    def test_zoning_evaluation_service(self):
        """Test zoning evaluation service"""
        service = ZoningEvaluationService()
        
        parcel_data = {
            "area_sqft": 8000,
            "geometry": self.sample_parcel
        }
        
        proposed_development = {
            "use_type": "single family dwelling",
            "units": 1,
            "height_ft": 28,
            "stories": 2,
            "building_area_sqft": 1200,
            "total_floor_area_sqft": 2400,
            "parking_spaces": 2,
            "landscaped_area_sqft": 1600
        }
        
        result = service.evaluate_zoning_compliance(
            parcel_data=parcel_data,
            zoning_district=self.sample_zoning,
            proposed_development=proposed_development
        )
        
        assert result["success"] is True
        assert "overall_compliant" in result
        assert "compliance_score" in result
        assert "compliance_details" in result
        print(f"✓ Zoning Evaluation: Compliance score = {result['compliance_score']:.2f}")
        
        # Test zoning summary
        summary = service.get_zoning_summary(self.sample_zoning)
        assert summary["success"] is True
        assert "development_potential" in summary
        print(f"✓ Zoning Summary: Restrictiveness score = {summary['restrictiveness_score']:.1f}")
    
    def test_rules_parser_service(self):
        """Test rules parser service"""
        service = RulesParserService()
        
        sample_zoning_text = """
        R-1 Single Family Residential District
        
        Purpose: To provide for single family residential development with 
        adequate light, air, and open space.
        
        Permitted Uses:
        - Single family dwellings
        - Accessory dwelling units
        - Home occupations (conditional)
        
        Dimensional Standards:
        - Maximum height: 35 feet or 2.5 stories
        - Minimum front setback: 25 feet
        - Minimum rear setback: 20 feet  
        - Minimum side setback: 10 feet
        - Maximum lot coverage: 40 percent
        - Maximum floor area ratio: 0.6
        - Minimum density: 4 units per acre
        - Maximum density: 8 units per acre
        """
        
        result = service.parse_zoning_text(sample_zoning_text, "R-1")
        
        assert result["success"] is True
        assert "parsed_rules" in result
        assert "parsing_confidence" in result
        
        parsed_rules = result["parsed_rules"]
        if "setbacks" in parsed_rules:
            print(f"✓ Rules Parser: Found setbacks = {parsed_rules['setbacks']}")
        if "height" in parsed_rules:
            print(f"✓ Rules Parser: Found height = {parsed_rules['height']}")
        if "uses" in parsed_rules:
            print(f"✓ Rules Parser: Found {len(parsed_rules['uses'])} use categories")
        
        print(f"✓ Rules Parser: Confidence = {result['parsing_confidence']:.2f}")
        
        # Test rule consistency validation
        if parsed_rules:
            validation = service.validate_rule_consistency(parsed_rules)
            assert validation["success"] is True
            print(f"✓ Rules Validation: Consistent = {validation['is_consistent']}")


if __name__ == "__main__":
    # Run tests directly
    test_instance = TestGeoprocessingServices()
    test_instance.setup_method()
    
    print("Running Geoprocessing Services Tests...")
    print("=" * 50)
    
    try:
        test_instance.test_setback_analysis_service()
        test_instance.test_backyard_analysis_service()
        test_instance.test_obstacle_analysis_service()
        test_instance.test_fit_test_service()
        test_instance.test_zoning_evaluation_service()
        test_instance.test_rules_parser_service()
        
        print("=" * 50)
        print("✅ All geoprocessing services tests passed!")
        
    except Exception as e:
        print("=" * 50)
        print(f"❌ Test failed: {str(e)}")
        raise