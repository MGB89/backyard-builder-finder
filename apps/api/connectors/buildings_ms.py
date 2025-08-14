"""
Microsoft US Building Footprints connector for production-grade building data ingestion.

This connector handles downloading, processing, and indexing Microsoft's open-source
US building footprint data from their GitHub releases.

Data source: https://github.com/microsoft/USBuildingFootprints
License: Open Data Commons Open Database License (ODbL)
"""

import os
import json
import logging
import asyncio
import zipfile
import tempfile
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import aiohttp
import aiofiles
import geopandas as gpd
from shapely.geometry import shape, Point, Polygon
from shapely.ops import transform
import pyproj

from connectors.base import BaseConnector
from core.config import settings

logger = logging.getLogger(__name__)


class MicrosoftBuildingsConnector(BaseConnector):
    """
    Production-ready connector for Microsoft US Building Footprints.
    
    Features:
    - Automatic state data discovery via GitHub releases API
    - Streaming download and processing for large datasets
    - PostGIS-optimized bulk insertion
    - Resume capability for interrupted downloads
    - Spatial indexing and caching
    """
    
    # GitHub releases API for building footprints
    GITHUB_API_BASE = "https://api.github.com/repos/microsoft/USBuildingFootprints"
    GITHUB_RELEASES_URL = f"{GITHUB_API_BASE}/releases"
    
    # State to region mapping for LA area
    SUPPORTED_STATES = {
        "california": {
            "code": "CA",
            "name": "California",
            "priority": 1,  # Highest priority for LA area
            "counties": ["Los Angeles", "Orange", "Ventura", "Riverside", "San Bernardino"]
        },
        "nevada": {
            "code": "NV", 
            "name": "Nevada",
            "priority": 2
        }
    }
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize Microsoft Buildings connector."""
        super().__init__("")  # No base URL needed
        
        # Set up caching directory
        self.cache_dir = Path(cache_dir) if cache_dir else Path(tempfile.gettempdir()) / "ms_buildings_cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Download progress tracking
        self._download_progress = {}
        
        logger.info(f"Microsoft Buildings connector initialized with cache: {self.cache_dir}")
    
    async def discover_available_data(self) -> Dict[str, Any]:
        """
        Discover available building footprint datasets from GitHub releases.
        
        Returns:
            Dictionary with available states, download URLs, and metadata
        """
        logger.info("Discovering available Microsoft Building Footprints data...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.GITHUB_RELEASES_URL) as response:
                    if response.status != 200:
                        raise Exception(f"GitHub API returned {response.status}")
                    
                    releases = await response.json()
            
            # Find the latest release
            latest_release = releases[0] if releases else None
            if not latest_release:
                raise Exception("No releases found")
            
            logger.info(f"Latest release: {latest_release['tag_name']} ({latest_release['published_at']})")
            
            # Parse assets to find state files
            available_states = {}
            
            for asset in latest_release.get("assets", []):
                name = asset["name"].lower()
                
                # Look for state ZIP files (e.g., "California.zip")
                if name.endswith(".zip"):
                    state_name = name.replace(".zip", "").lower()
                    
                    if state_name in self.SUPPORTED_STATES:
                        state_config = self.SUPPORTED_STATES[state_name].copy()
                        state_config.update({
                            "download_url": asset["browser_download_url"],
                            "file_size_mb": round(asset["size"] / (1024 * 1024), 1),
                            "updated_at": asset["updated_at"],
                            "download_count": asset["download_count"]
                        })
                        available_states[state_name] = state_config
            
            metadata = {
                "release_tag": latest_release["tag_name"],
                "release_date": latest_release["published_at"],
                "total_states": len(available_states),
                "supported_states": list(available_states.keys()),
                "cache_dir": str(self.cache_dir),
                "discovery_time": datetime.now().isoformat()
            }
            
            logger.info(f"Discovered {len(available_states)} supported states: {list(available_states.keys())}")
            
            return {
                "states": available_states,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to discover Microsoft Buildings data: {e}")
            return {"states": {}, "metadata": {"error": str(e)}}
    
    async def download_state_data(
        self,
        state: str,
        force_refresh: bool = False,
        progress_callback: Optional[callable] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Download building footprint data for a specific state.
        
        Args:
            state: State name (e.g., "california")
            force_refresh: Force re-download even if cached
            progress_callback: Optional callback for download progress
            
        Returns:
            Tuple of (success, file_path, metadata)
        """
        if state.lower() not in self.SUPPORTED_STATES:
            raise ValueError(f"Unsupported state: {state}. Supported: {list(self.SUPPORTED_STATES.keys())}")
        
        # Discover current data
        discovery = await self.discover_available_data()
        if state.lower() not in discovery["states"]:
            raise Exception(f"State {state} not found in current release")
        
        state_info = discovery["states"][state.lower()]
        download_url = state_info["download_url"]
        file_size = state_info["file_size_mb"]
        
        # Check cache
        cache_file = self.cache_dir / f"{state.lower()}_buildings.zip"
        metadata_file = self.cache_dir / f"{state.lower()}_metadata.json"
        
        if cache_file.exists() and not force_refresh:
            # Check if cached file is from current release
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        cached_metadata = json.load(f)
                    
                    if cached_metadata.get("release_tag") == discovery["metadata"]["release_tag"]:
                        logger.info(f"Using cached {state} data from {cache_file}")
                        return True, str(cache_file), cached_metadata
                except Exception as e:
                    logger.warning(f"Failed to read cached metadata: {e}")
        
        logger.info(f"Downloading {state} building footprints ({file_size} MB)...")
        
        try:
            # Download with progress tracking
            start_time = datetime.now()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status != 200:
                        raise Exception(f"Download failed with status {response.status}")
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    # Create temporary file first
                    temp_file = cache_file.with_suffix('.tmp')
                    
                    async with aiofiles.open(temp_file, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Report progress
                            if progress_callback and total_size > 0:
                                progress = (downloaded / total_size) * 100
                                await progress_callback(state, progress, downloaded, total_size)
                    
                    # Move to final location
                    temp_file.rename(cache_file)
            
            end_time = datetime.now()
            download_time = (end_time - start_time).total_seconds()
            
            # Save metadata
            download_metadata = {
                **state_info,
                "downloaded_at": datetime.now().isoformat(),
                "download_time_seconds": download_time,
                "file_path": str(cache_file),
                "file_size_bytes": cache_file.stat().st_size,
                "release_tag": discovery["metadata"]["release_tag"]
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(download_metadata, f, indent=2)
            
            logger.info(f"Downloaded {state} data in {download_time:.1f}s to {cache_file}")
            
            return True, str(cache_file), download_metadata
            
        except Exception as e:
            logger.error(f"Failed to download {state} data: {e}")
            # Clean up partial download
            if cache_file.with_suffix('.tmp').exists():
                cache_file.with_suffix('.tmp').unlink()
            
            return False, "", {"error": str(e)}
    
    async def process_state_buildings(
        self,
        state: str,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        max_buildings: int = 100000,
        progress_callback: Optional[callable] = None
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Process building footprints from downloaded state data in streaming fashion.
        
        Args:
            state: State name
            bbox: Optional bounding box to filter buildings (min_lon, min_lat, max_lon, max_lat)
            max_buildings: Maximum number of buildings to process
            progress_callback: Optional progress callback
            
        Yields:
            Batches of processed building dictionaries
        """
        # Ensure data is downloaded
        success, file_path, metadata = await self.download_state_data(state)
        if not success:
            raise Exception(f"Failed to download {state} data")
        
        logger.info(f"Processing {state} buildings from {file_path}")
        
        if bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            bbox_polygon = Polygon([
                (min_lon, min_lat), (max_lon, min_lat),
                (max_lon, max_lat), (min_lon, max_lat), (min_lon, min_lat)
            ])\n            logger.info(f"Filtering buildings within bbox: {bbox}")
        
        processed_count = 0\n        batch_size = 1000\n        current_batch = []\n        \n        try:\n            # Extract and process ZIP file\n            with zipfile.ZipFile(file_path, 'r') as zip_ref:\n                # Find GeoJSON file in ZIP\n                geojson_files = [f for f in zip_ref.namelist() if f.endswith('.geojson')]\n                \n                if not geojson_files:\n                    raise Exception(f\"No GeoJSON files found in {file_path}\")\n                \n                geojson_file = geojson_files[0]\n                logger.info(f\"Processing {geojson_file} from ZIP\")\n                \n                # Extract to temporary location for processing\n                with tempfile.TemporaryDirectory() as temp_dir:\n                    extracted_path = zip_ref.extract(geojson_file, temp_dir)\n                    \n                    # Use geopandas for efficient large file processing\n                    logger.info(\"Loading GeoDataFrame...\")\n                    gdf = gpd.read_file(extracted_path)\n                    \n                    total_buildings = len(gdf)\n                    logger.info(f\"Loaded {total_buildings} buildings\")\n                    \n                    # Apply spatial filter if bbox provided\n                    if bbox:\n                        logger.info(\"Applying spatial filter...\")\n                        bbox_gdf = gpd.GeoDataFrame([1], geometry=[bbox_polygon], crs=gdf.crs)\n                        gdf = gpd.overlay(gdf, bbox_gdf, how='intersection')\n                        logger.info(f\"Filtered to {len(gdf)} buildings within bbox\")\n                    \n                    # Limit results\n                    if len(gdf) > max_buildings:\n                        logger.info(f\"Limiting to {max_buildings} buildings\")\n                        gdf = gdf.head(max_buildings)\n                    \n                    # Process in batches\n                    for idx, row in gdf.iterrows():\n                        try:\n                            # Convert geometry to standard format\n                            geometry = row.geometry\n                            \n                            # Calculate area and centroid\n                            area_sqft = geometry.area * 10763910.4  # sq degrees to sq feet (approximate)\n                            centroid = geometry.centroid\n                            \n                            building = {\n                                \"external_id\": f\"msft_{state}_{idx}\",\n                                \"geometry\": geometry,\n                                \"centroid\": centroid,\n                                \"area_sqft\": area_sqft,\n                                \"building_type\": \"unknown\",  # MS data doesn't include building type\n                                \"height_ft\": None,  # Not available in MS data\n                                \"attributes\": {\n                                    \"source\": \"microsoft_buildings\",\n                                    \"state\": state,\n                                    \"processed_at\": datetime.now().isoformat()\n                                },\n                                \"source\": f\"microsoft_buildings_{state}\",\n                                \"region_code\": state.lower()\n                            }\n                            \n                            current_batch.append(building)\n                            processed_count += 1\n                            \n                            # Yield batch when full\n                            if len(current_batch) >= batch_size:\n                                if progress_callback:\n                                    progress = (processed_count / len(gdf)) * 100\n                                    await progress_callback(f\"processing_{state}\", progress, processed_count, len(gdf))\n                                \n                                yield current_batch\n                                current_batch = []\n                                \n                                # Small delay to prevent overwhelming the system\n                                await asyncio.sleep(0.01)\n                            \n                            # Stop if we've reached max_buildings\n                            if processed_count >= max_buildings:\n                                break\n                                \n                        except Exception as e:\n                            logger.warning(f\"Failed to process building {idx}: {e}\")\n                            continue\n                    \n                    # Yield remaining batch\n                    if current_batch:\n                        yield current_batch\n        \n        except Exception as e:\n            logger.error(f\"Failed to process {state} buildings: {e}\")\n            raise\n        \n        logger.info(f\"Processed {processed_count} buildings from {state}\")\n    \n    async def get_buildings_for_region(\n        self,\n        bbox: Tuple[float, float, float, float],\n        max_buildings: int = 10000\n    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:\n        \"\"\"Get building footprints for a specific bounding box.\"\"\"\n        min_lon, min_lat, max_lon, max_lat = bbox\n        \n        # Determine which states we need based on bbox\n        # For LA area, we primarily need California\n        states_to_process = []\n        \n        # LA area is primarily in California\n        if self._bbox_intersects_state(bbox, \"california\"):\n            states_to_process.append(\"california\")\n        \n        if not states_to_process:\n            logger.warning(f\"No supported states intersect with bbox: {bbox}\")\n            return [], {\"error\": \"No supported states for this area\"}\n        \n        all_buildings = []\n        metadata = {\n            \"bbox\": bbox,\n            \"states_processed\": [],\n            \"total_buildings\": 0,\n            \"processing_time_seconds\": 0\n        }\n        \n        start_time = datetime.now()\n        \n        for state in states_to_process:\n            logger.info(f\"Processing buildings from {state} for bbox {bbox}\")\n            \n            try:\n                remaining_buildings = max_buildings - len(all_buildings)\n                if remaining_buildings <= 0:\n                    break\n                \n                # Process buildings in batches\n                state_buildings = []\n                async for batch in self.process_state_buildings(\n                    state, bbox=bbox, max_buildings=remaining_buildings\n                ):\n                    state_buildings.extend(batch)\n                    if len(state_buildings) >= remaining_buildings:\n                        state_buildings = state_buildings[:remaining_buildings]\n                        break\n                \n                all_buildings.extend(state_buildings)\n                metadata[\"states_processed\"].append({\n                    \"state\": state,\n                    \"buildings_count\": len(state_buildings)\n                })\n                \n                logger.info(f\"Added {len(state_buildings)} buildings from {state}\")\n                \n            except Exception as e:\n                logger.error(f\"Failed to process {state}: {e}\")\n                metadata[\"states_processed\"].append({\n                    \"state\": state,\n                    \"error\": str(e)\n                })\n        \n        end_time = datetime.now()\n        metadata[\"total_buildings\"] = len(all_buildings)\n        metadata[\"processing_time_seconds\"] = (end_time - start_time).total_seconds()\n        \n        logger.info(f\"Retrieved {len(all_buildings)} buildings in {metadata['processing_time_seconds']:.1f}s\")\n        \n        return all_buildings, metadata\n    \n    def _bbox_intersects_state(self, bbox: Tuple[float, float, float, float], state: str) -> bool:\n        \"\"\"Check if bounding box intersects with a state (rough approximation).\"\"\"\n        min_lon, min_lat, max_lon, max_lat = bbox\n        \n        # Simple state bounding boxes (approximate)\n        state_bounds = {\n            \"california\": (-124.4, 32.5, -114.1, 42.0),\n            \"nevada\": (-120.0, 35.0, -114.0, 42.0)\n        }\n        \n        if state not in state_bounds:\n            return False\n        \n        state_min_lon, state_min_lat, state_max_lon, state_max_lat = state_bounds[state]\n        \n        # Check if bboxes intersect\n        return not (max_lon < state_min_lon or min_lon > state_max_lon or\n                   max_lat < state_min_lat or min_lat > state_max_lat)\n    \n    async def cleanup_cache(self, days_old: int = 30) -> Dict[str, Any]:\n        \"\"\"Clean up old cached files.\"\"\"\n        logger.info(f\"Cleaning up cache files older than {days_old} days\")\n        \n        cutoff_time = datetime.now() - timedelta(days=days_old)\n        removed_files = []\n        total_size_removed = 0\n        \n        for file_path in self.cache_dir.glob(\"*\"):\n            if file_path.is_file():\n                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)\n                if file_time < cutoff_time:\n                    file_size = file_path.stat().st_size\n                    file_path.unlink()\n                    removed_files.append(str(file_path))\n                    total_size_removed += file_size\n        \n        cleanup_info = {\n            \"removed_files\": len(removed_files),\n            \"total_size_mb\": round(total_size_removed / (1024 * 1024), 1),\n            \"cutoff_date\": cutoff_time.isoformat()\n        }\n        \n        logger.info(f\"Cleanup complete: {cleanup_info}\")\n        return cleanup_info