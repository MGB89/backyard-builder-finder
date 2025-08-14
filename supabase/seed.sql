-- Supabase seed data for development
-- This file is run automatically when you run `supabase db reset`

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create pgboss schema for job queue (if using pg-boss)
CREATE SCHEMA IF NOT EXISTS pgboss;

-- Insert sample organization for development
INSERT INTO public.organizations (
  id,
  name,
  display_name,
  subscription_tier,
  api_rate_limit,
  is_active
) VALUES (
  'org-sample-uuid-001',
  'demo-organization',
  'Demo Organization',
  'pro',
  1000,
  true
) ON CONFLICT (id) DO NOTHING;

-- Insert sample user for development
INSERT INTO public.users (
  id,
  org_id,
  email,
  first_name,
  last_name,
  role,
  is_active,
  is_verified,
  oauth_provider,
  oauth_provider_id
) VALUES (
  'user-sample-uuid-001',
  'org-sample-uuid-001',
  'demo@example.com',
  'Demo',
  'User',
  'owner',
  true,
  true,
  'google',
  'google-oauth-id-123'
) ON CONFLICT (id) DO NOTHING;

-- Insert sample LA area search for development
INSERT INTO public.searches (
  id,
  user_id,
  org_id,
  name,
  area_geom,
  filters,
  status,
  stage,
  total_parcels,
  eligible_parcels
) VALUES (
  'search-sample-uuid-001',
  'user-sample-uuid-001',
  'org-sample-uuid-001',
  'LA Demo Search - 1200 sq ft, No Pool',
  ST_GeomFromText('POLYGON((-118.5 33.9, -118.2 33.9, -118.2 34.1, -118.5 34.1, -118.5 33.9))', 4326),
  '{
    "unitSize": 1200,
    "excludePools": true,
    "zoningCodes": ["R1", "R2"],
    "maxLotCoverage": 0.4
  }',
  'completed',
  'fit_test',
  5000,
  150
) ON CONFLICT (id) DO NOTHING;

-- Insert sample export for development
INSERT INTO public.exports (
  id,
  user_id,
  org_id,
  search_id,
  format,
  status,
  file_path,
  download_count
) VALUES (
  'export-sample-uuid-001',
  'user-sample-uuid-001',
  'org-sample-uuid-001',
  'search-sample-uuid-001',
  'geojson',
  'completed',
  'exports/demo/sample-export.geojson',
  0
) ON CONFLICT (id) DO NOTHING;

-- Insert sample audit log entry
INSERT INTO public.audit_logs (
  id,
  user_id,
  org_id,
  event_type,
  event_category,
  action,
  resource_type,
  resource_id,
  status,
  ip_address,
  user_agent
) VALUES (
  'audit-sample-uuid-001',
  'user-sample-uuid-001',
  'org-sample-uuid-001',
  'search',
  'data',
  'Search executed successfully',
  'search',
  'search-sample-uuid-001',
  'success',
  '127.0.0.1',
  'Demo User Agent'
) ON CONFLICT (id) DO NOTHING;