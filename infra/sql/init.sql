-- =============================================================================
-- PostgreSQL Database Initialization Script with PostGIS Extension
-- Property Assessment System
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "hstore";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- =============================================================================
-- Create Application Schemas
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS property_data;
CREATE SCHEMA IF NOT EXISTS spatial_data;
CREATE SCHEMA IF NOT EXISTS audit_logs;
CREATE SCHEMA IF NOT EXISTS cache_data;

-- =============================================================================
-- Create Custom Types
-- =============================================================================

-- Property types
DO $$ BEGIN
    CREATE TYPE property_data.property_type AS ENUM (
        'residential',
        'commercial',
        'industrial',
        'agricultural',
        'recreational',
        'vacant_land',
        'mixed_use'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Assessment status
DO $$ BEGIN
    CREATE TYPE property_data.assessment_status AS ENUM (
        'pending',
        'in_progress',
        'completed',
        'under_review',
        'approved',
        'rejected'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Document types
DO $$ BEGIN
    CREATE TYPE property_data.document_type AS ENUM (
        'deed',
        'survey',
        'appraisal',
        'inspection',
        'photo',
        'tax_record',
        'permit',
        'other'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- =============================================================================
-- Core Property Tables
-- =============================================================================

-- Properties table
CREATE TABLE IF NOT EXISTS property_data.properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id VARCHAR(50) UNIQUE NOT NULL,
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    zip_code VARCHAR(20) NOT NULL,
    county VARCHAR(100) NOT NULL,
    property_type property_data.property_type NOT NULL,
    lot_size_sqft DECIMAL(15,2),
    building_sqft DECIMAL(15,2),
    year_built INTEGER,
    bedrooms INTEGER,
    bathrooms DECIMAL(3,1),
    stories INTEGER,
    garage_spaces INTEGER,
    pool BOOLEAN DEFAULT FALSE,
    fireplace BOOLEAN DEFAULT FALSE,
    basement BOOLEAN DEFAULT FALSE,
    attic BOOLEAN DEFAULT FALSE,
    assessed_value DECIMAL(15,2),
    market_value DECIMAL(15,2),
    tax_value DECIMAL(15,2),
    last_sale_date DATE,
    last_sale_price DECIMAL(15,2),
    owner_name TEXT,
    owner_address TEXT,
    parcel_number VARCHAR(50),
    legal_description TEXT,
    zoning_classification VARCHAR(50),
    land_use_code VARCHAR(20),
    school_district VARCHAR(100),
    assessment_status property_data.assessment_status DEFAULT 'pending',
    notes TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);

-- Spatial data for properties
CREATE TABLE IF NOT EXISTS spatial_data.property_boundaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL REFERENCES property_data.properties(id) ON DELETE CASCADE,
    boundary_geom GEOMETRY(POLYGON, 4326) NOT NULL,
    centroid_geom GEOMETRY(POINT, 4326),
    area_sqft DECIMAL(15,2),
    perimeter_ft DECIMAL(15,2),
    source_system VARCHAR(100),
    accuracy_level VARCHAR(50),
    survey_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Building footprints
CREATE TABLE IF NOT EXISTS spatial_data.building_footprints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL REFERENCES property_data.properties(id) ON DELETE CASCADE,
    building_geom GEOMETRY(POLYGON, 4326) NOT NULL,
    building_type VARCHAR(50),
    building_height DECIMAL(8,2),
    floor_count INTEGER,
    roof_type VARCHAR(50),
    construction_material VARCHAR(100),
    building_age INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Property assessments
CREATE TABLE IF NOT EXISTS property_data.assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL REFERENCES property_data.properties(id) ON DELETE CASCADE,
    assessment_date DATE NOT NULL,
    assessed_by VARCHAR(100) NOT NULL,
    assessment_type VARCHAR(50) NOT NULL,
    land_value DECIMAL(15,2),
    improvement_value DECIMAL(15,2),
    total_value DECIMAL(15,2),
    assessment_notes TEXT,
    methodology_used TEXT,
    comparable_properties JSONB,
    assessment_status property_data.assessment_status DEFAULT 'pending',
    review_date DATE,
    reviewed_by VARCHAR(100),
    approval_date DATE,
    approved_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Property documents
CREATE TABLE IF NOT EXISTS property_data.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL REFERENCES property_data.properties(id) ON DELETE CASCADE,
    document_name VARCHAR(255) NOT NULL,
    document_type property_data.document_type NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),
    description TEXT,
    document_date DATE,
    uploaded_by VARCHAR(100),
    is_public BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Property photos
CREATE TABLE IF NOT EXISTS property_data.photos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL REFERENCES property_data.properties(id) ON DELETE CASCADE,
    photo_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    thumbnail_path TEXT,
    file_size BIGINT,
    image_width INTEGER,
    image_height INTEGER,
    description TEXT,
    photo_date TIMESTAMP WITH TIME ZONE,
    location_geom GEOMETRY(POINT, 4326),
    camera_direction DECIMAL(5,2), -- degrees from north
    photo_type VARCHAR(50), -- exterior, interior, aerial, etc.
    uploaded_by VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Reference Tables
-- =============================================================================

-- Municipalities
CREATE TABLE IF NOT EXISTS spatial_data.municipalities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    municipality_type VARCHAR(50), -- city, town, village, etc.
    state VARCHAR(50) NOT NULL,
    county VARCHAR(100) NOT NULL,
    fips_code VARCHAR(10),
    boundary_geom GEOMETRY(MULTIPOLYGON, 4326),
    area_sqmi DECIMAL(10,4),
    population INTEGER,
    incorporation_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- School districts
CREATE TABLE IF NOT EXISTS spatial_data.school_districts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    district_code VARCHAR(20),
    district_type VARCHAR(50), -- elementary, high school, unified, etc.
    state VARCHAR(50) NOT NULL,
    boundary_geom GEOMETRY(MULTIPOLYGON, 4326),
    enrollment INTEGER,
    grade_levels VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Zoning districts
CREATE TABLE IF NOT EXISTS spatial_data.zoning_districts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    zone_code VARCHAR(20) NOT NULL,
    zone_name VARCHAR(100) NOT NULL,
    zone_description TEXT,
    municipality_id UUID REFERENCES spatial_data.municipalities(id),
    boundary_geom GEOMETRY(MULTIPOLYGON, 4326),
    max_building_height DECIMAL(8,2),
    max_floor_area_ratio DECIMAL(4,2),
    min_lot_size_sqft DECIMAL(15,2),
    setback_requirements JSONB,
    permitted_uses TEXT[],
    conditional_uses TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Audit and Logging Tables
-- =============================================================================

-- Audit log for all property changes
CREATE TABLE IF NOT EXISTS audit_logs.property_audit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    operation VARCHAR(10) NOT NULL, -- INSERT, UPDATE, DELETE
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT
);

