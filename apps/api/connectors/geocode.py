"""Geocoding service connector with multiple providers."""
from typing import Dict, Any, Optional, Tuple
import httpx
import logging

from connectors.base import BaseConnector
from core.config import settings

logger = logging.getLogger(__name__)


class GeocodeConnector:
    """Multi-provider geocoding service."""
    
    def __init__(self):
        self.providers = self._init_providers()
    
    def _init_providers(self) -> Dict[str, BaseConnector]:
        """Initialize available geocoding providers."""
        providers = {}
        
        # Always include Nominatim (free)
        providers["nominatim"] = NominatimProvider()
        
        # Add paid providers if keys are available
        if settings.MAPBOX_TOKEN:
            providers["mapbox"] = MapboxProvider(settings.MAPBOX_TOKEN)
        
        if settings.GOOGLE_MAPS_API_KEY:
            providers["google"] = GoogleMapsProvider(settings.GOOGLE_MAPS_API_KEY)
        
        if settings.MAPTILER_KEY:
            providers["maptiler"] = MapTilerProvider(settings.MAPTILER_KEY)
        
        return providers
    
    async def geocode(
        self,
        address: str,
        provider: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Geocode an address to coordinates."""
        # Use specified provider or fall back to available ones
        if provider and provider in self.providers:
            return await self.providers[provider].geocode(address)
        
        # Try providers in order of preference
        for provider_name in ["nominatim", "mapbox", "google", "maptiler"]:
            if provider_name in self.providers:
                try:
                    result = await self.providers[provider_name].geocode(address)
                    if result:
                        return result
                except Exception as e:
                    logger.warning(f"Geocoding failed with {provider_name}: {e}")
                    continue
        
        return None
    
    async def reverse_geocode(
        self,
        lat: float,
        lon: float,
        provider: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Reverse geocode coordinates to address."""
        if provider and provider in self.providers:
            return await self.providers[provider].reverse_geocode(lat, lon)
        
        # Try providers in order
        for provider_name in ["nominatim", "mapbox", "google", "maptiler"]:
            if provider_name in self.providers:
                try:
                    result = await self.providers[provider_name].reverse_geocode(lat, lon)
                    if result:
                        return result
                except Exception as e:
                    logger.warning(f"Reverse geocoding failed with {provider_name}: {e}")
                    continue
        
        return None


class NominatimProvider(BaseConnector):
    """OpenStreetMap Nominatim geocoding (free)."""
    
    def __init__(self):
        super().__init__("https://nominatim.openstreetmap.org")
    
    async def geocode(self, address: str) -> Optional[Dict[str, Any]]:
        """Geocode address using Nominatim."""
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        
        results = await self.fetch("search", params=params)
        if results and len(results) > 0:
            result = results[0]
            return {
                "lat": float(result["lat"]),
                "lon": float(result["lon"]),
                "display_name": result.get("display_name"),
                "address": result.get("address", {}),
                "bbox": result.get("boundingbox"),
                "provider": "nominatim"
            }
        
        return None
    
    async def reverse_geocode(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Reverse geocode using Nominatim."""
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "addressdetails": 1
        }
        
        result = await self.fetch("reverse", params=params)
        if result:
            return {
                "lat": lat,
                "lon": lon,
                "display_name": result.get("display_name"),
                "address": result.get("address", {}),
                "provider": "nominatim"
            }
        
        return None


class MapboxProvider(BaseConnector):
    """Mapbox geocoding service."""
    
    def __init__(self, api_key: str):
        super().__init__("https://api.mapbox.com/geocoding/v5/mapbox.places")
        self.api_key = api_key
    
    async def geocode(self, address: str) -> Optional[Dict[str, Any]]:
        """Geocode using Mapbox."""
        endpoint = f"{address}.json"
        params = {
            "access_token": self.api_key,
            "limit": 1
        }
        
        result = await self.fetch(endpoint, params=params)
        if result and result.get("features"):
            feature = result["features"][0]
            return {
                "lat": feature["center"][1],
                "lon": feature["center"][0],
                "display_name": feature.get("place_name"),
                "address": self._parse_mapbox_context(feature.get("context", [])),
                "bbox": feature.get("bbox"),
                "provider": "mapbox"
            }
        
        return None
    
    async def reverse_geocode(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Reverse geocode using Mapbox."""
        endpoint = f"{lon},{lat}.json"
        params = {
            "access_token": self.api_key
        }
        
        result = await self.fetch(endpoint, params=params)
        if result and result.get("features"):
            feature = result["features"][0]
            return {
                "lat": lat,
                "lon": lon,
                "display_name": feature.get("place_name"),
                "address": self._parse_mapbox_context(feature.get("context", [])),
                "provider": "mapbox"
            }
        
        return None
    
    def _parse_mapbox_context(self, context: list) -> Dict[str, str]:
        """Parse Mapbox context into address components."""
        address = {}
        for item in context:
            if "postcode" in item["id"]:
                address["postcode"] = item["text"]
            elif "place" in item["id"]:
                address["city"] = item["text"]
            elif "region" in item["id"]:
                address["state"] = item["text"]
            elif "country" in item["id"]:
                address["country"] = item["text"]
        return address


class GoogleMapsProvider(BaseConnector):
    """Google Maps geocoding service."""
    
    def __init__(self, api_key: str):
        super().__init__("https://maps.googleapis.com/maps/api/geocode")
        self.api_key = api_key
    
    async def geocode(self, address: str) -> Optional[Dict[str, Any]]:
        """Geocode using Google Maps."""
        params = {
            "address": address,
            "key": self.api_key
        }
        
        result = await self.fetch("json", params=params)
        if result and result.get("results"):
            location = result["results"][0]
            geometry = location["geometry"]
            return {
                "lat": geometry["location"]["lat"],
                "lon": geometry["location"]["lng"],
                "display_name": location.get("formatted_address"),
                "address": self._parse_google_components(location.get("address_components", [])),
                "bbox": self._google_viewport_to_bbox(geometry.get("viewport")),
                "provider": "google"
            }
        
        return None
    
    async def reverse_geocode(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Reverse geocode using Google Maps."""
        params = {
            "latlng": f"{lat},{lon}",
            "key": self.api_key
        }
        
        result = await self.fetch("json", params=params)
        if result and result.get("results"):
            location = result["results"][0]
            return {
                "lat": lat,
                "lon": lon,
                "display_name": location.get("formatted_address"),
                "address": self._parse_google_components(location.get("address_components", [])),
                "provider": "google"
            }
        
        return None
    
    def _parse_google_components(self, components: list) -> Dict[str, str]:
        """Parse Google address components."""
        address = {}
        for component in components:
            types = component.get("types", [])
            if "street_number" in types:
                address["house_number"] = component["short_name"]
            elif "route" in types:
                address["road"] = component["short_name"]
            elif "locality" in types:
                address["city"] = component["short_name"]
            elif "administrative_area_level_1" in types:
                address["state"] = component["short_name"]
            elif "postal_code" in types:
                address["postcode"] = component["short_name"]
            elif "country" in types:
                address["country"] = component["short_name"]
        return address
    
    def _google_viewport_to_bbox(self, viewport: Optional[dict]) -> Optional[list]:
        """Convert Google viewport to bbox."""
        if not viewport:
            return None
        return [
            viewport["southwest"]["lng"],
            viewport["southwest"]["lat"],
            viewport["northeast"]["lng"],
            viewport["northeast"]["lat"]
        ]


class MapTilerProvider(BaseConnector):
    """MapTiler geocoding service."""
    
    def __init__(self, api_key: str):
        super().__init__("https://api.maptiler.com/geocoding")
        self.api_key = api_key
    
    async def geocode(self, address: str) -> Optional[Dict[str, Any]]:
        """Geocode using MapTiler."""
        endpoint = f"{address}.json"
        params = {
            "key": self.api_key,
            "limit": 1
        }
        
        result = await self.fetch(endpoint, params=params)
        if result and result.get("features"):
            feature = result["features"][0]
            return {
                "lat": feature["center"][1],
                "lon": feature["center"][0],
                "display_name": feature.get("place_name"),
                "bbox": feature.get("bbox"),
                "provider": "maptiler"
            }
        
        return None
    
    async def reverse_geocode(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Reverse geocode using MapTiler."""
        endpoint = f"{lon},{lat}.json"
        params = {
            "key": self.api_key
        }
        
        result = await self.fetch(endpoint, params=params)
        if result and result.get("features"):
            feature = result["features"][0]
            return {
                "lat": lat,
                "lon": lon,
                "display_name": feature.get("place_name"),
                "provider": "maptiler"
            }
        
        return None