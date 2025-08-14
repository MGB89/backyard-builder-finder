"""ArcGIS parcel data connector for various regions."""
from typing import Dict, Any, List, Optional, Tuple
import logging
import asyncio
from datetime import datetime, timedelta
from shapely import wkb, wkt
from shapely.geometry import shape, Polygon, MultiPolygon
import json
import hashlib

from connectors.base import BaseConnector
from core.config import settings

logger = logging.getLogger(__name__)


class ArcGISParcelsConnector(BaseConnector):
    """Generic ArcGIS FeatureServer connector for parcel data."""
    
    # Region-specific endpoints (free/open data sources)
    ENDPOINTS = {
        "los-angeles": {
            "parcels": {
                "url": "https://maps.lacity.org/arcgis/rest/services/BETA/BaseMap_Labels_WM/MapServer/1",
                "name": "LA City Parcels",
                "id_field": "AIN",
                "area_field": "Shape__Area",
                "zoning_field": "UseType",
                "max_records": 1000
            },
            "zoning": {
                "url": "https://maps.lacity.org/arcgis/rest/services/BETA/BaseMap_Labels_WM/MapServer/0",
                "name": "LA City Zoning",
                "id_field": "OBJECTID",
                "zoning_field": "ZONE_CMPLT"
            },
            "county_parcels": {
                "url": "https://maps.lacity.org/arcgis/rest/services/Addressing/Parcels/MapServer/0",
                "name": "LA County Parcels",
                "id_field": "AIN",
                "area_field": "Shape_Area",
                "max_records": 2000
            }
        },
        "san-francisco": {
            "parcels": {
                "url": "https://services.arcgis.com/bkFwd6KaVFjLCRlE/ArcGIS/rest/services/Parcels/FeatureServer/0",
                "name": "San Francisco County",
                "id_field": "blklot",
                "area_field": "Shape__Area",
                "max_records": 1000
            }
        },
        "seattle": {
            "parcels": {
                "url": "https://services.arcgis.com/ZOyb2t4B0UWuU8wN/ArcGIS/rest/services/Parcels/FeatureServer/0",
                "name": "King County",
                "id_field": "PIN",
                "area_field": "Shape__Area",
                "max_records": 1000
            }
        }
    }
    
    def __init__(self, region: str = "los-angeles", layer: str = "parcels"):
        """Initialize connector for specific region and layer."""
        if region not in self.ENDPOINTS:
            raise ValueError(f"Unsupported region: {region}. Available: {list(self.ENDPOINTS.keys())}")
        
        if layer not in self.ENDPOINTS[region]:
            available_layers = list(self.ENDPOINTS[region].keys())
            raise ValueError(f"Unsupported layer: {layer}. Available for {region}: {available_layers}")
        
        self.region = region
        self.layer = layer
        self.config = self.ENDPOINTS[region][layer]
        self._cache = {}  # Simple in-memory cache
        self._cache_ttl = timedelta(hours=1)  # Cache for 1 hour
        super().__init__(self.config["url"])
    
    async def query_parcels_by_bbox(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        limit: int = 100,
        offset: int = 0,
        cache_key_suffix: str = ""
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Query parcels within bounding box with caching and metadata."""
        # Generate cache key
        cache_key = self._generate_cache_key(
            "bbox", min_lon, min_lat, max_lon, max_lat, limit, offset, cache_key_suffix
        )
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for bbox query: {cache_key}")
            return cached_result['data'], cached_result['metadata']
        
        # Validate bbox
        if not self._validate_bbox(min_lon, min_lat, max_lon, max_lat):
            logger.error(f"Invalid bounding box: {min_lon},{min_lat},{max_lon},{max_lat}")
            return [], {"error": "Invalid bounding box"}
        
        # Limit to service maximum
        max_records = self.config.get("max_records", 1000)
        limit = min(limit, max_records)
        
        params = {
            "where": "1=1",
            "geometry": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "geometryType": "esriGeometryEnvelope",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": limit,
            "returnCountOnly": "false",
            "returnExtentOnly": "false"
        }
        
        try:
            start_time = datetime.now()
            result = await self.fetch("query", params=params, timeout=30)
            end_time = datetime.now()
            
            parcels = self._parse_features(result.get("features", []))
            
            # Build metadata
            metadata = {
                "total_features": len(result.get("features", [])),
                "returned_count": len(parcels),
                "offset": offset,
                "limit": limit,
                "query_time_ms": int((end_time - start_time).total_seconds() * 1000),
                "source": f"arcgis_{self.region}_{self.layer}",
                "bbox": [min_lon, min_lat, max_lon, max_lat],
                "exceeded_transfer_limit": result.get("exceededTransferLimit", False)
            }
            
            # Cache the result
            self._set_cache(cache_key, {"data": parcels, "metadata": metadata})
            
            logger.info(f"Retrieved {len(parcels)} parcels from {self.region} in {metadata['query_time_ms']}ms")
            return parcels, metadata
            
        except Exception as e:
            logger.error(f"Failed to query parcels from {self.region}: {e}")
            error_metadata = {
                "error": str(e),
                "source": f"arcgis_{self.region}_{self.layer}",
                "bbox": [min_lon, min_lat, max_lon, max_lat]
            }
            return [], error_metadata
    
    async def query_parcels_by_polygon(
        self,
        polygon: Polygon,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query parcels within polygon area."""
        # Convert polygon to ArcGIS ring format
        rings = [list(polygon.exterior.coords)]
        
        params = {
            "where": "1=1",
            "geometry": json.dumps({
                "rings": rings,
                "spatialReference": {"wkid": 4326}
            }),
            "geometryType": "esriGeometryPolygon",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": limit
        }
        
        try:
            result = await self.fetch("query", params=params)
            return self._parse_features(result.get("features", []))
        except Exception as e:
            logger.error(f"Failed to query parcels by polygon: {e}")
            return []
    
    async def get_parcel_by_id(self, parcel_id: str) -> Optional[Dict[str, Any]]:
        """Get specific parcel by ID with caching."""
        cache_key = f"parcel_{self.region}_{self.layer}_{parcel_id}"
        
        # Check cache
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for parcel {parcel_id}")
            return cached_result
        
        id_field = self.config["id_field"]
        
        # Escape single quotes in parcel_id
        escaped_id = parcel_id.replace("'", "''")
        
        params = {
            "where": f"{id_field} = '{escaped_id}'",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "geojson"
        }
        
        try:
            result = await self.fetch("query", params=params, timeout=10)
            features = self._parse_features(result.get("features", []))
            
            parcel = features[0] if features else None
            
            # Cache individual parcel results
            self._set_cache(cache_key, parcel)
            
            if parcel:
                logger.debug(f"Retrieved parcel {parcel_id} from {self.region}")
            else:
                logger.warning(f"Parcel {parcel_id} not found in {self.region}")
            
            return parcel
            
        except Exception as e:
            logger.error(f"Failed to get parcel {parcel_id} from {self.region}: {e}")
            return None
    
    async def query_parcels_with_filters(
        self,
        bbox: Optional[tuple] = None,
        zoning_codes: Optional[List[str]] = None,
        min_area: Optional[float] = None,
        max_area: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query parcels with multiple filters."""
        # Build where clause
        where_clauses = []
        
        if min_area:
            area_field = self.config.get("area_field", "Shape__Area")
            where_clauses.append(f"{area_field} >= {min_area}")
        
        if max_area:
            area_field = self.config.get("area_field", "Shape__Area")
            where_clauses.append(f"{area_field} <= {max_area}")
        
        if zoning_codes and "zoning_field" in self.config:
            zoning_field = self.config["zoning_field"]
            codes_str = "','".join(zoning_codes)
            where_clauses.append(f"{zoning_field} IN ('{codes_str}')")
        
        where = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        params = {
            "where": where,
            "outFields": "*",
            "returnGeometry": "true",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": limit
        }
        
        # Add spatial filter if bbox provided
        if bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            params.update({
                "geometry": f"{min_lon},{min_lat},{max_lon},{max_lat}",
                "geometryType": "esriGeometryEnvelope",
                "spatialRel": "esriSpatialRelIntersects"
            })
        
        try:
            result = await self.fetch("query", params=params)
            return self._parse_features(result.get("features", []))
        except Exception as e:
            logger.error(f"Failed to query parcels with filters: {e}")
            return []
    
    def _parse_features(self, features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse GeoJSON features into standard format with validation."""
        parcels = []
        parse_errors = 0
        
        for idx, feature in enumerate(features):
            try:
                # Extract and validate geometry
                geom_data = feature.get("geometry")
                if not geom_data:
                    logger.warning(f"Feature {idx} missing geometry")
                    parse_errors += 1
                    continue
                
                geom = shape(geom_data)
                
                # Validate geometry
                if not geom.is_valid:
                    logger.warning(f"Feature {idx} has invalid geometry")
                    # Try to fix simple issues
                    geom = geom.buffer(0)
                    if not geom.is_valid:
                        parse_errors += 1
                        continue
                
                # Extract properties
                props = feature.get("properties", {})
                
                # Extract and validate external ID
                external_id = props.get(self.config["id_field"])
                if not external_id:
                    logger.warning(f"Feature {idx} missing ID field {self.config['id_field']}")
                    external_id = f"unknown_{idx}"
                
                # Calculate area if not provided
                area_sqft = props.get(self.config.get("area_field"))
                if not area_sqft and geom.geom_type in ['Polygon', 'MultiPolygon']:
                    # Convert from square degrees to approximate square feet
                    # This is rough but better than nothing
                    area_sqft = geom.area * 10763910.4  # sq degrees to sq feet (approximate)
                
                # Extract zoning code
                zoning_code = props.get(self.config.get("zoning_field"))
                
                # Calculate centroid
                try:
                    centroid = geom.centroid
                except Exception:
                    centroid = None
                
                # Map to standard format
                parcel = {
                    "external_id": str(external_id),
                    "geometry": geom,
                    "centroid": centroid,
                    "area_sqft": float(area_sqft) if area_sqft else None,
                    "zoning_code": zoning_code,
                    "attributes": props,
                    "source": f"arcgis_{self.region}_{self.layer}",
                    "region_code": self.region,
                    "parsed_at": datetime.now().isoformat()
                }
                
                parcels.append(parcel)
                
            except Exception as e:
                logger.warning(f"Failed to parse feature {idx}: {e}")
                parse_errors += 1
                continue
        
        if parse_errors > 0:
            logger.warning(f"Failed to parse {parse_errors}/{len(features)} features")
        
        return parcels
    
    async def get_metadata(self) -> Dict[str, Any]:
        """Get metadata about the feature service with caching."""
        cache_key = f"metadata_{self.region}_{self.layer}"
        
        # Check cache
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        try:
            result = await self.fetch("", params={"f": "json"}, timeout=10)
            
            metadata = {
                "name": result.get("name"),
                "description": result.get("description"),
                "extent": result.get("extent"),
                "fields": result.get("fields", []),
                "capabilities": result.get("capabilities"),
                "maxRecordCount": result.get("maxRecordCount", 1000),
                "geometryType": result.get("geometryType"),
                "spatialReference": result.get("spatialReference"),
                "service_url": self.config["url"],
                "region": self.region,
                "layer": self.layer,
                "last_updated": datetime.now().isoformat()
            }
            
            # Cache metadata for longer (24 hours)
            self._set_cache(cache_key, metadata, ttl=timedelta(hours=24))
            
            logger.info(f"Retrieved metadata for {self.region}/{self.layer}")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get metadata for {self.region}/{self.layer}: {e}")
            return {"error": str(e), "region": self.region, "layer": self.layer}
    
    def _generate_cache_key(self, *args) -> str:
        """Generate a cache key from arguments."""
        key_string = "_".join(str(arg) for arg in args)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired."""
        if key in self._cache:
            item, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._cache_ttl:
                return item
            else:
                # Remove expired item
                del self._cache[key]
        return None
    
    def _set_cache(self, key: str, value: Any, ttl: Optional[timedelta] = None):
        """Set item in cache with timestamp."""
        self._cache[key] = (value, datetime.now())
        
        # Simple cache cleanup - remove old items if cache gets too large
        if len(self._cache) > 100:
            # Remove oldest 20 items
            oldest_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k][1]
            )[:20]
            for old_key in oldest_keys:
                del self._cache[old_key]
    
    def _validate_bbox(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> bool:
        """Validate bounding box coordinates."""
        # Check coordinate ranges
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            return False
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            return False
        
        # Check that min < max
        if min_lon >= max_lon or min_lat >= max_lat:
            return False
        
        # Check reasonable size (not larger than a state)
        if (max_lon - min_lon) > 10 or (max_lat - min_lat) > 10:
            logger.warning(f"Very large bbox: {max_lon - min_lon}° x {max_lat - min_lat}°")
        
        return True
    
    async def batch_query_with_pagination(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        max_total: int = 10000
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Query parcels with automatic pagination to get all results."""
        all_parcels = []
        all_metadata = []
        offset = 0
        limit = self.config.get("max_records", 1000)
        
        logger.info(f"Starting batch query for {self.region} with max {max_total} parcels")
        
        while len(all_parcels) < max_total:
            remaining = max_total - len(all_parcels)
            current_limit = min(limit, remaining)
            
            parcels, metadata = await self.query_parcels_by_bbox(
                min_lon, min_lat, max_lon, max_lat,
                limit=current_limit,
                offset=offset,
                cache_key_suffix=f"batch_{offset}"
            )
            
            if not parcels:
                logger.info(f"No more parcels returned at offset {offset}")
                break
            
            all_parcels.extend(parcels)
            all_metadata.append(metadata)
            offset += len(parcels)
            
            # If we got fewer than requested, we've reached the end
            if len(parcels) < current_limit:
                logger.info(f"Reached end of results at offset {offset}")
                break
            
            # Small delay to be respectful to the service
            await asyncio.sleep(0.1)
        
        # Combine metadata
        combined_metadata = {
            "total_returned": len(all_parcels),
            "total_queries": len(all_metadata),
            "source": f"arcgis_{self.region}_{self.layer}",
            "bbox": [min_lon, min_lat, max_lon, max_lat],
            "queries": all_metadata
        }
        
        logger.info(f"Batch query completed: {len(all_parcels)} parcels from {len(all_metadata)} queries")
        return all_parcels, combined_metadata