-- System activity log
CREATE TABLE IF NOT EXISTS audit_logs.system_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    activity_type VARCHAR(50) NOT NULL,
    activity_description TEXT,
    user_id VARCHAR(100),
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    metadata JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Cache Tables for Performance
-- =============================================================================

-- Materialized view for property search
CREATE TABLE IF NOT EXISTS cache_data.property_search_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID NOT NULL,
    search_vector TSVECTOR,
    geom_envelope GEOMETRY(POLYGON, 4326),
    property_summary JSONB,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Indexes for Performance
-- =============================================================================

-- Primary property indexes
CREATE INDEX IF NOT EXISTS idx_properties_property_id ON property_data.properties(property_id);
CREATE INDEX IF NOT EXISTS idx_properties_address ON property_data.properties USING gin(to_tsvector('english', address));
CREATE INDEX IF NOT EXISTS idx_properties_city_state ON property_data.properties(city, state);
CREATE INDEX IF NOT EXISTS idx_properties_zip_code ON property_data.properties(zip_code);
CREATE INDEX IF NOT EXISTS idx_properties_property_type ON property_data.properties(property_type);
CREATE INDEX IF NOT EXISTS idx_properties_assessment_status ON property_data.properties(assessment_status);
CREATE INDEX IF NOT EXISTS idx_properties_created_at ON property_data.properties(created_at);
CREATE INDEX IF NOT EXISTS idx_properties_updated_at ON property_data.properties(updated_at);
CREATE INDEX IF NOT EXISTS idx_properties_assessed_value ON property_data.properties(assessed_value);
CREATE INDEX IF NOT EXISTS idx_properties_market_value ON property_data.properties(market_value);
CREATE INDEX IF NOT EXISTS idx_properties_metadata_gin ON property_data.properties USING gin(metadata);

-- Spatial indexes
CREATE INDEX IF NOT EXISTS idx_property_boundaries_geom ON spatial_data.property_boundaries USING gist(boundary_geom);
CREATE INDEX IF NOT EXISTS idx_property_boundaries_centroid ON spatial_data.property_boundaries USING gist(centroid_geom);
CREATE INDEX IF NOT EXISTS idx_building_footprints_geom ON spatial_data.building_footprints USING gist(building_geom);
CREATE INDEX IF NOT EXISTS idx_municipalities_geom ON spatial_data.municipalities USING gist(boundary_geom);
CREATE INDEX IF NOT EXISTS idx_school_districts_geom ON spatial_data.school_districts USING gist(boundary_geom);
CREATE INDEX IF NOT EXISTS idx_zoning_districts_geom ON spatial_data.zoning_districts USING gist(boundary_geom);
CREATE INDEX IF NOT EXISTS idx_photos_location_geom ON property_data.photos USING gist(location_geom);

