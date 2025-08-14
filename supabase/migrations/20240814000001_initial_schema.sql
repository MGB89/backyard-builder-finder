-- Initial schema migration for Backyard Builder Finder
-- Converted from Alembic to Supabase migrations

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create organizations table
CREATE TABLE IF NOT EXISTS public.organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255),
    description TEXT,
    email VARCHAR(255),
    phone VARCHAR(50),
    website VARCHAR(255),
    
    -- Subscription and limits
    subscription_tier VARCHAR(50) NOT NULL DEFAULT 'basic',
    api_rate_limit INTEGER NOT NULL DEFAULT 100,
    
    -- Address information
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    postal_code VARCHAR(20),
    country VARCHAR(50) DEFAULT 'US',
    
    -- Status and metadata
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Computed fields
    full_address TEXT GENERATED ALWAYS AS (
        CASE 
            WHEN address_line1 IS NOT NULL THEN
                CONCAT_WS(', ', 
                    CONCAT_WS(' ', address_line1, address_line2),
                    city, 
                    CONCAT_WS(' ', state, postal_code),
                    country
                )
            ELSE NULL
        END
    ) STORED
);

-- Create indexes for organizations
CREATE INDEX IF NOT EXISTS idx_organizations_name ON public.organizations(name);
CREATE INDEX IF NOT EXISTS idx_organizations_active ON public.organizations(is_active);

-- Create users table
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    
    -- Authentication
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) UNIQUE,
    hashed_password VARCHAR(255), -- Nullable for OAuth users
    
    -- Profile information
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(50),
    profile_image VARCHAR(500),
    
    -- OAuth integration
    oauth_provider VARCHAR(50), -- 'google', 'azure-ad', etc.
    oauth_provider_id VARCHAR(255), -- Provider's user ID
    
    -- Role and permissions
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    
    -- Security tracking
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    last_login_at TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Verification tokens
    verification_token VARCHAR(255),
    reset_token VARCHAR(255),
    reset_token_expires TIMESTAMPTZ,
    
    -- Profile settings
    profile_settings JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Computed full name
    full_name TEXT GENERATED ALWAYS AS (
        CASE 
            WHEN first_name IS NOT NULL OR last_name IS NOT NULL THEN
                TRIM(CONCAT(COALESCE(first_name, ''), ' ', COALESCE(last_name, '')))
            ELSE NULL
        END
    ) STORED,
    
    -- Role validation constraint
    CONSTRAINT valid_role CHECK (role IN ('owner', 'admin', 'member'))
);

-- Create indexes for users
CREATE INDEX IF NOT EXISTS idx_users_org_id ON public.users(org_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_oauth ON public.users(oauth_provider, oauth_provider_id);
CREATE INDEX IF NOT EXISTS idx_users_active ON public.users(is_active);

-- Create user_api_keys table
CREATE TABLE IF NOT EXISTS public.user_api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- API key details
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(500) NOT NULL, -- Encrypted API key
    key_prefix VARCHAR(10) NOT NULL, -- First few chars for identification
    
    -- Permissions and limits
    scopes JSONB, -- Array of scopes
    rate_limit VARCHAR(50), -- e.g., "1000/hour"
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for user_api_keys
CREATE INDEX IF NOT EXISTS idx_user_api_keys_org_user ON public.user_api_keys(org_id, user_id);
CREATE INDEX IF NOT EXISTS idx_user_api_keys_prefix ON public.user_api_keys(key_prefix);

-- Create searches table
CREATE TABLE IF NOT EXISTS public.searches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    
    -- Search definition
    name VARCHAR(255),
    area_geom GEOMETRY(POLYGON, 4326), -- Search area polygon
    filters JSONB NOT NULL, -- Search filters as JSON
    
    -- Processing status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    stage VARCHAR(50) NOT NULL DEFAULT 'queued',
    progress_percent INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- Results
    total_parcels INTEGER,
    eligible_parcels INTEGER,
    estimated_cost DECIMAL(10,4),
    actual_cost DECIMAL(10,4),
    
    -- Job tracking
    job_id VARCHAR(255), -- Queue job ID
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    -- Status validation
    CONSTRAINT valid_status CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    CONSTRAINT valid_stage CHECK (stage IN ('queued', 'area_resolve', 'attributes', 'geometry', 'cv', 'zoning', 'fit_test', 'completed'))
);

-- Create spatial index for searches
CREATE INDEX IF NOT EXISTS idx_searches_area_geom ON public.searches USING GIST(area_geom);
CREATE INDEX IF NOT EXISTS idx_searches_org_user ON public.searches(org_id, user_id);
CREATE INDEX IF NOT EXISTS idx_searches_status ON public.searches(status);

