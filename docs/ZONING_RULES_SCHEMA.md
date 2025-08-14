# Zoning Rules JSON Schema

## Overview
This document defines the JSON schema used for storing parsed zoning rules in the `zoning_rules.rules_jsonb` column.

## Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["code", "name", "category"],
  "properties": {
    "code": {
      "type": "string",
      "description": "Zoning code (e.g., R1, R2, C1)"
    },
    "name": {
      "type": "string",
      "description": "Human-readable name"
    },
    "category": {
      "type": "string",
      "enum": ["residential", "commercial", "industrial", "mixed", "agricultural", "special"],
      "description": "Primary use category"
    },
    "setbacks": {
      "type": "object",
      "properties": {
        "front": {"type": "number", "minimum": 0},
        "rear": {"type": "number", "minimum": 0},
        "side": {"type": "number", "minimum": 0},
        "street_side": {"type": "number", "minimum": 0}
      },
      "description": "Required setbacks in feet"
    },
    "coverage": {
      "type": "object",
      "properties": {
        "lot_coverage_max": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "Maximum lot coverage ratio (0-1)"
        },
        "far_max": {
          "type": "number",
          "minimum": 0,
          "description": "Maximum floor area ratio"
        },
        "impervious_max": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "Maximum impervious surface ratio"
        }
      }
    },
    "density": {
      "type": "object",
      "properties": {
        "units_per_acre_max": {"type": "number", "minimum": 0},
        "dwelling_units_max": {"type": "integer", "minimum": 0},
        "lot_size_min": {"type": "number", "minimum": 0},
        "lot_width_min": {"type": "number", "minimum": 0}
      }
    },
    "height": {
      "type": "object",
      "properties": {
        "max_feet": {"type": "number", "minimum": 0},
        "max_stories": {"type": "integer", "minimum": 0},
        "exceptions": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    },
    "adu": {
      "type": "object",
      "properties": {
        "allowed": {"type": "boolean"},
        "max_size_sqft": {"type": "number", "minimum": 0},
        "max_height_feet": {"type": "number", "minimum": 0},
        "parking_required": {"type": "integer", "minimum": 0},
        "owner_occupancy_required": {"type": "boolean"}
      },
      "description": "Accessory Dwelling Unit regulations"
    },
    "parking": {
      "type": "object",
      "properties": {
        "residential_per_unit": {"type": "number", "minimum": 0},
        "guest_per_units": {"type": "number", "minimum": 0},
        "commercial_per_sqft": {"type": "number", "minimum": 0}
      }
    },
    "allowed_uses": {
      "type": "array",
      "items": {"type": "string"},
      "description": "List of permitted uses"
    },
    "conditional_uses": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Uses requiring special permits"
    },
    "prohibited_uses": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Explicitly prohibited uses"
    },
    "special_provisions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "provision": {"type": "string"},
          "description": {"type": "string"},
          "conditions": {"type": "array", "items": {"type": "string"}}
        }
      }
    },
    "source": {
      "type": "object",
      "properties": {
        "document": {"type": "string"},
        "section": {"type": "string"},
        "url": {"type": "string", "format": "uri"},
        "effective_date": {"type": "string", "format": "date"},
        "parsed_date": {"type": "string", "format": "date-time"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
      }
    }
  }
}
```

## Example Instance

```json
{
  "code": "R1",
  "name": "Single-Family Residential",
  "category": "residential",
  "setbacks": {
    "front": 25,
    "rear": 10,
    "side": 5,
    "street_side": 10
  },
  "coverage": {
    "lot_coverage_max": 0.4,
    "far_max": 0.5,
    "impervious_max": 0.6
  },
  "density": {
    "units_per_acre_max": 4,
    "dwelling_units_max": 1,
    "lot_size_min": 7500,
    "lot_width_min": 60
  },
  "height": {
    "max_feet": 30,
    "max_stories": 2,
    "exceptions": ["chimney", "antenna"]
  },
  "adu": {
    "allowed": true,
    "max_size_sqft": 1200,
    "max_height_feet": 16,
    "parking_required": 0,
    "owner_occupancy_required": false
  },
  "parking": {
    "residential_per_unit": 2,
    "guest_per_units": 0.25
  },
  "allowed_uses": [
    "single_family_dwelling",
    "home_office",
    "accessory_dwelling_unit"
  ],
  "conditional_uses": [
    "daycare_facility",
    "group_home"
  ],
  "source": {
    "document": "Los Angeles Municipal Code",
    "section": "12.08",
    "url": "https://codelibrary.amlegal.com/codes/los_angeles",
    "effective_date": "2023-01-01",
    "parsed_date": "2024-01-15T10:30:00Z",
    "confidence": 0.95
  }
}
```

## Usage Notes

1. **Parsing Strategy**: Rules are parsed once per unique zoning code and cached
2. **LLM Integration**: When structured data unavailable, LLM extracts from text
3. **Confidence Scoring**: 0-1 scale indicating parsing reliability
4. **Updates**: Re-parse when source document changes
5. **Validation**: Use JSON Schema validation before storage