-- Assessment indexes
CREATE INDEX IF NOT EXISTS idx_assessments_property_id ON property_data.assessments(property_id);
CREATE INDEX IF NOT EXISTS idx_assessments_date ON property_data.assessments(assessment_date);
CREATE INDEX IF NOT EXISTS idx_assessments_status ON property_data.assessments(assessment_status);
CREATE INDEX IF NOT EXISTS idx_assessments_total_value ON property_data.assessments(total_value);

-- Document indexes
CREATE INDEX IF NOT EXISTS idx_documents_property_id ON property_data.documents(property_id);
CREATE INDEX IF NOT EXISTS idx_documents_type ON property_data.documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_name ON property_data.documents USING gin(to_tsvector('english', document_name));
CREATE INDEX IF NOT EXISTS idx_documents_metadata_gin ON property_data.documents USING gin(metadata);

-- Photo indexes
CREATE INDEX IF NOT EXISTS idx_photos_property_id ON property_data.photos(property_id);
CREATE INDEX IF NOT EXISTS idx_photos_type ON property_data.photos(photo_type);
CREATE INDEX IF NOT EXISTS idx_photos_date ON property_data.photos(photo_date);

-- Audit indexes
CREATE INDEX IF NOT EXISTS idx_property_audit_table_record ON audit_logs.property_audit(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_property_audit_changed_at ON audit_logs.property_audit(changed_at);
CREATE INDEX IF NOT EXISTS idx_property_audit_changed_by ON audit_logs.property_audit(changed_by);
CREATE INDEX IF NOT EXISTS idx_system_activity_type ON audit_logs.system_activity(activity_type);
CREATE INDEX IF NOT EXISTS idx_system_activity_user ON audit_logs.system_activity(user_id);
CREATE INDEX IF NOT EXISTS idx_system_activity_created ON audit_logs.system_activity(created_at);

-- Cache indexes
CREATE INDEX IF NOT EXISTS idx_search_cache_property_id ON cache_data.property_search_cache(property_id);
CREATE INDEX IF NOT EXISTS idx_search_cache_vector ON cache_data.property_search_cache USING gin(search_vector);
CREATE INDEX IF NOT EXISTS idx_search_cache_envelope ON cache_data.property_search_cache USING gist(geom_envelope);
CREATE INDEX IF NOT EXISTS idx_search_cache_summary ON cache_data.property_search_cache USING gin(property_summary);

-- =============================================================================
-- Triggers for Automatic Updates
-- =============================================================================

-- Function to update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers to relevant tables
DROP TRIGGER IF EXISTS update_properties_updated_at ON property_data.properties;
CREATE TRIGGER update_properties_updated_at
    BEFORE UPDATE ON property_data.properties
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_property_boundaries_updated_at ON spatial_data.property_boundaries;
CREATE TRIGGER update_property_boundaries_updated_at
    BEFORE UPDATE ON spatial_data.property_boundaries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_building_footprints_updated_at ON spatial_data.building_footprints;
CREATE TRIGGER update_building_footprints_updated_at
    BEFORE UPDATE ON spatial_data.building_footprints
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_assessments_updated_at ON property_data.assessments;
CREATE TRIGGER update_assessments_updated_at
    BEFORE UPDATE ON property_data.assessments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_documents_updated_at ON property_data.documents;
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON property_data.documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_photos_updated_at ON property_data.photos;
CREATE TRIGGER update_photos_updated_at
    BEFORE UPDATE ON property_data.photos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically calculate centroid for property boundaries
CREATE OR REPLACE FUNCTION calculate_boundary_centroid()
RETURNS TRIGGER AS $$
BEGIN
    NEW.centroid_geom = ST_Centroid(NEW.boundary_geom);
    NEW.area_sqft = ST_Area(ST_Transform(NEW.boundary_geom, 3857)) * 10.764; -- Convert sq meters to sq feet
    NEW.perimeter_ft = ST_Perimeter(ST_Transform(NEW.boundary_geom, 3857)) * 3.281; -- Convert meters to feet
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS calculate_boundary_metrics ON spatial_data.property_boundaries;
CREATE TRIGGER calculate_boundary_metrics
    BEFORE INSERT OR UPDATE ON spatial_data.property_boundaries
    FOR EACH ROW EXECUTE FUNCTION calculate_boundary_centroid();

-- =============================================================================
-- Views for Common Queries
-- =============================================================================

-- Comprehensive property view with spatial data
CREATE OR REPLACE VIEW property_data.properties_with_spatial AS
SELECT 
    p.*,
    pb.boundary_geom,
    pb.centroid_geom,
    pb.area_sqft as boundary_area_sqft,
    pb.perimeter_ft as boundary_perimeter_ft,
    ST_AsGeoJSON(pb.boundary_geom) as boundary_geojson,
    ST_AsGeoJSON(pb.centroid_geom) as centroid_geojson
FROM property_data.properties p
LEFT JOIN spatial_data.property_boundaries pb ON p.id = pb.property_id;

-- Property summary with latest assessment
CREATE OR REPLACE VIEW property_data.properties_with_latest_assessment AS
SELECT 
    p.*,
    a.assessment_date,
    a.assessed_by,
    a.land_value,
    a.improvement_value,
    a.total_value as latest_assessed_value,
    a.assessment_status as latest_assessment_status
FROM property_data.properties p
LEFT JOIN LATERAL (
    SELECT *
    FROM property_data.assessments
    WHERE property_id = p.id
    ORDER BY assessment_date DESC
    LIMIT 1
) a ON true;

-- =============================================================================
-- Spatial Functions
-- =============================================================================

-- Function to find properties within a radius of a point
CREATE OR REPLACE FUNCTION find_properties_within_radius(
    center_lat DECIMAL,
    center_lon DECIMAL,
    radius_miles DECIMAL
)
RETURNS TABLE(
    property_id UUID,
    property_code VARCHAR(50),
    address TEXT,
    distance_miles DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.property_id,
        p.address,
        ROUND(
            (ST_Distance(
                ST_Transform(pb.centroid_geom, 3857),
                ST_Transform(ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326), 3857)
            ) * 0.000621371)::DECIMAL, 2
        ) as distance_miles
    FROM property_data.properties p
    JOIN spatial_data.property_boundaries pb ON p.id = pb.property_id
    WHERE ST_DWithin(
        ST_Transform(pb.centroid_geom, 3857),
        ST_Transform(ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326), 3857),
        radius_miles * 1609.34  -- Convert miles to meters
    )
    ORDER BY distance_miles;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Insert Sample Data (Optional - for testing)
