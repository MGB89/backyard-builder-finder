"""
Secrets management service using configurable provider backend.
Supports both app-level encryption and AWS KMS depending on configuration.
"""

import json
import logging
from typing import Dict, Optional, Any
from functools import lru_cache

from core.config import settings
from services.providers import get_secrets_provider

logger = logging.getLogger(__name__)


class SecretsManager:
    """Secrets manager using configurable provider backend"""
    
    def __init__(self):
        self._provider = None
        logger.info(f"SecretsManager initialized with provider: {settings.SECRETS_PROVIDER}")
    
    @property
    def provider(self):
        """Get the secrets provider instance."""
        if self._provider is None:
            try:
                self._provider = get_secrets_provider()
            except Exception as e:
                logger.error(f"Failed to initialize secrets provider: {e}")
                # Fallback to legacy behavior
                self._provider = None
        return self._provider
    
    @lru_cache(maxsize=32)
    def get_secret(self, secret_name: str) -> Dict[str, Any]:
        """
        Retrieve and parse a secret using the configured provider
        
        Args:
            secret_name: Name of the secret
            
        Returns:
            Dictionary containing the secret values
            
        Raises:
            Exception: If secret cannot be retrieved
        """
        try:
            if self.provider:
                # Use provider-based secret retrieval
                secret_value = self.provider.get_secret(secret_name)
                if isinstance(secret_value, str):
                    try:
                        return json.loads(secret_value)
                    except json.JSONDecodeError:
                        # If not JSON, return as plain string in a dict
                        return {"value": secret_value}
                elif isinstance(secret_value, dict):
                    return secret_value
                else:
                    return {"value": secret_value}
            else:
                # Fallback to development secrets
                logger.warning(f"Provider not available, using development fallback for: {secret_name}")
                return self._get_development_secret(secret_name)
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            # Try development fallback
            return self._get_development_secret(secret_name)
    
    def _get_development_secret(self, secret_name: str) -> Dict[str, Any]:
        """
        Fallback for development environment - use environment variables
        """
        if secret_name.endswith('-app-secrets'):
            return {
                'jwt_secret': settings.JWT_SECRET,
                'api_key': 'dev-api-key',
                'encryption_key': 'dev-encryption-key-32-chars-long',
                'session_secret': 'dev-session-secret'
            }
        elif secret_name.endswith('-oauth-providers'):
            return {
                'nextauth_secret': settings.NEXTAUTH_SECRET,
                'google_client_id': settings.GOOGLE_CLIENT_ID or '',
                'google_client_secret': settings.GOOGLE_CLIENT_SECRET or '',
                'azure_ad_client_id': settings.AZURE_AD_CLIENT_ID or '',
                'azure_ad_client_secret': settings.AZURE_AD_CLIENT_SECRET or '',
                'azure_ad_tenant_id': settings.AZURE_AD_TENANT_ID or ''
            }
        elif secret_name.endswith('-db-connection'):
            return {
                'host': settings.DATABASE_URL.split('@')[1].split(':')[0] if '@' in settings.DATABASE_URL else 'localhost',
                'port': '5432',
                'database': 'backyard_builder',
                'username': 'bbf_user',
                'password': 'dev_password',
                'ssl_mode': 'prefer',
                'connection_string': settings.DATABASE_URL
            }
        elif secret_name.endswith('-third-party-apis'):
            return {
                'mapbox_token': settings.MAPBOX_TOKEN or '',
                'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY or '',
                'openai_api_key': 'USER_PROVIDED_ENCRYPTED',
                'anthropic_api_key': 'USER_PROVIDED_ENCRYPTED'
            }
        else:
            logger.warning(f"Unknown secret type: {secret_name}")
            return {}
    
    def get_app_secrets(self) -> Dict[str, Any]:
        """Get application secrets (JWT, encryption keys, etc.)"""
        secret_name = f"{settings.PROJECT_NAME}-{settings.ENVIRONMENT}-app-secrets"
        return self.get_secret(secret_name)
    
    def get_oauth_secrets(self) -> Dict[str, Any]:
        """Get OAuth provider secrets"""
        secret_name = f"{settings.PROJECT_NAME}-{settings.ENVIRONMENT}-oauth-providers"
        return self.get_secret(secret_name)
    
    def get_db_secrets(self) -> Dict[str, Any]:
        """Get database connection secrets"""
        secret_name = f"{settings.PROJECT_NAME}-{settings.ENVIRONMENT}-db-connection"
        return self.get_secret(secret_name)
    
    def get_third_party_secrets(self) -> Dict[str, Any]:
        """Get third-party API secrets"""
        secret_name = f"{settings.PROJECT_NAME}-{settings.ENVIRONMENT}-third-party-apis"
        return self.get_secret(secret_name)
    
    def invalidate_cache(self):
        """Clear the secrets cache (useful for testing or after secret rotation)"""
        self.get_secret.cache_clear()


# Global instance
secrets_manager = SecretsManager()


def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance"""
    return secrets_manager


# Convenience functions for common secret retrievals
def get_jwt_secret() -> str:
    """Get JWT secret for token signing"""
    try:
        secrets = secrets_manager.get_app_secrets()
        return secrets.get('jwt_secret', settings.JWT_SECRET)
    except Exception as e:
        logger.error(f"Failed to get JWT secret from Secrets Manager: {e}")
        return settings.JWT_SECRET


def get_database_url() -> str:
    """Get database connection URL"""
    try:
        secrets = secrets_manager.get_db_secrets()
        return secrets.get('connection_string', settings.DATABASE_URL)
    except Exception as e:
        logger.error(f"Failed to get database URL from Secrets Manager: {e}")
        return settings.DATABASE_URL


def get_nextauth_secret() -> str:
    """Get NextAuth secret"""
    try:
        secrets = secrets_manager.get_oauth_secrets()
        return secrets.get('nextauth_secret', settings.NEXTAUTH_SECRET)
    except Exception as e:
        logger.error(f"Failed to get NextAuth secret from Secrets Manager: {e}")
        return settings.NEXTAUTH_SECRET


def get_oauth_credentials() -> Dict[str, str]:
    """Get OAuth provider credentials"""
    try:
        secrets = secrets_manager.get_oauth_secrets()
        return {
            'google_client_id': secrets.get('google_client_id', ''),
            'google_client_secret': secrets.get('google_client_secret', ''),
            'azure_ad_client_id': secrets.get('azure_ad_client_id', ''),
            'azure_ad_client_secret': secrets.get('azure_ad_client_secret', ''),
            'azure_ad_tenant_id': secrets.get('azure_ad_tenant_id', '')
        }
    except Exception as e:
        logger.error(f"Failed to get OAuth credentials from Secrets Manager: {e}")
        return {
            'google_client_id': settings.GOOGLE_CLIENT_ID or '',
            'google_client_secret': settings.GOOGLE_CLIENT_SECRET or '',
            'azure_ad_client_id': settings.AZURE_AD_CLIENT_ID or '',
            'azure_ad_client_secret': settings.AZURE_AD_CLIENT_SECRET or '',
            'azure_ad_tenant_id': settings.AZURE_AD_TENANT_ID or ''
        }