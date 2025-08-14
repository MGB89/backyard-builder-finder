-- Row Level Security (RLS) policies for multi-tenant isolation
-- This ensures users can only access data from their own organization

-- Enable RLS on all tables
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.searches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parcels ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.building_footprints ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.zoning_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.derived_buildable ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cv_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- Helper function to get current user's organization ID from JWT claims
CREATE OR REPLACE FUNCTION get_current_org_id()
RETURNS UUID AS $$
BEGIN
    -- Get org_id from JWT custom claims
    RETURN COALESCE(
        (current_setting('request.jwt.claims', true)::json->>'org_id')::uuid,
        NULL
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Helper function to get current user ID from JWT claims
CREATE OR REPLACE FUNCTION get_current_user_id()
RETURNS UUID AS $$
BEGIN
    -- Get user_id from JWT custom claims or sub claim
    RETURN COALESCE(
        (current_setting('request.jwt.claims', true)::json->>'user_id')::uuid,
        (current_setting('request.jwt.claims', true)::json->>'sub')::uuid,
        NULL
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Helper function to check if current user is admin/owner
CREATE OR REPLACE FUNCTION is_current_user_admin()
RETURNS BOOLEAN AS $$
DECLARE
    user_role TEXT;
BEGIN
    SELECT role INTO user_role 
    FROM public.users 
    WHERE id = get_current_user_id() 
    AND org_id = get_current_org_id();
    
    RETURN user_role IN ('admin', 'owner');
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Organizations policies
-- Users can only see their own organization
CREATE POLICY "Users can view own organization" ON public.organizations
    FOR SELECT
    USING (id = get_current_org_id());

-- Only owners can update organization details
CREATE POLICY "Owners can update organization" ON public.organizations
    FOR UPDATE
    USING (
        id = get_current_org_id() AND
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE users.org_id = organizations.id 
            AND users.id = get_current_user_id() 
            AND users.role = 'owner'
        )
    );

-- Users policies
-- Users can see other users in their organization
CREATE POLICY "Users can view org members" ON public.users
    FOR SELECT
    USING (org_id = get_current_org_id());

-- Users can update their own profile
CREATE POLICY "Users can update own profile" ON public.users
    FOR UPDATE
    USING (id = get_current_user_id() AND org_id = get_current_org_id());

-- Admins can update users in their org
CREATE POLICY "Admins can update org users" ON public.users
    FOR UPDATE
    USING (
        org_id = get_current_org_id() AND
        is_current_user_admin()
    );

-- Only owners can delete users
CREATE POLICY "Owners can delete users" ON public.users
    FOR DELETE
    USING (
        org_id = get_current_org_id() AND
        EXISTS (
            SELECT 1 FROM public.users owner_check
            WHERE owner_check.id = get_current_user_id() 
            AND owner_check.org_id = get_current_org_id()
            AND owner_check.role = 'owner'
        )
    );

-- User API Keys policies
-- Users can manage their own API keys
CREATE POLICY "Users can manage own API keys" ON public.user_api_keys
    FOR ALL
    USING (
        user_id = get_current_user_id() AND 
        org_id = get_current_org_id()
    );

-- Admins can view all API keys in their org (but not the actual keys)
CREATE POLICY "Admins can view org API keys" ON public.user_api_keys
    FOR SELECT
    USING (
        org_id = get_current_org_id() AND
        is_current_user_admin()
    );

-- Searches policies
-- Users can access searches in their organization
CREATE POLICY "Users can access org searches" ON public.searches
    FOR ALL
    USING (org_id = get_current_org_id());

-- Parcels policies  
-- Users can access parcels for their organization
CREATE POLICY "Users can access org parcels" ON public.parcels
    FOR ALL
    USING (org_id = get_current_org_id());

-- Building footprints policies
CREATE POLICY "Users can access org building footprints" ON public.building_footprints
    FOR ALL
    USING (org_id = get_current_org_id());

-- Zoning rules policies
CREATE POLICY "Users can access org zoning rules" ON public.zoning_rules
    FOR ALL
    USING (org_id = get_current_org_id());

-- Derived buildable policies
CREATE POLICY "Users can access org buildable data" ON public.derived_buildable
    FOR ALL
    USING (org_id = get_current_org_id());

-- CV artifacts policies
CREATE POLICY "Users can access org CV artifacts" ON public.cv_artifacts
    FOR ALL
    USING (org_id = get_current_org_id());

-- Listings policies
CREATE POLICY "Users can access org listings" ON public.listings
    FOR ALL
    USING (org_id = get_current_org_id());

-- Exports policies
-- Users can access their own exports
CREATE POLICY "Users can access own exports" ON public.exports
    FOR ALL
    USING (
        user_id = get_current_user_id() AND 
        org_id = get_current_org_id()
    );

-- Admins can access all exports in their org
CREATE POLICY "Admins can access org exports" ON public.exports
    FOR SELECT
    USING (
        org_id = get_current_org_id() AND
        is_current_user_admin()
    );

-- Audit logs policies
-- Users can view audit logs for their own actions
CREATE POLICY "Users can view own audit logs" ON public.audit_logs
    FOR SELECT
    USING (
        user_id = get_current_user_id() AND 
        org_id = get_current_org_id()
    );

-- Admins can view all audit logs in their org
CREATE POLICY "Admins can view org audit logs" ON public.audit_logs
    FOR SELECT
    USING (
        org_id = get_current_org_id() AND
        is_current_user_admin()
    );

-- System/service role policies for data ingestion
-- Create a service role for data ingestion that bypasses RLS
CREATE ROLE service_role;
GRANT USAGE ON SCHEMA public TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- Allow service role to bypass RLS
ALTER TABLE public.parcels FORCE ROW LEVEL SECURITY;
ALTER TABLE public.building_footprints FORCE ROW LEVEL SECURITY;

-- Service role policies (bypasses RLS for ingestion)
CREATE POLICY "Service role full access" ON public.parcels
    FOR ALL
    TO service_role
    USING (true);

CREATE POLICY "Service role full access" ON public.building_footprints
    FOR ALL
    TO service_role
    USING (true);

-- Grant execute permissions on helper functions
GRANT EXECUTE ON FUNCTION get_current_org_id() TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_current_user_id() TO PUBLIC;
GRANT EXECUTE ON FUNCTION is_current_user_admin() TO PUBLIC;

-- Comments for documentation
COMMENT ON FUNCTION get_current_org_id() IS 'Gets the current organization ID from JWT custom claims';
COMMENT ON FUNCTION get_current_user_id() IS 'Gets the current user ID from JWT custom claims';
COMMENT ON FUNCTION is_current_user_admin() IS 'Checks if the current user has admin/owner role';

-- Create indexes to support RLS policy queries
CREATE INDEX IF NOT EXISTS idx_users_org_id_role ON public.users(org_id, role);
CREATE INDEX IF NOT EXISTS idx_users_id_org_id ON public.users(id, org_id);