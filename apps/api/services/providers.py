"""
Provider factory for creating provider instances based on configuration.

This module provides a centralized way to create provider instances
based on environment configuration, enabling switching between
different provider implementations.
"""

import logging
from typing import Optional

from core.config import settings

# Import provider interfaces
try:
    from packages.providers.src.storage.interface import StorageProvider
    from packages.providers.src.queue.interface import QueueProvider
    from packages.providers.src.secrets.interface import SecretsProvider
    from packages.providers.src.metrics.interface import MetricsProvider
    
    # Import provider implementations
    from packages.providers.src.storage.supabase import SupabaseStorageProvider
    from packages.providers.src.storage.s3 import S3StorageProvider
    from packages.providers.src.queue.pgboss import PgBossQueueProvider
    from packages.providers.src.queue.sqs import SQSQueueProvider
    from packages.providers.src.secrets.app import AppSecretsProvider
    from packages.providers.src.secrets.kms import KMSSecretsProvider
    from packages.providers.src.metrics.otel import OTelMetricsProvider
    from packages.providers.src.metrics.cloudwatch import CloudWatchMetricsProvider
    
    PROVIDERS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Provider packages not available: {e}")
    PROVIDERS_AVAILABLE = False
    
    # Define stub interfaces for fallback
    class StorageProvider:
        pass
    
    class QueueProvider:
        pass
    
    class SecretsProvider:
        pass
    
    class MetricsProvider:
        pass

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating provider instances based on configuration."""
    
    def __init__(self):
        self._storage_provider: Optional[StorageProvider] = None
        self._queue_provider: Optional[QueueProvider] = None
        self._secrets_provider: Optional[SecretsProvider] = None
        self._metrics_provider: Optional[MetricsProvider] = None
    
    def get_storage_provider(self) -> StorageProvider:
        """Get storage provider instance."""
        if self._storage_provider is None:
            if not PROVIDERS_AVAILABLE:
                raise RuntimeError("Provider packages not available")
            
            provider_type = settings.STORAGE_PROVIDER.lower()
            
            if provider_type == "supabase":
                if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
                    raise ValueError("Supabase configuration missing")
                
                self._storage_provider = SupabaseStorageProvider(
                    url=settings.SUPABASE_URL,
                    key=settings.SUPABASE_SERVICE_ROLE_KEY,
                    bucket=settings.STORAGE_BUCKET
                )
                logger.info("Initialized Supabase storage provider")
                
            elif provider_type == "s3":
                self._storage_provider = S3StorageProvider(
                    bucket=settings.S3_BUCKET,
                    region=settings.AWS_REGION
                )
                logger.info("Initialized S3 storage provider")
                
            else:
                raise ValueError(f"Unknown storage provider: {provider_type}")
        
        return self._storage_provider
    
    def get_queue_provider(self) -> QueueProvider:
        """Get queue provider instance."""
        if self._queue_provider is None:
            if not PROVIDERS_AVAILABLE:
                raise RuntimeError("Provider packages not available")
            
            provider_type = settings.QUEUE_PROVIDER.lower()
            
            if provider_type == "pgboss":
                self._queue_provider = PgBossQueueProvider(
                    connection_string=settings.DATABASE_URL
                )
                logger.info("Initialized pg-boss queue provider")
                
            elif provider_type == "sqs":
                self._queue_provider = SQSQueueProvider(
                    region=settings.AWS_REGION
                )
                logger.info("Initialized SQS queue provider")
                
            else:
                raise ValueError(f"Unknown queue provider: {provider_type}")
        
        return self._queue_provider
    
    def get_secrets_provider(self) -> SecretsProvider:
        """Get secrets provider instance."""
        if self._secrets_provider is None:
            if not PROVIDERS_AVAILABLE:
                raise RuntimeError("Provider packages not available")
            
            provider_type = settings.SECRETS_PROVIDER.lower()
            
            if provider_type == "app":
                if not settings.ENCRYPTION_SECRET_KEY:
                    raise ValueError("App-level encryption key not configured")
                
                self._secrets_provider = AppSecretsProvider(
                    secret_key=settings.ENCRYPTION_SECRET_KEY,
                    key_version=settings.ENCRYPTION_KEY_VERSION
                )
                logger.info("Initialized app-level secrets provider")
                
            elif provider_type == "kms":
                if not settings.KMS_KEY_ID:
                    raise ValueError("KMS key ID not configured")
                
                self._secrets_provider = KMSSecretsProvider(
                    kms_key_id=settings.KMS_KEY_ID,
                    region=settings.AWS_REGION
                )
                logger.info("Initialized KMS secrets provider")
                
            else:
                raise ValueError(f"Unknown secrets provider: {provider_type}")
        
        return self._secrets_provider
    
    def get_metrics_provider(self) -> MetricsProvider:
        """Get metrics provider instance."""
        if self._metrics_provider is None:
            if not PROVIDERS_AVAILABLE:
                raise RuntimeError("Provider packages not available")
            
            provider_type = settings.METRICS_PROVIDER.lower()
            
            if provider_type == "otel":
                self._metrics_provider = OTelMetricsProvider(
                    service_name=settings.SERVICE_NAME,
                    service_version=settings.SERVICE_VERSION,
                    endpoint=settings.OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
                    headers=settings.OTEL_EXPORTER_OTLP_HEADERS
                )
                logger.info("Initialized OpenTelemetry metrics provider")
                
            elif provider_type == "cloudwatch":
                self._metrics_provider = CloudWatchMetricsProvider(
                    namespace=f"{settings.PROJECT_NAME}-{settings.ENVIRONMENT}",
                    region=settings.AWS_REGION
                )
                logger.info("Initialized CloudWatch metrics provider")
                
            else:
                raise ValueError(f"Unknown metrics provider: {provider_type}")
        
        return self._metrics_provider
    
    def reset(self):
        """Reset all cached provider instances."""
        self._storage_provider = None
        self._queue_provider = None
        self._secrets_provider = None
        self._metrics_provider = None


# Global factory instance
_provider_factory = ProviderFactory()


def get_storage_provider() -> StorageProvider:
    """Get the configured storage provider."""
    return _provider_factory.get_storage_provider()


def get_queue_provider() -> QueueProvider:
    """Get the configured queue provider."""
    return _provider_factory.get_queue_provider()


def get_secrets_provider() -> SecretsProvider:
    """Get the configured secrets provider."""
    return _provider_factory.get_secrets_provider()


def get_metrics_provider() -> MetricsProvider:
    """Get the configured metrics provider."""
    return _provider_factory.get_metrics_provider()


def reset_providers():
    """Reset all provider instances (useful for testing)."""
    _provider_factory.reset()


def check_provider_health() -> dict:
    """Check health of all configured providers."""
    health = {
        "storage": {"configured": False, "healthy": False},
        "queue": {"configured": False, "healthy": False},
        "secrets": {"configured": False, "healthy": False},
        "metrics": {"configured": False, "healthy": False}
    }
    
    if not PROVIDERS_AVAILABLE:
        return {
            "error": "Provider packages not available",
            "providers": health
        }
    
    # Check storage provider
    try:
        storage = get_storage_provider()
        health["storage"]["configured"] = True
        # TODO: Add actual health check
        health["storage"]["healthy"] = True
    except Exception as e:
        health["storage"]["error"] = str(e)
    
    # Check queue provider
    try:
        queue = get_queue_provider()
        health["queue"]["configured"] = True
        # TODO: Add actual health check
        health["queue"]["healthy"] = True
    except Exception as e:
        health["queue"]["error"] = str(e)
    
    # Check secrets provider
    try:
        secrets = get_secrets_provider()
        health["secrets"]["configured"] = True
        # TODO: Add actual health check
        health["secrets"]["healthy"] = True
    except Exception as e:
        health["secrets"]["error"] = str(e)
    
    # Check metrics provider
    try:
        metrics = get_metrics_provider()
        health["metrics"]["configured"] = True
        # TODO: Add actual health check
        health["metrics"]["healthy"] = True
    except Exception as e:
        health["metrics"]["error"] = str(e)
    
    return {"providers": health}