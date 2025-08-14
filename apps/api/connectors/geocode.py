"""
Geocoding connector for address to coordinate conversion
"""

from typing import Optional, Dict, Any, List
from urllib.parse import urlencode
import logging

from .base import BaseConnector, ConnectorResponse, RateLimitInfo
from core.config import settings

logger = logging.getLogger(__name__)


class GeocodeConnector(BaseConnector):
    """
    Universal geocoding connector supporting multiple providers
    """
    
    def __init__(
        self,
        provider: str = "google",
        api_key: Optional[str] = None,
        **kwargs
    ):
        self.provider = provider.lower()
        
        # Provider-specific configuration
        if self.provider == "google":
            base_url = "https://maps.googleapis.com/maps/api"
            rate_limit = RateLimitInfo(
                requests_per_second=10,
                requests_per_minute=600,
                requests_per_hour=36000,
                requests_per_day=864000
            )
        elif self.provider == "mapbox":
            base_url = "https://api.mapbox.com"
            rate_limit = RateLimitInfo(
                requests_per_second=10,
                requests_per_minute=600,
                requests_per_hour=36000,
                requests_per_day=100000
            )
        elif self.provider == "arcgis":
            base_url = "https://geocode.arcgis.com/arcgis/rest/services"
            rate_limit = RateLimitInfo(
                requests_per_second=5,
                requests_per_minute=300,
                requests_per_hour=18000,
                requests_per_day=432000
            )
        else:
            raise ValueError(f"Unsupported geocoding provider: {provider}")
        
        super().__init__(
            api_key=api_key or settings.GEOCODING_API_KEY,
            base_url=base_url,
            rate_limit=rate_limit,
            **kwargs
        )
    
    async def test_connection(self) -> ConnectorResponse:
        """Test the geocoding service connection"""
        try:
            # Test with a simple address
            result = await self.geocode("1600 Amphitheatre Parkway, Mountain View, CA")
            
            if result.success:
                return ConnectorResponse(
                    success=True,
                    data={
                        "status": "connected",
                        "provider": self.provider,
                        "test_result": "success"
                    }
                )
            else:
                return ConnectorResponse(
                    success=False,
                    error=f"Test geocoding failed: {result.error}"
                )
        
        except Exception as e:
            return ConnectorResponse(
                success=False,
                error=f"Connection test failed: {str(e)}"
            )
    
    async def get_service_info(self) -> ConnectorResponse:
        """Get geocoding service information"""
        provider_info = {
            "google": {
                "name": "Google Geocoding API",
                "documentation": "https://developers.google.com/maps/documentation/geocoding",
                "features": ["geocoding", "reverse_geocoding", "place_details"]
            },
            "mapbox": {
                "name": "Mapbox Geocoding API",
                "documentation": "https://docs.mapbox.com/api/search/geocoding/",
                "features": ["geocoding", "reverse_geocoding", "batch_geocoding"]
            },
            "arcgis": {
                "name": "ArcGIS World Geocoding Service",
                "documentation": "https://developers.arcgis.com/rest/geocode/api-reference/",
                "features": ["geocoding", "reverse_geocoding", "suggest"]
            }
        }
        
        return ConnectorResponse(
            success=True,
            data={
                "provider": self.provider,
                "info": provider_info.get(self.provider, {}),
                "rate_limit": self.rate_limit.__dict__ if self.rate_limit else None
            }
        )
    
    async def geocode(
        self,
        address: str,
        components: Optional[Dict[str, str]] = None,
        bounds: Optional[Dict[str, float]] = None
    ) -> ConnectorResponse:
        """
        Geocode an address to coordinates
        
        Args:
            address: Address string to geocode
            components: Component filters (country, administrative_area, etc.)
            bounds: Bounding box to bias results
            
        Returns:
            ConnectorResponse: Geocoding result with coordinates and details
        """
        try:
            if self.provider == "google":
                return await self._geocode_google(address, components, bounds)
            elif self.provider == "mapbox":
                return await self._geocode_mapbox(address, components, bounds)
            elif self.provider == "arcgis":
                return await self._geocode_arcgis(address, components, bounds)
            else:
                return ConnectorResponse(
                    success=False,
                    error=f"Unsupported provider: {self.provider}"
                )
        
        except Exception as e:
            logger.error(f"Geocoding error: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"Geocoding failed: {str(e)}"
            )
    
    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        result_type: Optional[str] = None
    ) -> ConnectorResponse:
        """
        Reverse geocode coordinates to address
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            result_type: Type of result to return
            
        Returns:
            ConnectorResponse: Reverse geocoding result with address details
        """
        try:
            if self.provider == "google":
                return await self._reverse_geocode_google(latitude, longitude, result_type)
            elif self.provider == "mapbox":
                return await self._reverse_geocode_mapbox(latitude, longitude, result_type)
            elif self.provider == "arcgis":
                return await self._reverse_geocode_arcgis(latitude, longitude, result_type)
            else:
                return ConnectorResponse(
                    success=False,
                    error=f"Unsupported provider: {self.provider}"
                )
        
        except Exception as e:
            logger.error(f"Reverse geocoding error: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"Reverse geocoding failed: {str(e)}"
            )
    
    async def _geocode_google(
        self,
        address: str,
        components: Optional[Dict[str, str]] = None,
        bounds: Optional[Dict[str, float]] = None
    ) -> ConnectorResponse:
        """Geocode using Google Maps API"""
        params = {
            "address": address,
            "key": self.api_key
        }
        
        if components:
            component_str = "|".join([f"{k}:{v}" for k, v in components.items()])
            params["components"] = component_str
        
        if bounds:
            params["bounds"] = f"{bounds['south']},{bounds['west']}|{bounds['north']},{bounds['east']}"
        
        response = await self._make_request("GET", "/geocode/json", params=params)
        
        if not response.success:
            return response
        
        data = response.data
        if data.get("status") == "OK" and data.get("results"):
            result = data["results"][0]
            location = result["geometry"]["location"]
            
            return ConnectorResponse(
                success=True,
                data={
                    "latitude": location["lat"],
                    "longitude": location["lng"],
                    "formatted_address": result["formatted_address"],
                    "place_id": result.get("place_id"),
                    "types": result.get("types", []),
                    "address_components": result.get("address_components", []),
                    "geometry": result.get("geometry", {}),
                    "provider": "google"
                },
                metadata={"total_results": len(data["results"])}
            )
        else:
            return ConnectorResponse(
                success=False,
                error=f"Geocoding failed: {data.get('status', 'Unknown error')}"
            )
    
    async def _geocode_mapbox(
        self,
        address: str,
        components: Optional[Dict[str, str]] = None,
        bounds: Optional[Dict[str, float]] = None
    ) -> ConnectorResponse:
        """Geocode using Mapbox API"""
        url = f"/geocoding/v5/mapbox.places/{address}.json"
        params = {
            "access_token": self.api_key,
            "limit": 1
        }
        
        if components and "country" in components:
            params["country"] = components["country"]
        
        if bounds:
            params["bbox"] = f"{bounds['west']},{bounds['south']},{bounds['east']},{bounds['north']}"
        
        response = await self._make_request("GET", url, params=params)
        
        if not response.success:
            return response
        
        data = response.data
        if data.get("features"):
            feature = data["features"][0]
            coordinates = feature["geometry"]["coordinates"]
            
            return ConnectorResponse(
                success=True,
                data={
                    "latitude": coordinates[1],
                    "longitude": coordinates[0],
                    "formatted_address": feature["place_name"],
                    "place_id": feature.get("id"),
                    "types": feature.get("place_type", []),
                    "properties": feature.get("properties", {}),
                    "context": feature.get("context", []),
                    "provider": "mapbox"
                },
                metadata={"total_results": len(data["features"])}
            )
        else:
            return ConnectorResponse(
                success=False,
                error="No geocoding results found"
            )
    
    async def _geocode_arcgis(
        self,
        address: str,
        components: Optional[Dict[str, str]] = None,
        bounds: Optional[Dict[str, float]] = None
    ) -> ConnectorResponse:
        """Geocode using ArcGIS API"""
        params = {
            "SingleLine": address,
            "f": "json",
            "outFields": "*",
            "maxLocations": 1
        }
        
        if self.api_key:
            params["token"] = self.api_key
        
        if components and "country" in components:
            params["countryCode"] = components["country"]
        
        if bounds:
            params["searchExtent"] = f"{bounds['west']},{bounds['south']},{bounds['east']},{bounds['north']}"
        
        response = await self._make_request(
            "GET",
            "/World/GeocodeServer/findAddressCandidates",
            params=params
        )
        
        if not response.success:
            return response
        
        data = response.data
        if data.get("candidates"):
            candidate = data["candidates"][0]
            location = candidate["location"]
            
            return ConnectorResponse(
                success=True,
                data={
                    "latitude": location["y"],
                    "longitude": location["x"],
                    "formatted_address": candidate["address"],
                    "score": candidate.get("score"),
                    "attributes": candidate.get("attributes", {}),
                    "provider": "arcgis"
                },
                metadata={"total_results": len(data["candidates"])}
            )
        else:
            return ConnectorResponse(
                success=False,
                error="No geocoding results found"
            )
    
    async def _reverse_geocode_google(
        self,
        latitude: float,
        longitude: float,
        result_type: Optional[str] = None
    ) -> ConnectorResponse:
        """Reverse geocode using Google Maps API"""
        params = {
            "latlng": f"{latitude},{longitude}",
            "key": self.api_key
        }
        
        if result_type:
            params["result_type"] = result_type
        
        response = await self._make_request("GET", "/geocode/json", params=params)
        
        if not response.success:
            return response
        
        data = response.data
        if data.get("status") == "OK" and data.get("results"):
            results = data["results"]
            
            return ConnectorResponse(
                success=True,
                data={
                    "results": results,
                    "formatted_address": results[0]["formatted_address"] if results else None,
                    "provider": "google"
                },
                metadata={"total_results": len(results)}
            )
        else:
            return ConnectorResponse(
                success=False,
                error=f"Reverse geocoding failed: {data.get('status', 'Unknown error')}"
            )
    
    async def _reverse_geocode_mapbox(
        self,
        latitude: float,
        longitude: float,
        result_type: Optional[str] = None
    ) -> ConnectorResponse:
        """Reverse geocode using Mapbox API"""
        url = f"/geocoding/v5/mapbox.places/{longitude},{latitude}.json"
        params = {
            "access_token": self.api_key,
            "limit": 5
        }
        
        if result_type:
            params["types"] = result_type
        
        response = await self._make_request("GET", url, params=params)
        
        if not response.success:
            return response
        
        data = response.data
        features = data.get("features", [])
        
        return ConnectorResponse(
            success=True,
            data={
                "results": features,
                "formatted_address": features[0]["place_name"] if features else None,
                "provider": "mapbox"
            },
            metadata={"total_results": len(features)}
        )
    
    async def _reverse_geocode_arcgis(
        self,
        latitude: float,
        longitude: float,
        result_type: Optional[str] = None
    ) -> ConnectorResponse:
        """Reverse geocode using ArcGIS API"""
        params = {
            "location": f"{longitude},{latitude}",
            "f": "json",
            "outFields": "*"
        }
        
        if self.api_key:
            params["token"] = self.api_key
        
        response = await self._make_request(
            "GET",
            "/World/GeocodeServer/reverseGeocode",
            params=params
        )
        
        if not response.success:
            return response
        
        data = response.data
        if data.get("address"):
            return ConnectorResponse(
                success=True,
                data={
                    "results": [data],
                    "formatted_address": data["address"].get("Match_addr"),
                    "provider": "arcgis"
                },
                metadata={"total_results": 1}
            )
        else:
            return ConnectorResponse(
                success=False,
                error="No reverse geocoding results found"
            )
    
    async def batch_geocode(
        self,
        addresses: List[str],
        max_concurrent: int = 5
    ) -> ConnectorResponse:
        """
        Batch geocode multiple addresses
        
        Args:
            addresses: List of addresses to geocode
            max_concurrent: Maximum concurrent requests
            
        Returns:
            ConnectorResponse: Batch geocoding results
        """
        import asyncio
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def geocode_single(address):
            async with semaphore:
                return await self.geocode(address)
        
        try:
            tasks = [geocode_single(address) for address in addresses]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_results = []
            failed_results = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_results.append({
                        "address": addresses[i],
                        "error": str(result)
                    })
                elif result.success:
                    successful_results.append({
                        "address": addresses[i],
                        "result": result.data
                    })
                else:
                    failed_results.append({
                        "address": addresses[i],
                        "error": result.error
                    })
            
            return ConnectorResponse(
                success=True,
                data={
                    "successful": successful_results,
                    "failed": failed_results,
                    "total_processed": len(addresses),
                    "success_count": len(successful_results),
                    "failure_count": len(failed_results)
                }
            )
        
        except Exception as e:
            return ConnectorResponse(
                success=False,
                error=f"Batch geocoding failed: {str(e)}"
            )