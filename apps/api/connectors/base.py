"""Base connector class with retry logic and rate limiting."""
import asyncio
from typing import Any, Dict, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
from datetime import datetime, timedelta
import hashlib
import json

from core.config import settings
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class BaseConnector:
    """Base class for external service connectors."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
        self.cache = None
        self._init_cache()
    
    def _init_cache(self):
        """Initialize Redis cache if available."""
        try:
            self.cache = redis.from_url(settings.REDIS_URL)
        except Exception as e:
            logger.warning(f"Redis cache unavailable: {e}")
            self.cache = None
    
    def _get_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key from endpoint and params."""
        params_str = json.dumps(params, sort_keys=True)
        key_data = f"{self.base_url}:{endpoint}:{params_str}"
        return f"connector:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def _get_cached(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available."""
        if not self.cache:
            return None
        
        try:
            cached = await self.cache.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.debug(f"Cache get error: {e}")
        
        return None
    
    async def _set_cache(self, cache_key: str, data: Dict[str, Any], ttl: int = 3600):
        """Cache response data."""
        if not self.cache:
            return
        
        try:
            await self.cache.setex(
                cache_key,
                ttl,
                json.dumps(data)
            )
        except Exception as e:
            logger.debug(f"Cache set error: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def fetch(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        cache_ttl: int = 3600
    ) -> Dict[str, Any]:
        """Fetch data from external service with retry and caching."""
        # Check cache first
        if use_cache and method == "GET":
            cache_key = self._get_cache_key(endpoint, params or {})
            cached = await self._get_cached(cache_key)
            if cached:
                logger.debug(f"Cache hit for {endpoint}")
                return cached
        
        # Build request
        url = f"{self.base_url}/{endpoint}"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Make request
        try:
            if method == "GET":
                response = await self.client.get(url, params=params, headers=headers)
            elif method == "POST":
                response = await self.client.post(url, json=data, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            result = response.json()
            
            # Cache successful response
            if use_cache and method == "GET":
                await self._set_cache(cache_key, result, cache_ttl)
            
            return result
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limited
                retry_after = e.response.headers.get("Retry-After", "60")
                logger.warning(f"Rate limited, retry after {retry_after}s")
                await asyncio.sleep(int(retry_after))
                raise  # Let tenacity retry
            else:
                logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
                raise
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
    
    async def close(self):
        """Close connections."""
        await self.client.aclose()
        if self.cache:
            await self.cache.close()