-- =============================================================================

-- Sample municipality
INSERT INTO spatial_data.municipalities (name, municipality_type, state, county, fips_code)
VALUES ('Sample City', 'city', 'Sample State', 'Sample County', '12345')
ON CONFLICT DO NOTHING;

-- Sample school district
INSERT INTO spatial_data.school_districts (name, district_code, district_type, state, grade_levels)
VALUES ('Sample School District', 'SSD001', 'unified', 'Sample State', 'K-12')
ON CONFLICT DO NOTHING;

-- Sample property (without spatial data)
INSERT INTO property_data.properties (
    property_id, address, city, state, zip_code, county, property_type,
    lot_size_sqft, building_sqft, year_built, bedrooms, bathrooms,
    assessed_value, market_value, owner_name, parcel_number
)
VALUES (
    'PROP001', '123 Main Street', 'Sample City', 'Sample State', '12345', 'Sample County', 'residential',
    7500.00, 2000.00, 1995, 3, 2.5,
    250000.00, 275000.00, 'John Doe', 'PAR123456'
)
ON CONFLICT (property_id) DO NOTHING;

-- =============================================================================
-- Grant Permissions
-- =============================================================================

-- Grant usage on schemas to application user (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
        GRANT USAGE ON SCHEMA property_data TO app_user;
        GRANT USAGE ON SCHEMA spatial_data TO app_user;
        GRANT USAGE ON SCHEMA audit_logs TO app_user;
        GRANT USAGE ON SCHEMA cache_data TO app_user;
        
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA property_data TO app_user;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA spatial_data TO app_user;
        GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA audit_logs TO app_user;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA cache_data TO app_user;
        
        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA property_data TO app_user;
        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA spatial_data TO app_user;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Could not grant permissions to app_user: %', SQLERRM;
END
$$;

-- =============================================================================
-- Database Statistics and Optimization
-- =============================================================================

-- Analyze all tables for query planning
ANALYZE;

-- Set up automatic vacuum and analyze
COMMENT ON DATABASE postgres IS 'Property Assessment Database with PostGIS';

-- =============================================================================
-- Completion Message
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Property Assessment Database initialization completed successfully!';
    RAISE NOTICE 'PostGIS version: %', PostGIS_Version();
    RAISE NOTICE 'Created schemas: property_data, spatial_data, audit_logs, cache_data';
    RAISE NOTICE 'Database is ready for property assessment operations';
END
$$;