-- Create parcels table
CREATE TABLE IF NOT EXISTS public.parcels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    
    -- External identifiers
    external_id VARCHAR(255) NOT NULL,
    source VARCHAR(100) NOT NULL, -- 'arcgis_los-angeles', etc.
    region_code VARCHAR(50) NOT NULL,
    
    -- Geometry
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
    centroid GEOMETRY(POINT, 4326),
    area_sqft DECIMAL(12,2),
    
    -- Zoning information
    zoning_code VARCHAR(100),
    zoning_description TEXT,
    land_use VARCHAR(100),
    
    -- Attributes
    attributes JSONB, -- Raw attributes from source
    
    -- Processing metadata
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    data_vintage DATE,
    
    -- Unique constraint on external source
    UNIQUE(external_id, source, region_code)
);

-- Create spatial indexes for parcels
CREATE INDEX IF NOT EXISTS idx_parcels_geometry ON public.parcels USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_parcels_centroid ON public.parcels USING GIST(centroid);
CREATE INDEX IF NOT EXISTS idx_parcels_source ON public.parcels(source, region_code);
CREATE INDEX IF NOT EXISTS idx_parcels_zoning ON public.parcels(zoning_code);

-- Create building_footprints table
CREATE TABLE IF NOT EXISTS public.building_footprints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    
    -- External identifiers
    external_id VARCHAR(255) NOT NULL,
    source VARCHAR(100) NOT NULL DEFAULT 'microsoft_buildings',
    region_code VARCHAR(50) NOT NULL,
    
    -- Geometry
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
    centroid GEOMETRY(POINT, 4326),
    area_sqft DECIMAL(12,2),
    
    -- Building attributes
    building_type VARCHAR(100),
    height_ft DECIMAL(8,2),
    
    -- Metadata
    attributes JSONB,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint
    UNIQUE(external_id, source, region_code)
);

-- Create spatial indexes for building_footprints
CREATE INDEX IF NOT EXISTS idx_building_footprints_geometry ON public.building_footprints USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_building_footprints_source ON public.building_footprints(source, region_code);

-- Create zoning_rules table (for LLM-parsed zoning codes)
CREATE TABLE IF NOT EXISTS public.zoning_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    
    -- Zoning identification
    region_code VARCHAR(50) NOT NULL,
    zoning_code VARCHAR(100) NOT NULL,
    rules_hash VARCHAR(64) NOT NULL, -- Hash of input rules text
    
    -- Parsed rules (JSON following ZONING_RULES_SCHEMA.md)
    rules_jsonb JSONB NOT NULL,
    
    -- Source information
    source_text TEXT, -- Original zoning text
    llm_model VARCHAR(100), -- Model used for parsing
    confidence_score DECIMAL(3,2), -- 0.0-1.0
    
    -- Manual override capability
    is_manually_verified BOOLEAN DEFAULT false,
    verified_by UUID REFERENCES public.users(id),
    verified_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Unique constraint on zoning code per region
    UNIQUE(region_code, zoning_code, rules_hash)
);

-- Create indexes for zoning_rules
CREATE INDEX IF NOT EXISTS idx_zoning_rules_region_code ON public.zoning_rules(region_code, zoning_code);
CREATE INDEX IF NOT EXISTS idx_zoning_rules_hash ON public.zoning_rules(rules_hash);

-- Create derived_buildable table (cached results)
CREATE TABLE IF NOT EXISTS public.derived_buildable (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    parcel_id UUID NOT NULL REFERENCES public.parcels(id) ON DELETE CASCADE,
    
    -- Buildable area calculation
    buildable_geometry GEOMETRY(POLYGON, 4326),
    buildable_area_sqft DECIMAL(12,2),
    
    -- Setback values used
    front_setback_ft DECIMAL(8,2),
    side_setback_ft DECIMAL(8,2),
    rear_setback_ft DECIMAL(8,2),
    
    -- Zoning compliance
    zoning_compliant BOOLEAN,
    max_coverage_ratio DECIMAL(5,4),
    max_far DECIMAL(5,2),
    
    -- Unit placement test results
    unit_fits BOOLEAN,
    unit_geometry GEOMETRY(POLYGON, 4326),
    unit_area_sqft DECIMAL(10,2),
    
    -- Processing metadata
    settings_hash VARCHAR(64) NOT NULL, -- Hash of processing settings
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Unique constraint to prevent duplicates
    UNIQUE(parcel_id, settings_hash)
);

-- Create spatial indexes for derived_buildable
CREATE INDEX IF NOT EXISTS idx_derived_buildable_geometry ON public.derived_buildable USING GIST(buildable_geometry);
CREATE INDEX IF NOT EXISTS idx_derived_buildable_unit_geom ON public.derived_buildable USING GIST(unit_geometry);
CREATE INDEX IF NOT EXISTS idx_derived_buildable_fits ON public.derived_buildable(unit_fits);

