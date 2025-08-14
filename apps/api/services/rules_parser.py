"""
Rules parser service for interpreting zoning and building codes
"""

from typing import Dict, Any, List, Optional, Union, Tuple
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class RulesParserService:
    """Service for parsing and interpreting zoning and building code rules"""
    
    def __init__(self):
        self.rule_patterns = {
            "setback": r"(?:setback|yard)\s+(?:shall be|must be|minimum|min\.?)\s+(?:at least\s+)?(\d+(?:\.\d+)?)\s*(?:feet|ft\.?|')",
            "height": r"(?:height|tall|story|stories)\s+(?:shall not exceed|maximum|max\.?|limit)\s+(\d+(?:\.\d+)?)\s*(?:feet|ft\.?|'|stories?)",
            "coverage": r"(?:coverage|cover)\s+(?:shall not exceed|maximum|max\.?)\s+(\d+(?:\.\d+)?)\s*(?:percent|%)",
            "far": r"(?:floor area ratio|FAR|f\.a\.r\.)\s+(?:shall not exceed|maximum|max\.?)\s+(\d+(?:\.\d+)?)",
            "density": r"(?:density|units)\s+(?:shall not exceed|maximum|max\.?)\s+(\d+(?:\.\d+)?)\s*(?:units?|dwelling units?)\s*(?:per acre|/acre)",
            "parking": r"(?:parking|spaces)\s+(?:shall|must|required?)\s+(?:provide|be)\s+(\d+(?:\.\d+)?)\s*(?:spaces?)\s*(?:per unit|per dwelling|/unit)",
            "use": r"(?:permitted uses?|allowed uses?|principal uses?)(?:\s*:)?\s*(.*?)(?:\.|;|$)",
            "conditional": r"(?:conditional uses?|special uses?)(?:\s*:)?\s*(.*?)(?:\.|;|$)",
            "prohibited": r"(?:prohibited uses?|forbidden uses?|not permitted)(?:\s*:)?\s*(.*?)(?:\.|;|$)"
        }
        
        self.unit_conversions = {
            "feet": 1.0,
            "ft": 1.0,
            "'": 1.0,
            "inches": 1.0/12,
            "in": 1.0/12,
            '"': 1.0/12,
            "yards": 3.0,
            "yd": 3.0,
            "meters": 3.28084,
            "m": 3.28084
        }
        
        self.common_uses = {
            "residential": [
                "single family", "duplex", "triplex", "fourplex", "apartment",
                "condominium", "townhouse", "mobile home", "manufactured home"
            ],
            "commercial": [
                "retail", "office", "restaurant", "hotel", "motel", "shopping center",
                "bank", "medical office", "professional service", "personal service"
            ],
            "industrial": [
                "manufacturing", "warehouse", "distribution", "assembly", "processing",
                "heavy industry", "light industry", "storage", "logistics"
            ],
            "institutional": [
                "school", "church", "hospital", "government", "library", "museum",
                "community center", "fire station", "police station"
            ]
        }
    
    def parse_zoning_text(self, zoning_text: str, zoning_code: str = None) -> Dict[str, Any]:
        """
        Parse zoning ordinance text and extract regulations
        
        Args:
            zoning_text: Raw zoning ordinance text
            zoning_code: Zoning district code (optional)
            
        Returns:
            Dict[str, Any]: Parsed zoning regulations
        """
        try:
            # Clean and normalize text
            cleaned_text = self._clean_text(zoning_text)
            
            # Parse different types of regulations
            parsed_rules = {}
            
            # Parse setback requirements
            setbacks = self._parse_setbacks(cleaned_text)
            if setbacks:
                parsed_rules["setbacks"] = setbacks
            
            # Parse height restrictions
            height = self._parse_height_restrictions(cleaned_text)
            if height:
                parsed_rules["height"] = height
            
            # Parse lot coverage
            coverage = self._parse_lot_coverage(cleaned_text)
            if coverage:
                parsed_rules["lot_coverage"] = coverage
            
            # Parse FAR requirements
            far = self._parse_far_requirements(cleaned_text)
            if far:
                parsed_rules["far"] = far
            
            # Parse density requirements
            density = self._parse_density_requirements(cleaned_text)
            if density:
                parsed_rules["density"] = density
            
            # Parse parking requirements
            parking = self._parse_parking_requirements(cleaned_text)
            if parking:
                parsed_rules["parking"] = parking
            
            # Parse use regulations
            uses = self._parse_use_regulations(cleaned_text)
            if uses:
                parsed_rules["uses"] = uses
            
            # Parse special requirements
            special = self._parse_special_requirements(cleaned_text)
            if special:
                parsed_rules["special_requirements"] = special
            
            return {
                "success": True,
                "zoning_code": zoning_code,
                "parsed_rules": parsed_rules,
                "source_text_length": len(zoning_text),
                "parsing_confidence": self._calculate_parsing_confidence(parsed_rules),
                "parsed_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error parsing zoning text: {str(e)}")
            return {
                "success": False,
                "error": f"Zoning text parsing failed: {str(e)}"
            }
    
    def interpret_building_codes(self, building_code_text: str) -> Dict[str, Any]:
        """
        Interpret building code requirements
        
        Args:
            building_code_text: Building code text
            
        Returns:
            Dict[str, Any]: Interpreted building requirements
        """
        try:
            cleaned_text = self._clean_text(building_code_text)
            
            interpreted_codes = {
                "structural": self._parse_structural_requirements(cleaned_text),
                "fire_safety": self._parse_fire_safety_requirements(cleaned_text),
                "accessibility": self._parse_accessibility_requirements(cleaned_text),
                "energy": self._parse_energy_requirements(cleaned_text),
                "plumbing": self._parse_plumbing_requirements(cleaned_text),
                "electrical": self._parse_electrical_requirements(cleaned_text)
            }
            
            # Remove empty sections
            interpreted_codes = {k: v for k, v in interpreted_codes.items() if v}
            
            return {
                "success": True,
                "interpreted_codes": interpreted_codes,
                "source_text_length": len(building_code_text),
                "interpretation_confidence": self._calculate_interpretation_confidence(interpreted_codes),
                "interpreted_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error interpreting building codes: {str(e)}")
            return {
                "success": False,
                "error": f"Building code interpretation failed: {str(e)}"
            }
    
    def validate_rule_consistency(self, rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate consistency between different rules
        
        Args:
            rules: Parsed rules dictionary
            
        Returns:
            Dict[str, Any]: Validation results
        """
        try:
            inconsistencies = []
            warnings = []
            
            # Check for logical inconsistencies
            setbacks = rules.get("setbacks", {})
            height = rules.get("height", {})
            coverage = rules.get("lot_coverage", {})
            density = rules.get("density", {})
            
            # Validate setback reasonableness
            if setbacks:
                total_setbacks = sum(setbacks.values())
                if total_setbacks > 200:  # Very large combined setbacks
                    warnings.append("Combined setbacks are unusually large and may severely limit buildable area")
            
            # Validate height vs. stories consistency
            if height:
                max_height = height.get("max_height_ft")
                max_stories = height.get("max_stories")
                
                if max_height and max_stories:
                    avg_story_height = max_height / max_stories
                    if avg_story_height < 8:
                        inconsistencies.append("Maximum height insufficient for specified number of stories")
                    elif avg_story_height > 20:
                        warnings.append("Very tall story heights may indicate interpretation error")
            
            # Validate coverage vs. FAR consistency
            far_data = rules.get("far", {})
            if coverage and far_data:
                max_coverage = coverage.get("max_coverage_percent", 0) / 100
                max_far = far_data.get("max_far", 0)
                
                if max_far > max_coverage:
                    # FAR allows more floor area than lot coverage permits with single story
                    min_stories_needed = max_far / max_coverage if max_coverage > 0 else float('inf')
                    if min_stories_needed > height.get("max_stories", 1):
                        inconsistencies.append("FAR and lot coverage requirements conflict with height restrictions")
            
            # Validate density vs. lot coverage
            if density and coverage:
                max_density = density.get("max_density_units_acre", 0)
                max_coverage = coverage.get("max_coverage_percent", 0)
                
                # Rough check: high density with low coverage may be problematic
                if max_density > 20 and max_coverage < 30:
                    warnings.append("High density with low lot coverage may be challenging to achieve")
            
            return {
                "success": True,
                "is_consistent": len(inconsistencies) == 0,
                "inconsistencies": inconsistencies,
                "warnings": warnings,
                "validation_score": self._calculate_validation_score(inconsistencies, warnings)
            }
        
        except Exception as e:
            logger.error(f"Error validating rule consistency: {str(e)}")
            return {
                "success": False,
                "error": f"Rule validation failed: {str(e)}"
            }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for parsing"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might interfere with parsing
        text = re.sub(r'[^\w\s\.\,\;\:\(\)\-\%\'\"/]', '', text)
        
        # Normalize common abbreviations
        text = re.sub(r'\bft\.?\b', 'feet', text, flags=re.IGNORECASE)
        text = re.sub(r'\bsq\.?\s*ft\.?\b', 'square feet', text, flags=re.IGNORECASE)
        text = re.sub(r'\bmax\.?\b', 'maximum', text, flags=re.IGNORECASE)
        text = re.sub(r'\bmin\.?\b', 'minimum', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def _parse_setbacks(self, text: str) -> Optional[Dict[str, float]]:
        """Parse setback requirements from text"""
        setbacks = {}
        
        # Look for specific setback directions
        setback_types = {
            "front": r"front\s+(?:yard\s+)?setback",
            "rear": r"rear\s+(?:yard\s+)?setback",
            "side": r"side\s+(?:yard\s+)?setback",
            "street_side": r"street\s+side\s+(?:yard\s+)?setback"
        }
        
        for setback_type, pattern in setback_types.items():
            # Look for setback with specific direction
            full_pattern = pattern + r"[:\s]+(?:shall be|must be|minimum|min\.?)\s+(?:at least\s+)?(\d+(?:\.\d+)?)\s*(?:feet|ft\.?|')"
            matches = re.finditer(full_pattern, text, re.IGNORECASE)
            
            for match in matches:
                distance = float(match.group(1))
                setbacks[setback_type] = distance
        
        # Look for general setback requirements
        general_pattern = self.rule_patterns["setback"]
        matches = re.finditer(general_pattern, text, re.IGNORECASE)
        
        for match in matches:
            distance = float(match.group(1))
            if not setbacks:  # If no specific setbacks found, use as general
                setbacks["general"] = distance
        
        return setbacks if setbacks else None
    
    def _parse_height_restrictions(self, text: str) -> Optional[Dict[str, Union[float, int]]]:
        """Parse height restrictions from text"""
        height_info = {}
        
        # Parse maximum height in feet
        height_pattern = r"(?:building\s+)?height\s+(?:shall not exceed|maximum|max\.?|limit(?:ed to)?)\s+(\d+(?:\.\d+)?)\s*(?:feet|ft\.?|')"
        matches = re.finditer(height_pattern, text, re.IGNORECASE)
        
        for match in matches:
            height_info["max_height_ft"] = float(match.group(1))
        
        # Parse maximum stories
        stories_pattern = r"(?:building\s+)?(?:shall not exceed|maximum|max\.?|limit(?:ed to)?)\s+(\d+)\s*(?:stories?|story)"
        matches = re.finditer(stories_pattern, text, re.IGNORECASE)
        
        for match in matches:
            height_info["max_stories"] = int(match.group(1))
        
        return height_info if height_info else None
    
    def _parse_lot_coverage(self, text: str) -> Optional[Dict[str, float]]:
        """Parse lot coverage requirements from text"""
        coverage_pattern = self.rule_patterns["coverage"]
        matches = re.finditer(coverage_pattern, text, re.IGNORECASE)
        
        for match in matches:
            coverage_percent = float(match.group(1))
            return {"max_coverage_percent": coverage_percent}
        
        return None
    
    def _parse_far_requirements(self, text: str) -> Optional[Dict[str, float]]:
        """Parse Floor Area Ratio requirements from text"""
        far_pattern = self.rule_patterns["far"]
        matches = re.finditer(far_pattern, text, re.IGNORECASE)
        
        for match in matches:
            far_value = float(match.group(1))
            return {"max_far": far_value}
        
        return None
    
    def _parse_density_requirements(self, text: str) -> Optional[Dict[str, float]]:
        """Parse density requirements from text"""
        density_pattern = self.rule_patterns["density"]
        matches = re.finditer(density_pattern, text, re.IGNORECASE)
        
        for match in matches:
            density_value = float(match.group(1))
            return {"max_density_units_acre": density_value}
        
        return None
    
    def _parse_parking_requirements(self, text: str) -> Optional[Dict[str, Union[float, str]]]:
        """Parse parking requirements from text"""
        parking_info = {}
        
        # Parse spaces per unit
        parking_pattern = self.rule_patterns["parking"]
        matches = re.finditer(parking_pattern, text, re.IGNORECASE)
        
        for match in matches:
            spaces_per_unit = float(match.group(1))
            parking_info["spaces_per_unit"] = spaces_per_unit
        
        # Look for general parking requirements
        general_parking_pattern = r"parking\s+(?:shall|must|required?)\s+(?:provide|be)\s+(.*?)(?:\.|;|$)"
        matches = re.finditer(general_parking_pattern, text, re.IGNORECASE)
        
        for match in matches:
            requirement_text = match.group(1).strip()
            if requirement_text:
                parking_info["general_requirement"] = requirement_text
        
        return parking_info if parking_info else None
    
    def _parse_use_regulations(self, text: str) -> Optional[Dict[str, List[str]]]:
        """Parse use regulations from text"""
        uses = {}
        
        # Parse permitted uses
        permitted_pattern = self.rule_patterns["use"]
        matches = re.finditer(permitted_pattern, text, re.IGNORECASE)
        
        for match in matches:
            use_text = match.group(1).strip()
            permitted_uses = self._extract_use_list(use_text)
            if permitted_uses:
                uses["permitted"] = permitted_uses
        
        # Parse conditional uses
        conditional_pattern = self.rule_patterns["conditional"]
        matches = re.finditer(conditional_pattern, text, re.IGNORECASE)
        
        for match in matches:
            use_text = match.group(1).strip()
            conditional_uses = self._extract_use_list(use_text)
            if conditional_uses:
                uses["conditional"] = conditional_uses
        
        # Parse prohibited uses
        prohibited_pattern = self.rule_patterns["prohibited"]
        matches = re.finditer(prohibited_pattern, text, re.IGNORECASE)
        
        for match in matches:
            use_text = match.group(1).strip()
            prohibited_uses = self._extract_use_list(use_text)
            if prohibited_uses:
                uses["prohibited"] = prohibited_uses
        
        return uses if uses else None
    
    def _parse_special_requirements(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse special requirements from text"""
        special = {}
        
        # Look for landscaping requirements
        landscape_patterns = [
            r"landscaping\s+(?:shall|must|required?)\s+(.*?)(?:\.|;|$)",
            r"(?:green space|open space)\s+(?:shall|must|required?)\s+(.*?)(?:\.|;|$)"
        ]
        
        for pattern in landscape_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                special["landscaping"] = match.group(1).strip()
                break
        
        # Look for environmental requirements
        env_patterns = [
            r"environmental\s+(?:protection|review|assessment)\s+(.*?)(?:\.|;|$)",
            r"wetland\s+(?:protection|buffer)\s+(.*?)(?:\.|;|$)"
        ]
        
        for pattern in env_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                special["environmental"] = match.group(1).strip()
                break
        
        return special if special else None
    
    def _extract_use_list(self, use_text: str) -> List[str]:
        """Extract list of uses from text"""
        if not use_text:
            return []
        
        # Split by common delimiters
        uses = re.split(r'[,;]|\sand\s|\sor\s', use_text)
        
        # Clean up each use
        cleaned_uses = []
        for use in uses:
            cleaned_use = re.sub(r'^\W+|\W+$', '', use.strip())
            if cleaned_use and len(cleaned_use) > 2:
                cleaned_uses.append(cleaned_use.lower())
        
        return cleaned_uses
    
    def _parse_structural_requirements(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse structural requirements from building code"""
        # Placeholder implementation
        structural = {}
        
        # Look for load requirements
        load_pattern = r"(?:live load|dead load|wind load)\s+(?:shall|must|required?)\s+(\d+(?:\.\d+)?)\s*(?:psf|pounds per square foot)"
        matches = re.finditer(load_pattern, text, re.IGNORECASE)
        
        for match in matches:
            load_value = float(match.group(1))
            structural["load_requirements"] = f"{load_value} psf"
            break
        
        return structural if structural else None
    
    def _parse_fire_safety_requirements(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse fire safety requirements"""
        # Placeholder implementation
        fire_safety = {}
        
        # Look for sprinkler requirements
        if re.search(r"sprinkler\s+(?:system\s+)?(?:required|shall|must)", text, re.IGNORECASE):
            fire_safety["sprinkler_required"] = True
        
        return fire_safety if fire_safety else None
    
    def _parse_accessibility_requirements(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse accessibility requirements"""
        # Placeholder implementation
        accessibility = {}
        
        # Look for ADA compliance
        if re.search(r"ADA|americans with disabilities act|accessibility", text, re.IGNORECASE):
            accessibility["ada_compliance_required"] = True
        
        return accessibility if accessibility else None
    
    def _parse_energy_requirements(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse energy code requirements"""
        # Placeholder implementation
        energy = {}
        
        # Look for energy efficiency requirements
        if re.search(r"energy\s+(?:efficiency|code|star)", text, re.IGNORECASE):
            energy["energy_efficiency_required"] = True
        
        return energy if energy else None
    
    def _parse_plumbing_requirements(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse plumbing code requirements"""
        # Placeholder implementation
        return None
    
    def _parse_electrical_requirements(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse electrical code requirements"""
        # Placeholder implementation
        return None
    
    def _calculate_parsing_confidence(self, parsed_rules: Dict[str, Any]) -> float:
        """Calculate confidence score for parsing results"""
        if not parsed_rules:
            return 0.0
        
        # Basic confidence based on number of rules parsed
        rule_count = len(parsed_rules)
        base_confidence = min(0.8, rule_count * 0.15)
        
        # Boost confidence if common rules are found
        common_rules = ["setbacks", "height", "uses"]
        found_common = sum(1 for rule in common_rules if rule in parsed_rules)
        confidence_boost = found_common * 0.1
        
        return min(1.0, base_confidence + confidence_boost)
    
    def _calculate_interpretation_confidence(self, interpreted_codes: Dict[str, Any]) -> float:
        """Calculate confidence score for building code interpretation"""
        if not interpreted_codes:
            return 0.0
        
        return min(1.0, len(interpreted_codes) * 0.2)
    
    def _calculate_validation_score(self, inconsistencies: List[str], warnings: List[str]) -> float:
        """Calculate validation score based on consistency"""
        penalty = len(inconsistencies) * 0.3 + len(warnings) * 0.1
        return max(0.0, 1.0 - penalty)