"""
Base connector class for external data sources
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging
import asyncio
import aiohttp
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConnectorResponse:
    """Standard response format for all connectors"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class RateLimitInfo:
    """Rate limiting information"""
    requests_per_second: float
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    current_usage: int = 0
    reset_time: Optional[datetime] = None


class BaseConnector(ABC):
    """
    Base class for all external data connectors
    
    Provides common functionality for:
    - HTTP requests with retry logic
    - Rate limiting
    - Error handling and logging
    - Response caching
    - Authentication
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit: Optional[RateLimitInfo] = None
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit = rate_limit
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Request tracking
        self.request_count = 0
        self.last_request_time = None
        
        # Setup logging
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is available"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        headers = {
            "User-Agent": "PropertyAssessmentAPI/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    async def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        if not self.rate_limit:
            return
        
        now = datetime.utcnow()
        
        # Simple rate limiting implementation
        if self.last_request_time:
            time_since_last = (now - self.last_request_time).total_seconds()
            min_interval = 1.0 / self.rate_limit.requests_per_second
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
        
        self.last_request_time = now
        self.request_count += 1
    
    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> ConnectorResponse:
        """
        Make HTTP request with retry logic and error handling
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            params: Query parameters
            data: Request body data
            headers: Additional headers
            
        Returns:
            ConnectorResponse: Standardized response
        """
        await self._ensure_session()
        await self._check_rate_limit()
        
        # Prepare headers
        request_headers = self._get_auth_headers()
        if headers:
            request_headers.update(headers)
        
        # Build full URL
        if not url.startswith("http"):
            url = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
        
        start_time = datetime.utcnow()
        
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                async with self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=request_headers
                ) as response:
                    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                    
                    # Log response
                    self.logger.debug(f"Response: {response.status} in {response_time:.2f}ms")
                    
                    if response.status == 200:
                        try:
                            response_data = await response.json()
                            return ConnectorResponse(
                                success=True,
                                data=response_data,
                                response_time_ms=response_time,
                                metadata={
                                    "status_code": response.status,
                                    "attempt": attempt + 1
                                }
                            )
                        except Exception as e:
                            # Handle non-JSON responses
                            response_text = await response.text()
                            return ConnectorResponse(
                                success=True,
                                data=response_text,
                                response_time_ms=response_time,
                                metadata={
                                    "status_code": response.status,
                                    "attempt": attempt + 1,
                                    "content_type": response.content_type
                                }
                            )
                    
                    elif response.status in [429, 503]:  # Rate limited or service unavailable
                        if attempt < self.max_retries:
                            wait_time = 2 ** attempt  # Exponential backoff
                            self.logger.warning(f"Rate limited, waiting {wait_time} seconds")
                            await asyncio.sleep(wait_time)
                            continue
                    
                    # Handle error responses
                    try:
                        error_data = await response.json()
                        error_message = error_data.get("message", f"HTTP {response.status}")
                    except:
                        error_message = f"HTTP {response.status}: {response.reason}"
                    
                    return ConnectorResponse(
                        success=False,
                        error=error_message,
                        response_time_ms=response_time,
                        metadata={
                            "status_code": response.status,
                            "attempt": attempt + 1
                        }
                    )
            
            except asyncio.TimeoutError:
                self.logger.warning(f"Request timeout (attempt {attempt + 1})")
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                
                return ConnectorResponse(
                    success=False,
                    error="Request timeout",
                    metadata={"attempt": attempt + 1}
                )
            
            except Exception as e:
                self.logger.error(f"Request error (attempt {attempt + 1}): {str(e)}")
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                
                return ConnectorResponse(
                    success=False,
                    error=str(e),
                    metadata={"attempt": attempt + 1}
                )
        
        return ConnectorResponse(
            success=False,
            error="Max retries exceeded",
            metadata={"max_retries": self.max_retries}
        )
    
    @abstractmethod
    async def test_connection(self) -> ConnectorResponse:
        """
        Test the connection to the external service
        
        Returns:
            ConnectorResponse: Connection test result
        """
        pass
    
    @abstractmethod
    async def get_service_info(self) -> ConnectorResponse:
        """
        Get information about the external service
        
        Returns:
            ConnectorResponse: Service information
        """
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get connector usage statistics
        
        Returns:
            Dict[str, Any]: Usage statistics
        """
        return {
            "request_count": self.request_count,
            "last_request_time": self.last_request_time,
            "rate_limit": self.rate_limit.__dict__ if self.rate_limit else None,
            "session_active": self.session is not None and not self.session.closed
        }


class MockConnector(BaseConnector):
    """Mock connector for testing purposes"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mock_data = {}
    
    def set_mock_data(self, key: str, data: Any):
        """Set mock data for responses"""
        self.mock_data[key] = data
    
    async def test_connection(self) -> ConnectorResponse:
        """Mock connection test"""
        return ConnectorResponse(
            success=True,
            data={"status": "connected", "service": "mock"}
        )
    
    async def get_service_info(self) -> ConnectorResponse:
        """Mock service info"""
        return ConnectorResponse(
            success=True,
            data={
                "service_name": "Mock Connector",
                "version": "1.0.0",
                "features": ["testing", "development"]
            }
        )
    
    async def get_mock_response(self, key: str) -> ConnectorResponse:
        """Get mock response data"""
        if key in self.mock_data:
            return ConnectorResponse(
                success=True,
                data=self.mock_data[key]
            )
        else:
            return ConnectorResponse(
                success=False,
                error=f"Mock data not found for key: {key}"
            )