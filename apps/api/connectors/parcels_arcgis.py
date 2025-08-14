"""
ArcGIS parcel data connector for property information
"""

from typing import Optional, Dict, Any, List
import logging

from .base import BaseConnector, ConnectorResponse, RateLimitInfo
from core.config import settings

logger = logging.getLogger(__name__)


class ArcGISParcelConnector(BaseConnector):
    """
    Connector for ArcGIS-based parcel data services
    Supports various county and state parcel databases
    """
    
    def __init__(
        self,
        service_url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ):
        # Default to generic ArcGIS service if no URL provided
        base_url = service_url or "https://services.arcgis.com"
        
        # Standard ArcGIS rate limits
        rate_limit = RateLimitInfo(
            requests_per_second=10,
            requests_per_minute=600,
            requests_per_hour=36000,
            requests_per_day=864000
        )
        
        super().__init__(
            api_key=api_key or settings.ARCGIS_API_KEY,
            base_url=base_url,
            rate_limit=rate_limit,
            timeout=30,
            **kwargs
        )
        
        # Common ArcGIS endpoints
        self.endpoints = {
            "parcels": "/MapServer/0",
            "assessments": "/MapServer/1",
            "owners": "/MapServer/2",
            "sales": "/MapServer/3"
        }
    
    async def test_connection(self) -> ConnectorResponse:
        """Test the ArcGIS service connection"""
        try:
            # Test with a simple service info request
            response = await self._make_request(
                "GET",
                f"{self.endpoints['parcels']}",
                params={"f": "json"}
            )
            
            if response.success:
                service_info = response.data
                return ConnectorResponse(
                    success=True,
                    data={
                        "status": "connected",
                        "service": "ArcGIS Parcel Service",
                        "service_name": service_info.get("name", "Unknown"),
                        "description": service_info.get("description", ""),
                        "max_record_count": service_info.get("maxRecordCount", 1000)
                    }
                )
            else:
                return response
        
        except Exception as e:
            return ConnectorResponse(
                success=False,
                error=f"Connection test failed: {str(e)}"
            )
    
    async def get_service_info(self) -> ConnectorResponse:
        """Get ArcGIS service information"""
        try:
            response = await self._make_request(
                "GET",
                "/",
                params={"f": "json"}
            )
            
            if response.success:
                return ConnectorResponse(
                    success=True,
                    data={
                        "service_info": response.data,
                        "endpoints": self.endpoints,
                        "rate_limit": self.rate_limit.__dict__ if self.rate_limit else None
                    }
                )
            else:
                return response
        
        except Exception as e:
            return ConnectorResponse(
                success=False,
                error=f"Failed to get service info: {str(e)}"
            )
    
    async def get_parcel_by_point(
        self,
        latitude: float,
        longitude: float,
        return_geometry: bool = True
    ) -> ConnectorResponse:
        """
        Get parcel information by geographic point
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            return_geometry: Whether to include geometry in response
            
        Returns:
            ConnectorResponse: Parcel information
        """
        try:
            # Construct spatial query
            geometry = f"{longitude},{latitude}"
            
            params = {
                "f": "json",
                "geometry": geometry,
                "geometryType": "esriGeometryPoint",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "*",
                "returnGeometry": "true" if return_geometry else "false",
                "maxRecordCount": 1
            }
            
            if self.api_key:
                params["token"] = self.api_key
            
            response = await self._make_request(
                "GET",
                f"{self.endpoints['parcels']}/query",
                params=params
            )
            
            if not response.success:
                return response
            
            data = response.data
            features = data.get("features", [])
            
            if not features:
                return ConnectorResponse(
                    success=False,
                    error="No parcel found at the specified location"
                )
            
            parcel = features[0]
            attributes = parcel.get("attributes", {})
            geometry = parcel.get("geometry") if return_geometry else None
            
            # Standardize parcel data
            standardized_parcel = self._standardize_parcel_data(attributes, geometry)
            
            return ConnectorResponse(
                success=True,
                data=standardized_parcel,
                metadata={
                    "total_features": len(features),
                    "coordinate": [latitude, longitude]
                }
            )
        
        except Exception as e:
            logger.error(f"Error getting parcel by point: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"Failed to get parcel: {str(e)}"
            )
    
    async def get_parcel_by_apn(
        self,
        apn: str,
        apn_field: str = "APN",
        return_geometry: bool = True
    ) -> ConnectorResponse:
        """
        Get parcel information by Assessor's Parcel Number (APN)
        
        Args:
            apn: Assessor's Parcel Number
            apn_field: Field name for APN in the service
            return_geometry: Whether to include geometry in response
            
        Returns:
            ConnectorResponse: Parcel information
        """
        try:
            where_clause = f"{apn_field} = '{apn}'"
            
            params = {
                "f": "json",
                "where": where_clause,
                "outFields": "*",
                "returnGeometry": "true" if return_geometry else "false",
                "maxRecordCount": 1
            }
            
            if self.api_key:
                params["token"] = self.api_key
            
            response = await self._make_request(
                "GET",
                f"{self.endpoints['parcels']}/query",
                params=params
            )
            
            if not response.success:
                return response
            
            data = response.data
            features = data.get("features", [])
            
            if not features:
                return ConnectorResponse(
                    success=False,
                    error=f"No parcel found with APN: {apn}"
                )
            
            parcel = features[0]
            attributes = parcel.get("attributes", {})
            geometry = parcel.get("geometry") if return_geometry else None
            
            standardized_parcel = self._standardize_parcel_data(attributes, geometry)
            
            return ConnectorResponse(
                success=True,
                data=standardized_parcel,
                metadata={"apn": apn, "apn_field": apn_field}
            )
        
        except Exception as e:
            logger.error(f"Error getting parcel by APN: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"Failed to get parcel: {str(e)}"
            )
    
    async def search_parcels(
        self,
        where_clause: str,
        return_geometry: bool = False,
        max_results: int = 100
    ) -> ConnectorResponse:
        """
        Search parcels using SQL where clause
        
        Args:
            where_clause: SQL where clause for filtering
            return_geometry: Whether to include geometry in response
            max_results: Maximum number of results to return
            
        Returns:
            ConnectorResponse: Search results
        """
        try:
            params = {
                "f": "json",
                "where": where_clause,
                "outFields": "*",
                "returnGeometry": "true" if return_geometry else "false",
                "maxRecordCount": max_results
            }
            
            if self.api_key:
                params["token"] = self.api_key
            
            response = await self._make_request(
                "GET",
                f"{self.endpoints['parcels']}/query",
                params=params
            )
            
            if not response.success:
                return response
            
            data = response.data
            features = data.get("features", [])
            
            standardized_parcels = []
            for feature in features:
                attributes = feature.get("attributes", {})
                geometry = feature.get("geometry") if return_geometry else None
                standardized_parcel = self._standardize_parcel_data(attributes, geometry)
                standardized_parcels.append(standardized_parcel)
            
            return ConnectorResponse(
                success=True,
                data={
                    "parcels": standardized_parcels,
                    "total_results": len(standardized_parcels),
                    "exceeded_transfer_limit": data.get("exceededTransferLimit", False)
                },
                metadata={"where_clause": where_clause}
            )
        
        except Exception as e:
            logger.error(f"Error searching parcels: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"Parcel search failed: {str(e)}"
            )
    
    async def get_parcels_in_bounds(
        self,
        min_longitude: float,
        min_latitude: float,
        max_longitude: float,
        max_latitude: float,
        return_geometry: bool = False,
        max_results: int = 500
    ) -> ConnectorResponse:
        """
        Get parcels within bounding box
        
        Args:
            min_longitude: Minimum longitude
            min_latitude: Minimum latitude
            max_longitude: Maximum longitude
            max_latitude: Maximum latitude
            return_geometry: Whether to include geometry
            max_results: Maximum number of results
            
        Returns:
            ConnectorResponse: Parcels within bounds
        """
        try:
            # Construct envelope geometry
            envelope = f"{min_longitude},{min_latitude},{max_longitude},{max_latitude}"
            
            params = {
                "f": "json",
                "geometry": envelope,
                "geometryType": "esriGeometryEnvelope",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "*",
                "returnGeometry": "true" if return_geometry else "false",
                "maxRecordCount": max_results
            }
            
            if self.api_key:
                params["token"] = self.api_key
            
            response = await self._make_request(
                "GET",
                f"{self.endpoints['parcels']}/query",
                params=params
            )
            
            if not response.success:
                return response
            
            data = response.data
            features = data.get("features", [])
            
            standardized_parcels = []
            for feature in features:
                attributes = feature.get("attributes", {})
                geometry = feature.get("geometry") if return_geometry else None
                standardized_parcel = self._standardize_parcel_data(attributes, geometry)
                standardized_parcels.append(standardized_parcel)
            
            return ConnectorResponse(
                success=True,
                data={
                    "parcels": standardized_parcels,
                    "total_results": len(standardized_parcels),
                    "bounds": {
                        "min_longitude": min_longitude,
                        "min_latitude": min_latitude,
                        "max_longitude": max_longitude,
                        "max_latitude": max_latitude
                    }
                }
            )
        
        except Exception as e:
            logger.error(f"Error getting parcels in bounds: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"Failed to get parcels in bounds: {str(e)}"
            )
    
    async def get_assessment_data(
        self,
        parcel_id: str,
        id_field: str = "PARCEL_ID"
    ) -> ConnectorResponse:
        """
        Get assessment data for a parcel
        
        Args:
            parcel_id: Parcel identifier
            id_field: Field name for parcel ID
            
        Returns:
            ConnectorResponse: Assessment data
        """
        try:
            where_clause = f"{id_field} = '{parcel_id}'"
            
            params = {
                "f": "json",
                "where": where_clause,
                "outFields": "*",
                "returnGeometry": "false"
            }
            
            if self.api_key:
                params["token"] = self.api_key
            
            response = await self._make_request(
                "GET",
                f"{self.endpoints['assessments']}/query",
                params=params
            )
            
            if not response.success:
                return response
            
            data = response.data
            features = data.get("features", [])
            
            if not features:
                return ConnectorResponse(
                    success=False,
                    error=f"No assessment data found for parcel: {parcel_id}"
                )
            
            assessment = features[0].get("attributes", {})
            standardized_assessment = self._standardize_assessment_data(assessment)
            
            return ConnectorResponse(
                success=True,
                data=standardized_assessment,
                metadata={"parcel_id": parcel_id}
            )
        
        except Exception as e:
            logger.error(f"Error getting assessment data: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"Failed to get assessment data: {str(e)}"
            )
    
    def _standardize_parcel_data(
        self,
        attributes: Dict[str, Any],
        geometry: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Standardize parcel data from ArcGIS service
        
        Args:
            attributes: Raw attributes from ArcGIS
            geometry: Geometry data (optional)
            
        Returns:
            Dict[str, Any]: Standardized parcel data
        """
        # Common field mappings (these may vary by service)
        field_mappings = {
            "APN": ["APN", "PARCEL_ID", "PARCEL_NUMBER", "PIN"],
            "OWNER_NAME": ["OWNER_NAME", "OWNER", "OWNERNAME", "TAXPAYER"],
            "SITUS_ADDRESS": ["SITUS_ADDRESS", "ADDRESS", "SITE_ADDR", "PROP_ADDR"],
            "LAND_VALUE": ["LAND_VALUE", "LANDVAL", "ASSESSED_LAND"],
            "IMPROVEMENT_VALUE": ["IMPROVEMENT_VALUE", "IMPVAL", "ASSESSED_IMP"],
            "TOTAL_VALUE": ["TOTAL_VALUE", "TOTALVAL", "ASSESSED_TOTAL"],
            "ACRES": ["ACRES", "ACREAGE", "AREA_ACRES"],
            "SQUARE_FEET": ["SQUARE_FEET", "AREA_SQFT", "LOT_SIZE"],
            "YEAR_BUILT": ["YEAR_BUILT", "YR_BLT", "BUILD_YEAR"],
            "LAND_USE": ["LAND_USE", "USE_CODE", "PROPERTY_TYPE"],
            "ZONING": ["ZONING", "ZONE", "ZONING_CODE"]
        }
        
        standardized = {}
        
        # Map fields using field mappings
        for standard_field, possible_fields in field_mappings.items():
            for field in possible_fields:
                if field in attributes and attributes[field] is not None:
                    standardized[standard_field.lower()] = attributes[field]
                    break
        
        # Add geometry if provided
        if geometry:
            standardized["geometry"] = geometry
            
            # Calculate centroid for polygon geometry
            if geometry.get("type") == "polygon" and geometry.get("rings"):
                rings = geometry["rings"][0]  # Outer ring
                if rings:
                    # Simple centroid calculation
                    x_coords = [point[0] for point in rings]
                    y_coords = [point[1] for point in rings]
                    centroid_x = sum(x_coords) / len(x_coords)
                    centroid_y = sum(y_coords) / len(y_coords)
                    standardized["centroid"] = {
                        "longitude": centroid_x,
                        "latitude": centroid_y
                    }
        
        # Add all original attributes for reference
        standardized["original_attributes"] = attributes
        
        # Add data source metadata
        standardized["data_source"] = "arcgis"
        standardized["last_updated"] = attributes.get("LAST_UPDATE", attributes.get("EditDate"))
        
        return standardized
    
    def _standardize_assessment_data(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize assessment data from ArcGIS service
        
        Args:
            attributes: Raw assessment attributes
            
        Returns:
            Dict[str, Any]: Standardized assessment data
        """
        standardized = {
            "assessed_value": attributes.get("ASSESSED_VALUE") or attributes.get("TOTAL_VALUE"),
            "land_value": attributes.get("LAND_VALUE"),
            "improvement_value": attributes.get("IMPROVEMENT_VALUE"),
            "tax_year": attributes.get("TAX_YEAR") or attributes.get("YEAR"),
            "tax_amount": attributes.get("TAX_AMOUNT") or attributes.get("ANNUAL_TAX"),
            "exemptions": attributes.get("EXEMPTIONS"),
            "assessment_date": attributes.get("ASSESSMENT_DATE"),
            "original_attributes": attributes,
            "data_source": "arcgis_assessment"
        }
        
        return standardized