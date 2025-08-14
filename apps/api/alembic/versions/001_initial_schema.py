"""Initial schema with PostGIS support, indexes, constraints, and RLS

Revision ID: 001
Revises: 
Create Date: 2025-08-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables with PostGIS geometry columns, indexes, constraints, and RLS policies."""
    
    # Enable PostGIS extension
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis_topology')
    op.execute('CREATE EXTENSION IF NOT EXISTS fuzzystrmatch')
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create custom ENUM types
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE user_role AS ENUM ('owner', 'admin', 'member');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE footprint_type AS ENUM ('main', 'outbuilding', 'driveway');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE cv_artifact_type AS ENUM ('pool', 'tree_canopy', 'driveway');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE export_type AS ENUM ('csv', 'geojson', 'pdf');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE api_provider AS ENUM ('openai', 'anthropic', 'mapbox', 'maptiler', 'google');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Organizations table
    op.create_table('organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('address_line1', sa.String(length=255), nullable=True),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=50), nullable=True, server_default='US'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('subscription_tier', sa.String(length=50), nullable=False, server_default='basic'),
        sa.Column('settings', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('api_key', sa.String(length=255), nullable=True),
        sa.Column('api_rate_limit', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_organizations')),
        sa.UniqueConstraint('api_key', name=op.f('uq_organizations_api_key')),
        sa.CheckConstraint('api_rate_limit > 0', name=op.f('ck_organizations_positive_rate_limit')),
        sa.CheckConstraint("subscription_tier IN ('basic', 'professional', 'enterprise')", name=op.f('ck_organizations_valid_subscription_tier'))
    )
    
    # Create indexes for organizations
    op.create_index(op.f('ix_organizations_id'), 'organizations', ['id'], unique=False)
    op.create_index(op.f('ix_organizations_name'), 'organizations', ['name'], unique=False)
    op.create_index(op.f('ix_organizations_is_active'), 'organizations', ['is_active'], unique=False)
    
    # Add trigger for updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    op.execute("""
        CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('profile_settings', sa.Text(), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('verification_token', sa.String(length=255), nullable=True),
        sa.Column('reset_token', sa.String(length=255), nullable=True),
        sa.Column('reset_token_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_users_organization_id_organizations'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('email', name=op.f('uq_users_email')),
        sa.UniqueConstraint('username', name=op.f('uq_users_username')),
        sa.CheckConstraint("role IN ('admin', 'manager', 'user')", name=op.f('ck_users_valid_role')),
        sa.CheckConstraint('failed_login_attempts >= 0', name=op.f('ck_users_non_negative_failed_attempts'))
    )
    
    # Create indexes for users
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_organization_id'), 'users', ['organization_id'], unique=False)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_index(op.f('ix_users_is_active'), 'users', ['is_active'], unique=False)
    op.create_index(op.f('ix_users_last_login_at'), 'users', ['last_login_at'], unique=False)
    
    # Add trigger for users updated_at
    op.execute("""
        CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Enable RLS on users table
    op.execute('ALTER TABLE users ENABLE ROW LEVEL SECURITY')
    
    # User sessions table
    op.create_table('user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(length=255), nullable=False),
        sa.Column('refresh_token', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('device_info', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_activity', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_sessions_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_sessions')),
        sa.UniqueConstraint('session_token', name=op.f('uq_user_sessions_session_token')),
        sa.UniqueConstraint('refresh_token', name=op.f('uq_user_sessions_refresh_token'))
    )
    
    # Create indexes for user_sessions
    op.create_index(op.f('ix_user_sessions_id'), 'user_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_sessions_session_token'), 'user_sessions', ['session_token'], unique=True)
    op.create_index(op.f('ix_user_sessions_refresh_token'), 'user_sessions', ['refresh_token'], unique=True)
    op.create_index(op.f('ix_user_sessions_is_active'), 'user_sessions', ['is_active'], unique=False)
    op.create_index(op.f('ix_user_sessions_expires_at'), 'user_sessions', ['expires_at'], unique=False)
    
    # Zoning districts table
    op.create_table('zoning_districts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('jurisdiction', sa.String(length=100), nullable=False),
        sa.Column('municipality', sa.String(length=100), nullable=True),
        sa.Column('county', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('subcategory', sa.String(length=100), nullable=True),
        sa.Column('min_lot_size_sqft', sa.Float(), nullable=True),
        sa.Column('max_lot_coverage', sa.Float(), nullable=True),
        sa.Column('max_floor_area_ratio', sa.Float(), nullable=True),
        sa.Column('max_density_units_acre', sa.Float(), nullable=True),
        sa.Column('max_building_height_ft', sa.Float(), nullable=True),
        sa.Column('max_stories', sa.Integer(), nullable=True),
        sa.Column('min_building_setback_front_ft', sa.Float(), nullable=True),
        sa.Column('min_building_setback_rear_ft', sa.Float(), nullable=True),
        sa.Column('min_building_setback_side_ft', sa.Float(), nullable=True),
        sa.Column('min_parking_spaces_per_unit', sa.Float(), nullable=True),
        sa.Column('parking_requirements', sa.Text(), nullable=True),
        sa.Column('permitted_uses', sa.JSON(), nullable=True),
        sa.Column('conditional_uses', sa.JSON(), nullable=True),
        sa.Column('prohibited_uses', sa.JSON(), nullable=True),
        sa.Column('landscape_requirements', sa.Text(), nullable=True),
        sa.Column('architectural_standards', sa.Text(), nullable=True),
        sa.Column('environmental_requirements', sa.Text(), nullable=True),
        sa.Column('overlay_districts', sa.JSON(), nullable=True),
        sa.Column('historic_district', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('flood_overlay', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('impact_fees', sa.JSON(), nullable=True),
        sa.Column('permit_fees', sa.JSON(), nullable=True),
        sa.Column('administrative_approval', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('requires_conditional_use_permit', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('requires_variance', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('requires_public_hearing', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('boundary', geoalchemy2.types.Geometry('MULTIPOLYGON', srid=4326, spatial_index=False), nullable=True),
        sa.Column('regulation_text', sa.Text(), nullable=True),
        sa.Column('regulation_url', sa.String(length=500), nullable=True),
        sa.Column('ordinance_number', sa.String(length=100), nullable=True),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expiration_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_amended', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('attributes', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_zoning_districts')),
        sa.UniqueConstraint('code', name=op.f('uq_zoning_districts_code')),
        sa.CheckConstraint('max_lot_coverage >= 0 AND max_lot_coverage <= 100', name=op.f('ck_zoning_districts_valid_lot_coverage')),
        sa.CheckConstraint('max_floor_area_ratio >= 0', name=op.f('ck_zoning_districts_positive_far')),
        sa.CheckConstraint('max_density_units_acre >= 0', name=op.f('ck_zoning_districts_positive_density')),
        sa.CheckConstraint('max_building_height_ft >= 0', name=op.f('ck_zoning_districts_positive_height')),
        sa.CheckConstraint('max_stories >= 0', name=op.f('ck_zoning_districts_positive_stories'))
    )
    
    # Create indexes for zoning_districts
    op.create_index(op.f('ix_zoning_districts_id'), 'zoning_districts', ['id'], unique=False)
    op.create_index(op.f('ix_zoning_districts_code'), 'zoning_districts', ['code'], unique=True)
    op.create_index(op.f('ix_zoning_districts_jurisdiction'), 'zoning_districts', ['jurisdiction'], unique=False)
    op.create_index(op.f('ix_zoning_districts_municipality'), 'zoning_districts', ['municipality'], unique=False)
    op.create_index(op.f('ix_zoning_districts_county'), 'zoning_districts', ['county'], unique=False)
    op.create_index(op.f('ix_zoning_districts_state'), 'zoning_districts', ['state'], unique=False)
    op.create_index(op.f('ix_zoning_districts_category'), 'zoning_districts', ['category'], unique=False)
    op.create_index(op.f('ix_zoning_districts_is_active'), 'zoning_districts', ['is_active'], unique=False)
    
    # Create GIST index for boundary geometry
    op.execute('CREATE INDEX ix_zoning_districts_boundary_gist ON zoning_districts USING GIST (boundary)')
    
    # Add trigger for zoning_districts updated_at
    op.execute("""
        CREATE TRIGGER update_zoning_districts_updated_at BEFORE UPDATE ON zoning_districts
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Parcels table
    op.create_table('parcels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('parcel_id', sa.String(length=100), nullable=False),
        sa.Column('parcel_number', sa.String(length=100), nullable=True),
        sa.Column('county_parcel_id', sa.String(length=100), nullable=True),
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('street_number', sa.String(length=20), nullable=True),
        sa.Column('street_name', sa.String(length=200), nullable=True),
        sa.Column('unit_number', sa.String(length=50), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('county', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('geometry', geoalchemy2.types.Geometry('POLYGON', srid=4326, spatial_index=False), nullable=True),
        sa.Column('centroid', geoalchemy2.types.Geometry('POINT', srid=4326, spatial_index=False), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('area_sqft', sa.Float(), nullable=True),
        sa.Column('area_acres', sa.Float(), nullable=True),
        sa.Column('frontage_ft', sa.Float(), nullable=True),
        sa.Column('depth_ft', sa.Float(), nullable=True),
        sa.Column('zoning_code', sa.String(length=50), nullable=True),
        sa.Column('zoning_description', sa.Text(), nullable=True),
        sa.Column('land_use_code', sa.String(length=50), nullable=True),
        sa.Column('land_use_description', sa.Text(), nullable=True),
        sa.Column('property_type', sa.String(length=100), nullable=True),
        sa.Column('property_subtype', sa.String(length=100), nullable=True),
        sa.Column('lot_type', sa.String(length=50), nullable=True),
        sa.Column('corner_lot', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('owner_name', sa.String(length=500), nullable=True),
        sa.Column('owner_address', sa.Text(), nullable=True),
        sa.Column('owner_type', sa.String(length=50), nullable=True),
        sa.Column('assessed_value', sa.Float(), nullable=True),
        sa.Column('market_value', sa.Float(), nullable=True),
        sa.Column('tax_year', sa.Integer(), nullable=True),
        sa.Column('annual_taxes', sa.Float(), nullable=True),
        sa.Column('building_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_building_sqft', sa.Float(), nullable=True),
        sa.Column('year_built', sa.Integer(), nullable=True),
        sa.Column('water_available', sa.Boolean(), nullable=True),
        sa.Column('sewer_available', sa.Boolean(), nullable=True),
        sa.Column('electric_available', sa.Boolean(), nullable=True),
        sa.Column('gas_available', sa.Boolean(), nullable=True),
        sa.Column('flood_zone', sa.String(length=50), nullable=True),
        sa.Column('wetlands', sa.Boolean(), nullable=True),
        sa.Column('steep_slopes', sa.Boolean(), nullable=True),
        sa.Column('environmental_constraints', sa.Text(), nullable=True),
        sa.Column('data_source', sa.String(length=100), nullable=True),
        sa.Column('data_quality', sa.String(length=50), nullable=False, server_default='unknown'),
        sa.Column('last_verified', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attributes', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_parcels_organization_id_organizations'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_parcels')),
        sa.CheckConstraint('area_sqft >= 0', name=op.f('ck_parcels_positive_area_sqft')),
        sa.CheckConstraint('area_acres >= 0', name=op.f('ck_parcels_positive_area_acres')),
        sa.CheckConstraint('assessed_value >= 0', name=op.f('ck_parcels_positive_assessed_value')),
        sa.CheckConstraint('market_value >= 0', name=op.f('ck_parcels_positive_market_value')),
        sa.CheckConstraint('annual_taxes >= 0', name=op.f('ck_parcels_positive_annual_taxes')),
        sa.CheckConstraint('building_count >= 0', name=op.f('ck_parcels_non_negative_building_count')),
        sa.CheckConstraint('latitude >= -90 AND latitude <= 90', name=op.f('ck_parcels_valid_latitude')),
        sa.CheckConstraint('longitude >= -180 AND longitude <= 180', name=op.f('ck_parcels_valid_longitude')),
        sa.CheckConstraint("data_quality IN ('high', 'medium', 'low', 'unknown')", name=op.f('ck_parcels_valid_data_quality'))
    )
    
    # Create indexes for parcels
    op.create_index(op.f('ix_parcels_id'), 'parcels', ['id'], unique=False)
    op.create_index(op.f('ix_parcels_organization_id'), 'parcels', ['organization_id'], unique=False)
    op.create_index(op.f('ix_parcels_parcel_id'), 'parcels', ['parcel_id'], unique=False)
    op.create_index(op.f('ix_parcels_parcel_number'), 'parcels', ['parcel_number'], unique=False)
    op.create_index(op.f('ix_parcels_county_parcel_id'), 'parcels', ['county_parcel_id'], unique=False)
    op.create_index(op.f('ix_parcels_address'), 'parcels', ['address'], unique=False)
    op.create_index(op.f('ix_parcels_city'), 'parcels', ['city'], unique=False)
    op.create_index(op.f('ix_parcels_county'), 'parcels', ['county'], unique=False)
    op.create_index(op.f('ix_parcels_state'), 'parcels', ['state'], unique=False)
    op.create_index(op.f('ix_parcels_postal_code'), 'parcels', ['postal_code'], unique=False)
    op.create_index(op.f('ix_parcels_latitude'), 'parcels', ['latitude'], unique=False)
    op.create_index(op.f('ix_parcels_longitude'), 'parcels', ['longitude'], unique=False)
    op.create_index(op.f('ix_parcels_zoning_code'), 'parcels', ['zoning_code'], unique=False)
    op.create_index(op.f('ix_parcels_property_type'), 'parcels', ['property_type'], unique=False)
    op.create_index(op.f('ix_parcels_is_active'), 'parcels', ['is_active'], unique=False)
    
    # Create composite indexes for common queries
    op.create_index('ix_parcels_org_city', 'parcels', ['organization_id', 'city'], unique=False)
    op.create_index('ix_parcels_org_state', 'parcels', ['organization_id', 'state'], unique=False)
    op.create_index('ix_parcels_org_zoning', 'parcels', ['organization_id', 'zoning_code'], unique=False)
    
    # Create GIST indexes for geometry columns
    op.execute('CREATE INDEX ix_parcels_geometry_gist ON parcels USING GIST (geometry)')
    op.execute('CREATE INDEX ix_parcels_centroid_gist ON parcels USING GIST (centroid)')
    
    # Add trigger for parcels updated_at
    op.execute("""
        CREATE TRIGGER update_parcels_updated_at BEFORE UPDATE ON parcels
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Building footprints table
    op.create_table('building_footprints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parcel_id', sa.Integer(), nullable=False),
        sa.Column('building_id', sa.String(length=100), nullable=True),
        sa.Column('building_name', sa.String(length=200), nullable=True),
        sa.Column('geometry', geoalchemy2.types.Geometry('POLYGON', srid=4326, spatial_index=False), nullable=False),
        sa.Column('centroid', geoalchemy2.types.Geometry('POINT', srid=4326, spatial_index=False), nullable=True),
        sa.Column('area_sqft', sa.Float(), nullable=True),
        sa.Column('perimeter_ft', sa.Float(), nullable=True),
        sa.Column('height_ft', sa.Float(), nullable=True),
        sa.Column('stories', sa.Integer(), nullable=True),
        sa.Column('building_type', sa.String(length=100), nullable=True),
        sa.Column('occupancy_class', sa.String(length=50), nullable=True),
        sa.Column('use_description', sa.Text(), nullable=True),
        sa.Column('construction_type', sa.String(length=100), nullable=True),
        sa.Column('roof_type', sa.String(length=100), nullable=True),
        sa.Column('foundation_type', sa.String(length=100), nullable=True),
        sa.Column('exterior_material', sa.String(length=100), nullable=True),
        sa.Column('year_built', sa.Integer(), nullable=True),
        sa.Column('year_renovated', sa.Integer(), nullable=True),
        sa.Column('condition', sa.String(length=50), nullable=True),
        sa.Column('hvac_type', sa.String(length=100), nullable=True),
        sa.Column('heating_fuel', sa.String(length=50), nullable=True),
        sa.Column('electrical_service', sa.String(length=50), nullable=True),
        sa.Column('plumbing_type', sa.String(length=50), nullable=True),
        sa.Column('ada_compliant', sa.Boolean(), nullable=True),
        sa.Column('elevator', sa.Boolean(), nullable=True),
        sa.Column('sprinkler_system', sa.Boolean(), nullable=True),
        sa.Column('security_system', sa.Boolean(), nullable=True),
        sa.Column('energy_rating', sa.String(length=10), nullable=True),
        sa.Column('insulation_type', sa.String(length=100), nullable=True),
        sa.Column('window_type', sa.String(length=100), nullable=True),
        sa.Column('data_source', sa.String(length=100), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('detection_method', sa.String(length=100), nullable=True),
        sa.Column('geometry_quality', sa.String(length=50), nullable=False, server_default='unknown'),
        sa.Column('attribute_completeness', sa.Float(), nullable=True),
        sa.Column('is_primary_structure', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_accessory_structure', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_demolished', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('attributes', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['parcel_id'], ['parcels.id'], name=op.f('fk_building_footprints_parcel_id_parcels'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_building_footprints')),
        sa.CheckConstraint('area_sqft >= 0', name=op.f('ck_building_footprints_positive_area')),
        sa.CheckConstraint('height_ft >= 0', name=op.f('ck_building_footprints_positive_height')),
        sa.CheckConstraint('stories >= 0', name=op.f('ck_building_footprints_positive_stories')),
        sa.CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name=op.f('ck_building_footprints_valid_confidence')),
        sa.CheckConstraint('attribute_completeness >= 0 AND attribute_completeness <= 1', name=op.f('ck_building_footprints_valid_completeness')),
        sa.CheckConstraint("condition IN ('excellent', 'good', 'fair', 'poor') OR condition IS NULL", name=op.f('ck_building_footprints_valid_condition')),
        sa.CheckConstraint("geometry_quality IN ('high', 'medium', 'low', 'unknown')", name=op.f('ck_building_footprints_valid_geometry_quality'))
    )
    
    # Create indexes for building_footprints
    op.create_index(op.f('ix_building_footprints_id'), 'building_footprints', ['id'], unique=False)
    op.create_index(op.f('ix_building_footprints_parcel_id'), 'building_footprints', ['parcel_id'], unique=False)
    op.create_index(op.f('ix_building_footprints_building_id'), 'building_footprints', ['building_id'], unique=False)
    op.create_index(op.f('ix_building_footprints_building_type'), 'building_footprints', ['building_type'], unique=False)
    op.create_index(op.f('ix_building_footprints_year_built'), 'building_footprints', ['year_built'], unique=False)
    op.create_index(op.f('ix_building_footprints_data_source'), 'building_footprints', ['data_source'], unique=False)
    op.create_index(op.f('ix_building_footprints_is_primary'), 'building_footprints', ['is_primary_structure'], unique=False)
    
    # Create GIST indexes for geometry columns
    op.execute('CREATE INDEX ix_building_footprints_geometry_gist ON building_footprints USING GIST (geometry)')
    op.execute('CREATE INDEX ix_building_footprints_centroid_gist ON building_footprints USING GIST (centroid)')
    
    # Add trigger for building_footprints updated_at
    op.execute("""
        CREATE TRIGGER update_building_footprints_updated_at BEFORE UPDATE ON building_footprints
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Listings table
    op.create_table('listings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parcel_id', sa.Integer(), nullable=True),
        sa.Column('mls_number', sa.String(length=100), nullable=True),
        sa.Column('listing_id', sa.String(length=100), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('listing_type', sa.String(length=50), nullable=False),
        sa.Column('property_type', sa.String(length=100), nullable=True),
        sa.Column('property_subtype', sa.String(length=100), nullable=True),
        sa.Column('list_price', sa.Float(), nullable=True),
        sa.Column('original_price', sa.Float(), nullable=True),
        sa.Column('sold_price', sa.Float(), nullable=True),
        sa.Column('price_per_sqft', sa.Float(), nullable=True),
        sa.Column('monthly_rent', sa.Float(), nullable=True),
        sa.Column('annual_rent', sa.Float(), nullable=True),
        sa.Column('rent_per_sqft', sa.Float(), nullable=True),
        sa.Column('bedrooms', sa.Integer(), nullable=True),
        sa.Column('bathrooms', sa.Float(), nullable=True),
        sa.Column('total_rooms', sa.Integer(), nullable=True),
        sa.Column('living_area_sqft', sa.Float(), nullable=True),
        sa.Column('total_area_sqft', sa.Float(), nullable=True),
        sa.Column('lot_size_sqft', sa.Float(), nullable=True),
        sa.Column('lot_size_acres', sa.Float(), nullable=True),
        sa.Column('year_built', sa.Integer(), nullable=True),
        sa.Column('stories', sa.Integer(), nullable=True),
        sa.Column('garage_spaces', sa.Integer(), nullable=True),
        sa.Column('parking_spaces', sa.Integer(), nullable=True),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('appliances', sa.JSON(), nullable=True),
        sa.Column('utilities', sa.JSON(), nullable=True),
        sa.Column('condition', sa.String(length=50), nullable=True),
        sa.Column('renovation_year', sa.Integer(), nullable=True),
        sa.Column('elementary_school', sa.String(length=200), nullable=True),
        sa.Column('middle_school', sa.String(length=200), nullable=True),
        sa.Column('high_school', sa.String(length=200), nullable=True),
        sa.Column('school_district', sa.String(length=200), nullable=True),
        sa.Column('hoa_fee', sa.Float(), nullable=True),
        sa.Column('hoa_frequency', sa.String(length=50), nullable=True),
        sa.Column('hoa_includes', sa.JSON(), nullable=True),
        sa.Column('property_taxes', sa.Float(), nullable=True),
        sa.Column('tax_year', sa.Integer(), nullable=True),
        sa.Column('assessment_value', sa.Float(), nullable=True),
        sa.Column('listing_agent_name', sa.String(length=200), nullable=True),
        sa.Column('listing_agent_phone', sa.String(length=50), nullable=True),
        sa.Column('listing_agent_email', sa.String(length=255), nullable=True),
        sa.Column('listing_office', sa.String(length=200), nullable=True),
        sa.Column('showing_instructions', sa.Text(), nullable=True),
        sa.Column('showing_requirements', sa.Text(), nullable=True),
        sa.Column('lockbox_type', sa.String(length=50), nullable=True),
        sa.Column('marketing_description', sa.Text(), nullable=True),
        sa.Column('private_remarks', sa.Text(), nullable=True),
        sa.Column('virtual_tour_url', sa.String(length=500), nullable=True),
        sa.Column('photo_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('list_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pending_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sold_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('close_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expiration_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('days_on_market', sa.Integer(), nullable=True),
        sa.Column('cumulative_days_on_market', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('status_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('data_quality', sa.String(length=50), nullable=False, server_default='unknown'),
        sa.Column('last_verified', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attributes', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parcel_id'], ['parcels.id'], name=op.f('fk_listings_parcel_id_parcels'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_listings')),
        sa.UniqueConstraint('mls_number', name=op.f('uq_listings_mls_number')),
        sa.CheckConstraint('list_price >= 0', name=op.f('ck_listings_positive_list_price')),
        sa.CheckConstraint('sold_price >= 0', name=op.f('ck_listings_positive_sold_price')),
        sa.CheckConstraint('monthly_rent >= 0', name=op.f('ck_listings_positive_monthly_rent')),
        sa.CheckConstraint('bedrooms >= 0', name=op.f('ck_listings_non_negative_bedrooms')),
        sa.CheckConstraint('bathrooms >= 0', name=op.f('ck_listings_non_negative_bathrooms')),
        sa.CheckConstraint('living_area_sqft >= 0', name=op.f('ck_listings_positive_living_area')),
        sa.CheckConstraint('lot_size_sqft >= 0', name=op.f('ck_listings_positive_lot_size')),
        sa.CheckConstraint('photo_count >= 0', name=op.f('ck_listings_non_negative_photo_count')),
        sa.CheckConstraint('days_on_market >= 0', name=op.f('ck_listings_non_negative_dom')),
        sa.CheckConstraint("listing_type IN ('sale', 'rent', 'sold', 'rented')", name=op.f('ck_listings_valid_listing_type')),
        sa.CheckConstraint("status IN ('active', 'pending', 'sold', 'expired', 'withdrawn', 'cancelled')", name=op.f('ck_listings_valid_status'))
    )
    
    # Create indexes for listings
    op.create_index(op.f('ix_listings_id'), 'listings', ['id'], unique=False)
    op.create_index(op.f('ix_listings_parcel_id'), 'listings', ['parcel_id'], unique=False)
    op.create_index(op.f('ix_listings_mls_number'), 'listings', ['mls_number'], unique=True)
    op.create_index(op.f('ix_listings_listing_id'), 'listings', ['listing_id'], unique=False)
    op.create_index(op.f('ix_listings_source'), 'listings', ['source'], unique=False)
    op.create_index(op.f('ix_listings_address'), 'listings', ['address'], unique=False)
    op.create_index(op.f('ix_listings_city'), 'listings', ['city'], unique=False)
    op.create_index(op.f('ix_listings_state'), 'listings', ['state'], unique=False)
    op.create_index(op.f('ix_listings_postal_code'), 'listings', ['postal_code'], unique=False)
    op.create_index(op.f('ix_listings_listing_type'), 'listings', ['listing_type'], unique=False)
    op.create_index(op.f('ix_listings_property_type'), 'listings', ['property_type'], unique=False)
    op.create_index(op.f('ix_listings_status'), 'listings', ['status'], unique=False)
    op.create_index(op.f('ix_listings_is_active'), 'listings', ['is_active'], unique=False)
    op.create_index(op.f('ix_listings_list_date'), 'listings', ['list_date'], unique=False)
    op.create_index(op.f('ix_listings_sold_date'), 'listings', ['sold_date'], unique=False)
    
    # Create composite indexes for common queries
    op.create_index('ix_listings_type_status', 'listings', ['listing_type', 'status'], unique=False)
    op.create_index('ix_listings_city_type', 'listings', ['city', 'listing_type'], unique=False)
    op.create_index('ix_listings_price_range', 'listings', ['list_price', 'bedrooms'], unique=False)
    
    # Add trigger for listings updated_at
    op.execute("""
        CREATE TRIGGER update_listings_updated_at BEFORE UPDATE ON listings
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Property assessments table
    op.create_table('property_assessments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('parcel_id', sa.Integer(), nullable=False),
        sa.Column('assessment_id', sa.String(length=100), nullable=False),
        sa.Column('assessment_name', sa.String(length=200), nullable=True),
        sa.Column('assessment_type', sa.String(length=100), nullable=False),
        sa.Column('requested_by', sa.String(length=200), nullable=True),
        sa.Column('client_reference', sa.String(length=100), nullable=True),
        sa.Column('purpose', sa.Text(), nullable=True),
        sa.Column('proposed_use', sa.String(length=200), nullable=True),
        sa.Column('proposed_units', sa.Integer(), nullable=True),
        sa.Column('proposed_sqft', sa.Float(), nullable=True),
        sa.Column('proposed_stories', sa.Integer(), nullable=True),
        sa.Column('proposed_height_ft', sa.Float(), nullable=True),
        sa.Column('zoning_compliant', sa.Boolean(), nullable=True),
        sa.Column('development_feasible', sa.Boolean(), nullable=True),
        sa.Column('max_buildable_sqft', sa.Float(), nullable=True),
        sa.Column('max_units', sa.Integer(), nullable=True),
        sa.Column('max_stories', sa.Integer(), nullable=True),
        sa.Column('max_height_ft', sa.Float(), nullable=True),
        sa.Column('required_setbacks', sa.JSON(), nullable=True),
        sa.Column('available_setbacks', sa.JSON(), nullable=True),
        sa.Column('setback_compliant', sa.Boolean(), nullable=True),
        sa.Column('buildable_area_sqft', sa.Float(), nullable=True),
        sa.Column('required_parking_spaces', sa.Integer(), nullable=True),
        sa.Column('available_parking_spaces', sa.Integer(), nullable=True),
        sa.Column('parking_compliant', sa.Boolean(), nullable=True),
        sa.Column('max_lot_coverage', sa.Float(), nullable=True),
        sa.Column('proposed_lot_coverage', sa.Float(), nullable=True),
        sa.Column('coverage_compliant', sa.Boolean(), nullable=True),
        sa.Column('max_far', sa.Float(), nullable=True),
        sa.Column('proposed_far', sa.Float(), nullable=True),
        sa.Column('far_compliant', sa.Boolean(), nullable=True),
        sa.Column('max_density', sa.Float(), nullable=True),
        sa.Column('proposed_density', sa.Float(), nullable=True),
        sa.Column('density_compliant', sa.Boolean(), nullable=True),
        sa.Column('max_allowed_height_ft', sa.Float(), nullable=True),
        sa.Column('height_compliant', sa.Boolean(), nullable=True),
        sa.Column('height_restrictions', sa.JSON(), nullable=True),
        sa.Column('flood_zone_impact', sa.Boolean(), nullable=True),
        sa.Column('wetland_impact', sa.Boolean(), nullable=True),
        sa.Column('slope_impact', sa.Boolean(), nullable=True),
        sa.Column('environmental_compliant', sa.Boolean(), nullable=True),
        sa.Column('environmental_notes', sa.Text(), nullable=True),
        sa.Column('utilities_available', sa.JSON(), nullable=True),
        sa.Column('access_adequate', sa.Boolean(), nullable=True),
        sa.Column('infrastructure_notes', sa.Text(), nullable=True),
        sa.Column('estimated_development_cost', sa.Float(), nullable=True),
        sa.Column('estimated_permit_fees', sa.Float(), nullable=True),
        sa.Column('estimated_impact_fees', sa.Float(), nullable=True),
        sa.Column('estimated_total_cost', sa.Float(), nullable=True),
        sa.Column('comparable_sales', sa.JSON(), nullable=True),
        sa.Column('estimated_market_value', sa.Float(), nullable=True),
        sa.Column('estimated_rent', sa.Float(), nullable=True),
        sa.Column('market_notes', sa.Text(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('alternative_scenarios', sa.JSON(), nullable=True),
        sa.Column('next_steps', sa.JSON(), nullable=True),
        sa.Column('permits_required', sa.JSON(), nullable=True),
        sa.Column('approvals_required', sa.JSON(), nullable=True),
        sa.Column('estimated_approval_time', sa.String(length=100), nullable=True),
        sa.Column('risk_level', sa.String(length=50), nullable=True),
        sa.Column('risk_factors', sa.JSON(), nullable=True),
        sa.Column('mitigation_strategies', sa.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('data_quality', sa.String(length=50), nullable=False, server_default='unknown'),
        sa.Column('limitations', sa.Text(), nullable=True),
        sa.Column('report_generated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('report_url', sa.String(length=500), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('progress_percentage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processing_time_seconds', sa.Float(), nullable=True),
        sa.Column('processing_notes', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('attributes', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_property_assessments_organization_id_organizations'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parcel_id'], ['parcels.id'], name=op.f('fk_property_assessments_parcel_id_parcels'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_property_assessments')),
        sa.UniqueConstraint('assessment_id', name=op.f('uq_property_assessments_assessment_id')),
        sa.CheckConstraint('proposed_units >= 0', name=op.f('ck_property_assessments_positive_proposed_units')),
        sa.CheckConstraint('proposed_sqft >= 0', name=op.f('ck_property_assessments_positive_proposed_sqft')),
        sa.CheckConstraint('max_buildable_sqft >= 0', name=op.f('ck_property_assessments_positive_max_buildable_sqft')),
        sa.CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name=op.f('ck_property_assessments_valid_confidence')),
        sa.CheckConstraint('progress_percentage >= 0 AND progress_percentage <= 100', name=op.f('ck_property_assessments_valid_progress')),
        sa.CheckConstraint("status IN ('pending', 'in_progress', 'completed', 'failed')", name=op.f('ck_property_assessments_valid_status')),
        sa.CheckConstraint("risk_level IN ('low', 'medium', 'high') OR risk_level IS NULL", name=op.f('ck_property_assessments_valid_risk_level')),
        sa.CheckConstraint("assessment_type IN ('zoning', 'development', 'feasibility', 'compliance', 'market')", name=op.f('ck_property_assessments_valid_assessment_type'))
    )
    
    # Create indexes for property_assessments
    op.create_index(op.f('ix_property_assessments_id'), 'property_assessments', ['id'], unique=False)
    op.create_index(op.f('ix_property_assessments_organization_id'), 'property_assessments', ['organization_id'], unique=False)
    op.create_index(op.f('ix_property_assessments_parcel_id'), 'property_assessments', ['parcel_id'], unique=False)
    op.create_index(op.f('ix_property_assessments_assessment_id'), 'property_assessments', ['assessment_id'], unique=True)
    op.create_index(op.f('ix_property_assessments_assessment_type'), 'property_assessments', ['assessment_type'], unique=False)
    op.create_index(op.f('ix_property_assessments_status'), 'property_assessments', ['status'], unique=False)
    op.create_index(op.f('ix_property_assessments_created_at'), 'property_assessments', ['created_at'], unique=False)
    op.create_index(op.f('ix_property_assessments_completed_at'), 'property_assessments', ['completed_at'], unique=False)
    
    # Create composite indexes for common queries
    op.create_index('ix_property_assessments_org_status', 'property_assessments', ['organization_id', 'status'], unique=False)
    op.create_index('ix_property_assessments_org_type', 'property_assessments', ['organization_id', 'assessment_type'], unique=False)
    
    # Add trigger for property_assessments updated_at
    op.execute("""
        CREATE TRIGGER update_property_assessments_updated_at BEFORE UPDATE ON property_assessments
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Audit logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_category', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=200), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=True),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('resource_name', sa.String(length=200), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_method', sa.String(length=10), nullable=True),
        sa.Column('request_url', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('old_values', sa.JSON(), nullable=True),
        sa.Column('new_values', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('correlation_id', sa.String(length=255), nullable=True),
        sa.Column('country', sa.String(length=2), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('browser', sa.String(length=100), nullable=True),
        sa.Column('operating_system', sa.String(length=100), nullable=True),
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.Column('anomaly_detected', sa.String(length=50), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_audit_logs_user_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs')),
        sa.CheckConstraint('risk_score >= 0 AND risk_score <= 100', name=op.f('ck_audit_logs_valid_risk_score')),
        sa.CheckConstraint("event_category IN ('auth', 'data', 'admin', 'system')", name=op.f('ck_audit_logs_valid_event_category')),
        sa.CheckConstraint("status IN ('success', 'failure', 'error')", name=op.f('ck_audit_logs_valid_status')),
        sa.CheckConstraint("anomaly_detected IN ('none', 'low', 'medium', 'high') OR anomaly_detected IS NULL", name=op.f('ck_audit_logs_valid_anomaly'))
    )
    
    # Create indexes for audit_logs
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_event_type'), 'audit_logs', ['event_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_event_category'), 'audit_logs', ['event_category'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_type'), 'audit_logs', ['resource_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_id'), 'audit_logs', ['resource_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_status'), 'audit_logs', ['status'], unique=False)
    op.create_index(op.f('ix_audit_logs_session_id'), 'audit_logs', ['session_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_correlation_id'), 'audit_logs', ['correlation_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    
    # Create composite indexes for common audit queries
    op.create_index('ix_audit_logs_user_event', 'audit_logs', ['user_id', 'event_type'], unique=False)
    op.create_index('ix_audit_logs_resource_action', 'audit_logs', ['resource_type', 'resource_id'], unique=False)
    op.create_index('ix_audit_logs_security_events', 'audit_logs', ['event_category', 'status', 'created_at'], unique=False)
    
    # Enable RLS on multi-tenant tables
    op.execute('ALTER TABLE users ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY')
    
    # Create RLS policies for organization isolation
    op.execute("""
        CREATE POLICY users_org_isolation ON users
        FOR ALL
        USING (organization_id = current_setting('app.org_id', true)::int)
        WITH CHECK (organization_id = current_setting('app.org_id', true)::int)
    """)
    
    op.execute("""
        CREATE POLICY audit_logs_user_isolation ON audit_logs
        FOR ALL
        USING (
            user_id IS NULL OR 
            user_id IN (
                SELECT id FROM users 
                WHERE organization_id = current_setting('app.org_id', true)::int
            )
        )
    """)
    
    # Create foreign key constraint from parcels to zoning_districts (after both tables exist)
    op.create_foreign_key(
        op.f('fk_parcels_zoning_code_zoning_districts'),
        'parcels', 'zoning_districts',
        ['zoning_code'], ['code'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Drop all tables and extensions."""
    
    # Drop tables in reverse order (due to foreign key constraints)
    op.drop_table('audit_logs')
    op.drop_table('property_assessments')
    op.drop_table('listings')
    op.drop_table('building_footprints')
    op.drop_table('parcels')
    op.drop_table('zoning_districts')
    op.drop_table('user_sessions')
    op.drop_table('users')
    op.drop_table('organizations')
    
    # Drop the update trigger function
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')
    
    # Drop custom types
    op.execute('DROP TYPE IF EXISTS api_provider')
    op.execute('DROP TYPE IF EXISTS export_type')
    op.execute('DROP TYPE IF EXISTS cv_artifact_type')
    op.execute('DROP TYPE IF EXISTS footprint_type')
    op.execute('DROP TYPE IF EXISTS user_role')
    
    # Note: We don't drop PostGIS extensions as they might be used by other databases