"""
RESO (Real Estate Standards Organization) MLS connector for listing data
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timedelta
import base64

from .base import BaseConnector, ConnectorResponse, RateLimitInfo
from core.config import settings

logger = logging.getLogger(__name__)


class RESOConnector(BaseConnector):
    """
    Connector for RESO-compliant MLS systems
    Supports RESO Data Dictionary and Web API standards
    """
    
    def __init__(
        self,
        login_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        api_version: str = "2.0.0",
        **kwargs
    ):
        self.login_url = login_url or settings.RESO_LOGIN_URL
        self.client_id = client_id or settings.RESO_CLIENT_ID
        self.client_secret = client_secret or settings.RESO_CLIENT_SECRET
        self.api_version = api_version
        
        # RESO standard rate limits (varies by MLS)
        rate_limit = RateLimitInfo(
            requests_per_second=2,
            requests_per_minute=120,
            requests_per_hour=7200,
            requests_per_day=172800
        )
        
        super().__init__(
            base_url=self.login_url,
            rate_limit=rate_limit,
            **kwargs
        )
        
        # Authentication tokens
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
        # RESO endpoints (discovered from metadata)
        self.metadata_url = None
        self.data_url = None
        
        # Standard RESO resources
        self.standard_resources = [
            "Property", "Member", "Office", "Listing", "Media",
            "LookupResource", "PropertySubType", "PropertyType"
        ]
    
    async def test_connection(self) -> ConnectorResponse:
        """Test the RESO MLS connection"""
        try:
            # Test authentication
            auth_response = await self.authenticate()
            
            if not auth_response.success:
                return ConnectorResponse(
                    success=False,
                    error=f"Authentication failed: {auth_response.error}"
                )
            
            # Test metadata discovery
            metadata_response = await self.discover_metadata()
            
            if metadata_response.success:
                return ConnectorResponse(
                    success=True,
                    data={
                        "status": "connected",
                        "service": "RESO MLS",
                        "api_version": self.api_version,
                        "authenticated": True,
                        "metadata_available": True
                    }
                )
            else:
                return ConnectorResponse(
                    success=False,
                    error=f"Metadata discovery failed: {metadata_response.error}"
                )
        
        except Exception as e:
            return ConnectorResponse(
                success=False,
                error=f"Connection test failed: {str(e)}"
            )
    
    async def get_service_info(self) -> ConnectorResponse:
        """Get RESO service information"""
        return ConnectorResponse(
            success=True,
            data={
                "service_name": "RESO MLS Connector",
                "description": "Real Estate Standards Organization compliant MLS access",
                "standards": ["RESO Data Dictionary", "RESO Web API"],
                "api_version": self.api_version,
                "authentication": "OAuth 2.0",
                "supported_resources": self.standard_resources,
                "rate_limit": self.rate_limit.__dict__ if self.rate_limit else None
            }
        )
    
    async def authenticate(self) -> ConnectorResponse:
        """
        Authenticate with RESO MLS using OAuth 2.0
        
        Returns:
            ConnectorResponse: Authentication result
        """
        try:
            if not all([self.login_url, self.client_id, self.client_secret]):
                return ConnectorResponse(
                    success=False,
                    error="Missing required authentication parameters"
                )
            
            # Prepare OAuth 2.0 client credentials request
            auth_string = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()
            
            headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "grant_type": "client_credentials",
                "scope": "api"
            }
            
            response = await self._make_request(
                "POST",
                "/oauth2/token",
                data=data,
                headers=headers
            )
            
            if not response.success:
                return response
            
            token_data = response.data
            
            self.access_token = token_data.get("access_token")
            self.refresh_token = token_data.get("refresh_token")
            
            # Calculate token expiration
            expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            return ConnectorResponse(
                success=True,
                data={
                    "authenticated": True,
                    "token_type": token_data.get("token_type", "Bearer"),
                    "expires_in": expires_in,
                    "expires_at": self.token_expires_at.isoformat()
                }
            )
        
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"Authentication failed: {str(e)}"
            )
    
    async def discover_metadata(self) -> ConnectorResponse:
        """
        Discover RESO service metadata and endpoints
        
        Returns:
            ConnectorResponse: Metadata discovery result
        """
        try:
            if not await self._ensure_authenticated():
                return ConnectorResponse(
                    success=False,
                    error="Authentication required for metadata discovery"
                )
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
            
            # Try to discover metadata endpoint
            response = await self._make_request(
                "GET",
                "/$metadata",
                headers=headers
            )
            
            if response.success:
                # Parse metadata to discover endpoints
                metadata = response.data
                
                # Extract service URLs (this would need proper OData metadata parsing)
                self.metadata_url = f"{self.base_url}/$metadata"
                self.data_url = self.base_url.replace("/oauth2", "")
                
                return ConnectorResponse(
                    success=True,
                    data={
                        "metadata_url": self.metadata_url,
                        "data_url": self.data_url,
                        "metadata": metadata
                    }
                )
            else:
                return response
        
        except Exception as e:
            logger.error(f"Metadata discovery error: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"Metadata discovery failed: {str(e)}"
            )
    
    async def get_properties(
        self,
        filters: Optional[Dict[str, Any]] = None,
        select_fields: Optional[List[str]] = None,
        max_results: int = 100
    ) -> ConnectorResponse:
        """
        Get property listings from RESO MLS
        
        Args:
            filters: OData filter conditions
            select_fields: Specific fields to retrieve
            max_results: Maximum number of results
            
        Returns:
            ConnectorResponse: Property listings
        """
        try:
            if not await self._ensure_authenticated():
                return ConnectorResponse(
                    success=False,
                    error="Authentication required"
                )
            
            # Build OData query parameters
            params = {
                "$top": str(max_results),
                "$count": "true"
            }
            
            if select_fields:
                params["$select"] = ",".join(select_fields)
            
            if filters:
                filter_conditions = []
                for field, value in filters.items():
                    if isinstance(value, str):
                        filter_conditions.append(f"{field} eq '{value}'")
                    else:
                        filter_conditions.append(f"{field} eq {value}")
                
                if filter_conditions:
                    params["$filter"] = " and ".join(filter_conditions)
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
            
            response = await self._make_request(
                "GET",
                "/Property",
                params=params,
                headers=headers
            )
            
            if not response.success:
                return response
            
            data = response.data
            properties = data.get("value", [])
            
            # Standardize property data
            standardized_properties = [
                self._standardize_property_data(prop) for prop in properties
            ]
            
            return ConnectorResponse(
                success=True,
                data={
                    "properties": standardized_properties,
                    "total_count": data.get("@odata.count", len(properties)),
                    "has_more": len(properties) >= max_results
                },
                metadata={
                    "query_params": params,
                    "result_count": len(properties)
                }
            )
        
        except Exception as e:
            logger.error(f"Error getting properties: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"Failed to get properties: {str(e)}"
            )
    
    async def get_property_by_mls_number(
        self,
        mls_number: str
    ) -> ConnectorResponse:
        """
        Get specific property by MLS number
        
        Args:
            mls_number: MLS listing number
            
        Returns:
            ConnectorResponse: Property details
        """
        try:
            filters = {"ListingId": mls_number}
            response = await self.get_properties(filters=filters, max_results=1)
            
            if not response.success:
                return response
            
            properties = response.data.get("properties", [])
            
            if not properties:
                return ConnectorResponse(
                    success=False,
                    error=f"No property found with MLS number: {mls_number}"
                )
            
            return ConnectorResponse(
                success=True,
                data=properties[0],
                metadata={"mls_number": mls_number}
            )
        
        except Exception as e:
            logger.error(f"Error getting property by MLS number: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"Failed to get property: {str(e)}"
            )
    
    async def search_properties(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        postal_code: Optional[str] = None,
        property_type: Optional[str] = None,
        status: Optional[str] = "Active",
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_bedrooms: Optional[int] = None,
        max_results: int = 100
    ) -> ConnectorResponse:
        """
        Search properties with common criteria
        
        Args:
            city: City name
            state: State abbreviation
            postal_code: Postal/ZIP code
            property_type: Property type filter
            status: Listing status (Active, Sold, etc.)
            min_price: Minimum price
            max_price: Maximum price
            min_bedrooms: Minimum bedrooms
            max_results: Maximum results to return
            
        Returns:
            ConnectorResponse: Search results
        """
        try:
            filters = {}
            
            if city:
                filters["City"] = city
            if state:
                filters["StateOrProvince"] = state
            if postal_code:
                filters["PostalCode"] = postal_code
            if property_type:
                filters["PropertyType"] = property_type
            if status:
                filters["StandardStatus"] = status
            
            # Build complex filters for price and bedrooms
            filter_conditions = []
            
            for field, value in filters.items():
                filter_conditions.append(f"{field} eq '{value}'")
            
            if min_price:
                filter_conditions.append(f"ListPrice ge {min_price}")
            if max_price:
                filter_conditions.append(f"ListPrice le {max_price}")
            if min_bedrooms:
                filter_conditions.append(f"BedroomsTotal ge {min_bedrooms}")
            
            # Convert to OData filter format
            odata_filters = {}
            if filter_conditions:
                odata_filters["$filter"] = " and ".join(filter_conditions)
            
            # Use raw OData query instead of simple filters
            params = {
                "$top": str(max_results),
                "$count": "true"
            }
            
            if filter_conditions:
                params["$filter"] = " and ".join(filter_conditions)
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
            
            response = await self._make_request(
                "GET",
                "/Property",
                params=params,
                headers=headers
            )
            
            if not response.success:
                return response
            
            data = response.data
            properties = data.get("value", [])
            
            standardized_properties = [
                self._standardize_property_data(prop) for prop in properties
            ]
            
            return ConnectorResponse(
                success=True,
                data={
                    "properties": standardized_properties,
                    "total_count": data.get("@odata.count", len(properties)),
                    "search_criteria": {
                        "city": city,
                        "state": state,
                        "postal_code": postal_code,
                        "property_type": property_type,
                        "status": status,
                        "price_range": [min_price, max_price],
                        "min_bedrooms": min_bedrooms
                    }
                }
            )
        
        except Exception as e:
            logger.error(f"Property search error: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"Property search failed: {str(e)}"
            )
    
    async def _ensure_authenticated(self) -> bool:
        """Ensure valid authentication token"""
        if not self.access_token:
            auth_response = await self.authenticate()
            return auth_response.success
        
        # Check if token is expired
        if self.token_expires_at and datetime.utcnow() >= self.token_expires_at:
            auth_response = await self.authenticate()
            return auth_response.success
        
        return True
    
    def _standardize_property_data(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize RESO property data to common format
        
        Args:
            property_data: Raw RESO property data
            
        Returns:
            Dict[str, Any]: Standardized property data
        """
        # RESO field mappings to standard fields
        standardized = {
            "mls_number": property_data.get("ListingId"),
            "address": property_data.get("UnparsedAddress"),
            "city": property_data.get("City"),
            "state": property_data.get("StateOrProvince"),
            "postal_code": property_data.get("PostalCode"),
            "property_type": property_data.get("PropertyType"),
            "property_subtype": property_data.get("PropertySubType"),
            "status": property_data.get("StandardStatus"),
            "list_price": property_data.get("ListPrice"),
            "original_price": property_data.get("OriginalListPrice"),
            "sold_price": property_data.get("ClosePrice"),
            "bedrooms": property_data.get("BedroomsTotal"),
            "bathrooms": property_data.get("BathroomsTotal"),
            "living_area_sqft": property_data.get("LivingArea"),
            "lot_size_sqft": property_data.get("LotSizeSquareFeet"),
            "lot_size_acres": property_data.get("LotSizeAcres"),
            "year_built": property_data.get("YearBuilt"),
            "parking_spaces": property_data.get("ParkingTotal"),
            "garage_spaces": property_data.get("GarageSpaces"),
            "list_date": property_data.get("ListingContractDate"),
            "pending_date": property_data.get("PendingTimestamp"),
            "sold_date": property_data.get("CloseDate"),
            "days_on_market": property_data.get("DaysOnMarket"),
            "listing_agent": property_data.get("ListAgentFullName"),
            "listing_office": property_data.get("ListOfficeName"),
            "latitude": property_data.get("Latitude"),
            "longitude": property_data.get("Longitude"),
            "description": property_data.get("PublicRemarks"),
            "private_remarks": property_data.get("PrivateRemarks"),
            "photo_count": property_data.get("PhotosCount"),
            "virtual_tour_url": property_data.get("VirtualTourURLUnbranded"),
            "source": "reso_mls",
            "last_updated": property_data.get("ModificationTimestamp"),
            "original_data": property_data
        }
        
        # Remove None values
        return {k: v for k, v in standardized.items() if v is not None}