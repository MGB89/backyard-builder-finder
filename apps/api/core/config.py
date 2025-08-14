"""Application configuration using Pydantic settings."""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # Application
    APP_NAME: str = "Backyard Builder Finder API"
    PROJECT_NAME: str = Field(default="backyard-builder", env="PROJECT_NAME")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://bbf_user:dev_password@localhost:5432/backyard_builder",
        env="DATABASE_URL"
    )
    SYNC_DATABASE_URL: str = Field(
        default="postgresql://bbf_user:dev_password@localhost:5432/backyard_builder",
        env="SYNC_DATABASE_URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    # Authentication
    JWT_SECRET: str = Field(default="change-this-secret-key", env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_HOURS: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # NextAuth Integration
    NEXTAUTH_URL: str = Field(default="http://localhost:3000", env="NEXTAUTH_URL")
    NEXTAUTH_SECRET: str = Field(default="", env="NEXTAUTH_SECRET")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    CACHE_TTL: int = Field(default=3600, env="CACHE_TTL")
    
    # Provider configuration
    STORAGE_PROVIDER: str = Field(default="supabase", env="STORAGE_PROVIDER")
    QUEUE_PROVIDER: str = Field(default="pgboss", env="QUEUE_PROVIDER") 
    SECRETS_PROVIDER: str = Field(default="app", env="SECRETS_PROVIDER")
    METRICS_PROVIDER: str = Field(default="otel", env="METRICS_PROVIDER")
    
    # Supabase configuration
    SUPABASE_URL: Optional[str] = Field(default=None, env="SUPABASE_URL")
    SUPABASE_ANON_KEY: Optional[str] = Field(default=None, env="SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = Field(default=None, env="SUPABASE_SERVICE_ROLE_KEY")
    
    # Storage configuration
    STORAGE_BUCKET: str = Field(default="exports", env="STORAGE_BUCKET")
    
    # App-level encryption
    ENCRYPTION_SECRET_KEY: Optional[str] = Field(default=None, env="ENCRYPTION_SECRET_KEY")
    ENCRYPTION_KEY_VERSION: int = Field(default=1, env="ENCRYPTION_KEY_VERSION")
    
    # Observability
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: Optional[str] = Field(default=None, env="OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
    OTEL_EXPORTER_OTLP_HEADERS: Optional[str] = Field(default=None, env="OTEL_EXPORTER_OTLP_HEADERS")
    SERVICE_NAME: str = Field(default="backyard-builder-api", env="SERVICE_NAME")
    SERVICE_VERSION: str = Field(default="1.0.0", env="SERVICE_VERSION")
    
    # Legacy AWS support (for migration)
    AWS_REGION: str = Field(default="us-west-2", env="AWS_REGION")
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    S3_BUCKET: str = Field(default="backyard-builder-exports", env="S3_BUCKET")
    KMS_KEY_ID: Optional[str] = Field(default=None, env="KMS_KEY_ID")
    
    # OAuth Providers
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_SECRET")
    AZURE_AD_CLIENT_ID: Optional[str] = Field(default=None, env="AZURE_AD_CLIENT_ID")
    AZURE_AD_CLIENT_SECRET: Optional[str] = Field(default=None, env="AZURE_AD_CLIENT_SECRET")
    AZURE_AD_TENANT_ID: Optional[str] = Field(default=None, env="AZURE_AD_TENANT_ID")
    
    # LLM Providers
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL")
    ANTHROPIC_BASE_URL: str = Field(default="https://api.anthropic.com", env="ANTHROPIC_BASE_URL")
    
    # Geocoding
    MAPBOX_TOKEN: Optional[str] = Field(default=None, env="MAPBOX_TOKEN")
    GOOGLE_MAPS_API_KEY: Optional[str] = Field(default=None, env="GOOGLE_MAPS_API_KEY")
    MAPTILER_KEY: Optional[str] = Field(default=None, env="MAPTILER_KEY")
    
    # Data Sources
    LA_PARCELS_ENDPOINT: str = Field(
        default="https://maps.lacity.org/arcgis/rest/services/Parcel/MapServer/0",
        env="LA_PARCELS_ENDPOINT"
    )
    LA_ZONING_ENDPOINT: str = Field(
        default="https://maps.lacity.org/arcgis/rest/services/Zoning/MapServer/0",
        env="LA_ZONING_ENDPOINT"
    )
    MSFT_BUILDINGS_URL: str = Field(
        default="https://github.com/microsoft/USBuildingFootprints",
        env="MSFT_BUILDINGS_URL"
    )
    
    # RESO MLS (optional)
    RESO_CLIENT_ID: Optional[str] = Field(default=None, env="RESO_CLIENT_ID")
    RESO_CLIENT_SECRET: Optional[str] = Field(default=None, env="RESO_CLIENT_SECRET")
    RESO_API_URL: Optional[str] = Field(default=None, env="RESO_API_URL")
    
    # Feature Flags
    ENABLE_CV_MODULE: bool = Field(default=False, env="ENABLE_CV_MODULE")
    ENABLE_PORTAL_SCRAPING: bool = Field(default=False, env="ENABLE_PORTAL_SCRAPING")
    REQUIRE_TOS_ACCEPTANCE: bool = Field(default=True, env="REQUIRE_TOS_ACCEPTANCE")
    
    # System Limits
    MAX_PARCELS_PER_SEARCH: int = Field(default=50000, env="MAX_PARCELS_PER_SEARCH")
    MAX_LLM_TOKENS_PER_ORG_DAILY: int = Field(default=100000, env="MAX_LLM_TOKENS_PER_ORG_DAILY")
    MAX_CV_TILES_PER_SEARCH: int = Field(default=100, env="MAX_CV_TILES_PER_SEARCH")
    DEFAULT_PAGE_SIZE: int = Field(default=100, env="DEFAULT_PAGE_SIZE")
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW")
    
    # Geoprocessing Defaults
    DEFAULT_FRONT_SETBACK: float = Field(default=25.0, env="DEFAULT_FRONT_SETBACK")
    DEFAULT_SIDE_SETBACK: float = Field(default=5.0, env="DEFAULT_SIDE_SETBACK")
    DEFAULT_REAR_SETBACK: float = Field(default=10.0, env="DEFAULT_REAR_SETBACK")
    MAX_LOT_COVERAGE: float = Field(default=0.4, env="MAX_LOT_COVERAGE")
    DEFAULT_FAR: float = Field(default=0.5, env="DEFAULT_FAR")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Development
    ENABLE_DOCS: bool = Field(default=True, env="ENABLE_DOCS")
    ENABLE_REDOC: bool = Field(default=True, env="ENABLE_REDOC")
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()