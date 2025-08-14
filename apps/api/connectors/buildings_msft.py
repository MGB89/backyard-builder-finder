"""
Microsoft Building Footprints connector for building outline data
"""

from typing import Optional, Dict, Any, List
import logging

from .base import BaseConnector, ConnectorResponse, RateLimitInfo
from core.config import settings

logger = logging.getLogger(__name__)


class MicrosoftBuildingConnector(BaseConnector):
    """
    Connector for Microsoft Building Footprints data
    Provides access to AI-generated building outlines from satellite imagery
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        use_github_releases: bool = True,
        **kwargs
    ):
        # Microsoft Building Footprints can be accessed via:
        # 1. GitHub releases (static data)
        # 2. Azure Open Datasets (programmatic access)
        # 3. Direct download from Microsoft
        
        self.use_github_releases = use_github_releases
        
        if use_github_releases:
            # GitHub releases API for building footprints
            base_url = "https://api.github.com/repos/microsoft/USBuildingFootprints"
            rate_limit = RateLimitInfo(
                requests_per_second=10,
                requests_per_minute=600,
                requests_per_hour=36000,
                requests_per_day=864000
            )
        else:
            # Azure Open Datasets API
            base_url = "https://azure.microsoft.com/en-us/services/open-datasets"
            rate_limit = RateLimitInfo(
                requests_per_second=5,
                requests_per_minute=300,
                requests_per_hour=18000,
                requests_per_day=432000
            )
        
        super().__init__(
            api_key=api_key or settings.MICROSOFT_BUILDING_API_KEY,
            base_url=base_url,
            rate_limit=rate_limit,
            **kwargs
        )
        
        # State/region codes for building footprint data
        self.available_states = {
            "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
            "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
            "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
            "maine", "maryland", "massachusetts", "michigan", "minnesota",
            "mississippi", "missouri", "montana", "nebraska", "nevada",
            "newhampshire", "newjersey", "newmexico", "newyork", "northcarolina",
            "northdakota", "ohio", "oklahoma", "oregon", "pennsylvania",
            "rhodeisland", "southcarolina", "southdakota", "tennessee", "texas",
            "utah", "vermont", "virginia", "washington", "westvirginia",
            "wisconsin", "wyoming"
        }
    
    async def test_connection(self) -> ConnectorResponse:
        """Test the Microsoft Building Footprints service connection"""
        try:
            if self.use_github_releases:
                # Test GitHub API connection
                response = await self._make_request("GET", "/releases/latest")
                
                if response.success:
                    release_info = response.data
                    return ConnectorResponse(
                        success=True,
                        data={
                            "status": "connected",
                            "service": "Microsoft Building Footprints (GitHub)",
                            "latest_release": release_info.get("tag_name"),
                            "published_at": release_info.get("published_at")
                        }
                    )
                else:
                    return response
            else:
                # Test Azure Open Datasets connection
                return ConnectorResponse(
                    success=True,
                    data={
                        "status": "connected",
                        "service": "Microsoft Building Footprints (Azure)",
                        "note": "Azure Open Datasets connection test placeholder"
                    }
                )
        
        except Exception as e:
            return ConnectorResponse(
                success=False,
                error=f"Connection test failed: {str(e)}"
            )
    
    async def get_service_info(self) -> ConnectorResponse:
        """Get Microsoft Building Footprints service information"""
        return ConnectorResponse(
            success=True,
            data={
                "service_name": "Microsoft Building Footprints",
                "description": "Computer generated building footprints for the United States",
                "data_source": "Satellite and aerial imagery",
                "coverage": "United States (all 50 states + DC)",
                "format": "GeoJSON",
                "accuracy": "Estimated 99.3% precision and 93.5% recall",
                "last_updated": "2018-2023 (varies by state)",
                "total_buildings": "Over 130 million buildings",
                "license": "Open Data Commons Open Database License (ODbL)",
                "github_repo": "https://github.com/microsoft/USBuildingFootprints",
                "available_states": list(self.available_states),
                "use_github_releases": self.use_github_releases
            }
        )
    
    async def get_available_releases(self) -> ConnectorResponse:
        """Get available data releases"""
        try:
            if not self.use_github_releases:
                return ConnectorResponse(
                    success=False,
                    error="Release information only available for GitHub data source"
                )
            
            response = await self._make_request("GET", "/releases")
            
            if not response.success:
                return response
            
            releases = response.data
            release_info = []
            
            for release in releases[:10]:  # Limit to last 10 releases
                release_info.append({
                    "tag_name": release.get("tag_name"),
                    "name": release.get("name"),
                    "published_at": release.get("published_at"),
                    "body": release.get("body", "")[:200] + "..." if len(release.get("body", "")) > 200 else release.get("body", ""),
                    "asset_count": len(release.get("assets", []))
                })
            
            return ConnectorResponse(
                success=True,
                data={
                    "releases": release_info,
                    "total_releases": len(releases)
                }
            )
        
        except Exception as e:
            return ConnectorResponse(
                success=False,
                error=f"Failed to get releases: {str(e)}"
            )
    
    async def get_state_data_info(self, state: str) -> ConnectorResponse:
        """
        Get information about building footprint data for a specific state
        
        Args:
            state: State name (e.g., 'california', 'texas')
            
        Returns:
            ConnectorResponse: State data information
        """
        try:
            state_lower = state.lower().replace(" ", "")
            
            if state_lower not in self.available_states:
                return ConnectorResponse(
                    success=False,
                    error=f"State '{state}' not available. Available states: {list(self.available_states)}"
                )
            
            if self.use_github_releases:
                # Get latest release to find state-specific assets
                response = await self._make_request("GET", "/releases/latest")
                
                if not response.success:
                    return response
                
                release = response.data
                assets = release.get("assets", [])
                
                # Find assets for the specific state
                state_assets = [
                    asset for asset in assets
                    if state_lower in asset.get("name", "").lower()
                ]
                
                if not state_assets:
                    return ConnectorResponse(
                        success=False,
                        error=f"No building footprint data found for {state}"
                    )
                
                return ConnectorResponse(
                    success=True,
                    data={
                        "state": state,
                        "assets": [
                            {
                                "name": asset.get("name"),
                                "size": asset.get("size"),
                                "download_url": asset.get("browser_download_url"),
                                "content_type": asset.get("content_type"),
                                "updated_at": asset.get("updated_at")
                            }
                            for asset in state_assets
                        ],
                        "release_info": {
                            "tag_name": release.get("tag_name"),
                            "published_at": release.get("published_at")
                        }
                    }
                )
            else:
                # Azure Open Datasets implementation would go here
                return ConnectorResponse(
                    success=True,
                    data={
                        "state": state,
                        "message": "Azure Open Datasets implementation not yet available",
                        "suggestion": "Use GitHub releases mode for data access"
                    }
                )
        
        except Exception as e:
            return ConnectorResponse(
                success=False,
                error=f"Failed to get state data info: {str(e)}"
            )
    
    async def get_buildings_by_bounds(
        self,
        min_longitude: float,
        min_latitude: float,
        max_longitude: float,
        max_latitude: float,
        state: Optional[str] = None
    ) -> ConnectorResponse:
        """
        Get building footprints within bounding box
        
        Note: This is a placeholder implementation. The actual implementation
        would require downloading and processing the GeoJSON files, which is
        typically done as a batch process rather than real-time API calls.
        
        Args:
            min_longitude: Minimum longitude
            min_latitude: Minimum latitude
            max_longitude: Maximum longitude
            max_latitude: Maximum latitude
            state: State to search in (optional)
            
        Returns:
            ConnectorResponse: Building footprints within bounds
        """
        return ConnectorResponse(
            success=False,
            error="Real-time building footprint queries not implemented. "
                  "Microsoft Building Footprints data should be downloaded "
                  "and processed offline, then stored in a local database "
                  "for efficient querying."
        )
    
    async def get_buildings_by_point(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float = 100,
        state: Optional[str] = None
    ) -> ConnectorResponse:
        """
        Get building footprints near a point
        
        Note: This is a placeholder implementation. See get_buildings_by_bounds
        for explanation.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            radius_meters: Search radius in meters
            state: State to search in (optional)
            
        Returns:
            ConnectorResponse: Building footprints near point
        """
        return ConnectorResponse(
            success=False,
            error="Real-time building footprint queries not implemented. "
                  "Microsoft Building Footprints data should be downloaded "
                  "and processed offline, then stored in a local database "
                  "for efficient querying."
        )
    
    async def download_state_data(
        self,
        state: str,
        download_path: str = "./downloads/building_footprints"
    ) -> ConnectorResponse:
        """
        Download building footprint data for a specific state
        
        Args:
            state: State name
            download_path: Local path to save downloaded files
            
        Returns:
            ConnectorResponse: Download information
        """
        try:
            # Get state data info first
            state_info_response = await self.get_state_data_info(state)
            
            if not state_info_response.success:
                return state_info_response
            
            state_info = state_info_response.data
            assets = state_info.get("assets", [])
            
            if not assets:
                return ConnectorResponse(
                    success=False,
                    error=f"No downloadable assets found for {state}"
                )
            
            # This would implement actual file download logic
            # For now, return download URLs and instructions
            download_info = {
                "state": state,
                "download_instructions": f"Download files to {download_path}",
                "files_to_download": [
                    {
                        "filename": asset["name"],
                        "url": asset["download_url"],
                        "size_bytes": asset["size"]
                    }
                    for asset in assets
                ],
                "total_size_bytes": sum(asset["size"] for asset in assets),
                "estimated_download_time": "Varies based on connection speed"
            }
            
            return ConnectorResponse(
                success=True,
                data=download_info,
                metadata={
                    "note": "Actual download implementation required",
                    "suggestion": "Use tools like wget or curl to download the files"
                }
            )
        
        except Exception as e:
            return ConnectorResponse(
                success=False,
                error=f"Download preparation failed: {str(e)}"
            )
    
    def get_processing_recommendations(self) -> Dict[str, Any]:
        """
        Get recommendations for processing Microsoft Building Footprints data
        
        Returns:
            Dict[str, Any]: Processing recommendations
        """
        return {
            "data_format": "GeoJSON",
            "coordinate_system": "WGS84 (EPSG:4326)",
            "storage_recommendations": [
                "Use PostGIS database for spatial indexing",
                "Create spatial indexes on geometry columns",
                "Consider partitioning by state or county",
                "Use GIST indexes for efficient spatial queries"
            ],
            "processing_steps": [
                "1. Download state-specific GeoJSON files",
                "2. Validate geometry and fix any topology issues",
                "3. Load into spatial database with appropriate indexes",
                "4. Create aggregation tables for faster queries",
                "5. Set up regular update process for new releases"
            ],
            "performance_tips": [
                "Use spatial clustering for frequently queried areas",
                "Pre-compute building counts and areas by region",
                "Cache common query results",
                "Use geometry simplification for overview queries"
            ],
            "data_quality": {
                "precision": "99.3%",
                "recall": "93.5%",
                "notes": "Accuracy varies by region and building type"
            }
        }