-- Create cv_artifacts table (computer vision results)
CREATE TABLE IF NOT EXISTS public.cv_artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    parcel_id UUID NOT NULL REFERENCES public.parcels(id) ON DELETE CASCADE,
    
    -- CV detection results
    has_pool BOOLEAN,
    has_trees BOOLEAN,
    has_driveway BOOLEAN,
    
    -- Geometries of detected features
    pool_geometry GEOMETRY(MULTIPOLYGON, 4326),
    tree_geometry GEOMETRY(MULTIPOLYGON, 4326),
    driveway_geometry GEOMETRY(MULTIPOLYGON, 4326),
    
    -- Confidence scores
    pool_confidence DECIMAL(3,2),
    tree_confidence DECIMAL(3,2),
    driveway_confidence DECIMAL(3,2),
    
    -- Processing metadata
    cv_model VARCHAR(100),
    imagery_source VARCHAR(100),
    imagery_date DATE,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Settings used
    settings_hash VARCHAR(64) NOT NULL,
    
    -- Unique constraint
    UNIQUE(parcel_id, settings_hash)
);

-- Create spatial indexes for cv_artifacts
CREATE INDEX IF NOT EXISTS idx_cv_artifacts_pool_geom ON public.cv_artifacts USING GIST(pool_geometry);
CREATE INDEX IF NOT EXISTS idx_cv_artifacts_tree_geom ON public.cv_artifacts USING GIST(tree_geometry);
CREATE INDEX IF NOT EXISTS idx_cv_artifacts_features ON public.cv_artifacts(has_pool, has_trees, has_driveway);

-- Create listings table (public MLS data)
CREATE TABLE IF NOT EXISTS public.listings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    
    -- External identifiers
    external_id VARCHAR(255) NOT NULL,
    source VARCHAR(100) NOT NULL,
    
    -- Location
    address TEXT,
    geometry GEOMETRY(POINT, 4326),
    parcel_id UUID REFERENCES public.parcels(id),
    
    -- Listing details
    price DECIMAL(12,2),
    bedrooms INTEGER,
    bathrooms DECIMAL(3,1),
    sqft INTEGER,
    lot_size_sqft INTEGER,
    year_built INTEGER,
    
    -- Listing metadata
    listing_type VARCHAR(50), -- 'for_sale', 'for_rent', 'sold'
    listing_date DATE,
    status VARCHAR(50),
    
    -- Additional attributes
    attributes JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Unique constraint
    UNIQUE(external_id, source)
);

-- Create indexes for listings
CREATE INDEX IF NOT EXISTS idx_listings_geometry ON public.listings USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_listings_price ON public.listings(price);
CREATE INDEX IF NOT EXISTS idx_listings_type_status ON public.listings(listing_type, status);

-- Create exports table
CREATE TABLE IF NOT EXISTS public.exports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    search_id UUID NOT NULL REFERENCES public.searches(id) ON DELETE CASCADE,
    
    -- Export details
    format VARCHAR(20) NOT NULL, -- 'csv', 'geojson', 'pdf'
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    
    -- File information
    file_path VARCHAR(500),
    file_size_bytes BIGINT,
    signed_url VARCHAR(1000), -- Temporary signed URL
    signed_url_expires TIMESTAMPTZ,
    
    -- Usage tracking
    download_count INTEGER NOT NULL DEFAULT 0,
    last_downloaded_at TIMESTAMPTZ,
    
    -- Processing
    job_id VARCHAR(255),
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT valid_format CHECK (format IN ('csv', 'geojson', 'pdf')),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'expired'))
);

-- Create indexes for exports
CREATE INDEX IF NOT EXISTS idx_exports_user_org ON public.exports(user_id, org_id);
CREATE INDEX IF NOT EXISTS idx_exports_search ON public.exports(search_id);
CREATE INDEX IF NOT EXISTS idx_exports_status ON public.exports(status);

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    org_id UUID REFERENCES public.organizations(id) ON DELETE CASCADE,
    
    -- Event classification
    event_type VARCHAR(50) NOT NULL, -- 'login', 'search', 'export', etc.
    event_category VARCHAR(50) NOT NULL, -- 'auth', 'data', 'admin'
    action TEXT NOT NULL,
    
    -- Resource information
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    
    -- Event details
    description TEXT,
    old_values JSONB,
    new_values JSONB,
    
    -- Request context
    ip_address INET,
    user_agent TEXT,
    session_id VARCHAR(255),
    
    -- Status and timing
    status VARCHAR(20) NOT NULL DEFAULT 'success',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('success', 'failure', 'warning'))
);

-- Create indexes for audit_logs
CREATE INDEX IF NOT EXISTS idx_audit_logs_org_id ON public.audit_logs(org_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON public.audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event ON public.audit_logs(event_type, event_category);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON public.audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON public.audit_logs(resource_type, resource_id);

-- Create updated_at triggers for all tables
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON public.organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_api_keys_updated_at BEFORE UPDATE ON public.user_api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_searches_updated_at BEFORE UPDATE ON public.searches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_zoning_rules_updated_at BEFORE UPDATE ON public.zoning_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_listings_updated_at BEFORE UPDATE ON public.listings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_exports_updated_at BEFORE UPDATE ON public.exports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();