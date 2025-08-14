-- pg-boss job queue schema for background processing
-- This creates the necessary tables for pg-boss to manage job queues

-- Create pgboss schema
CREATE SCHEMA IF NOT EXISTS pgboss;

-- Grant usage to authenticated users
GRANT USAGE ON SCHEMA pgboss TO authenticated, service_role;

-- The pg-boss library will create its own tables, but we need to ensure permissions
-- and set up some custom job tracking tables

-- Create job_progress table for tracking long-running jobs
CREATE TABLE IF NOT EXISTS public.job_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    
    -- Job identification
    job_id VARCHAR(255) NOT NULL UNIQUE, -- pg-boss job ID
    job_name VARCHAR(255) NOT NULL,
    job_type VARCHAR(100) NOT NULL, -- 'search', 'export', 'ingest'
    
    -- Progress tracking
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    progress_percent INTEGER DEFAULT 0,
    current_stage VARCHAR(100),
    total_stages INTEGER,
    completed_stages INTEGER DEFAULT 0,
    
    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    estimated_completion TIMESTAMPTZ,
    
    -- Results and errors
    result JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Resource tracking
    resource_type VARCHAR(50), -- 'search', 'export', etc.
    resource_id UUID, -- ID of the resource being processed
    
    -- Metadata
    job_data JSONB, -- Original job payload
    processing_stats JSONB, -- Performance metrics
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('queued', 'active', 'completed', 'failed', 'cancelled', 'retry'))
);

-- Create indexes for job_progress
CREATE INDEX IF NOT EXISTS idx_job_progress_job_id ON public.job_progress(job_id);
CREATE INDEX IF NOT EXISTS idx_job_progress_org_user ON public.job_progress(org_id, user_id);
CREATE INDEX IF NOT EXISTS idx_job_progress_status ON public.job_progress(status);
CREATE INDEX IF NOT EXISTS idx_job_progress_type ON public.job_progress(job_type);
CREATE INDEX IF NOT EXISTS idx_job_progress_resource ON public.job_progress(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_job_progress_created_at ON public.job_progress(created_at);

-- Enable RLS on job_progress
ALTER TABLE public.job_progress ENABLE ROW LEVEL SECURITY;

-- RLS policies for job_progress
CREATE POLICY "Users can access own job progress" ON public.job_progress
    FOR ALL
    USING (
        user_id = get_current_user_id() AND 
        org_id = get_current_org_id()
    );

-- Admins can access all job progress in their org
CREATE POLICY "Admins can access org job progress" ON public.job_progress
    FOR SELECT
    USING (
        org_id = get_current_org_id() AND
        is_current_user_admin()
    );

-- Create updated_at trigger for job_progress
CREATE TRIGGER update_job_progress_updated_at BEFORE UPDATE ON public.job_progress
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function to update job progress
CREATE OR REPLACE FUNCTION update_job_progress(
    p_job_id VARCHAR(255),
    p_status VARCHAR(50) DEFAULT NULL,
    p_progress_percent INTEGER DEFAULT NULL,
    p_current_stage VARCHAR(100) DEFAULT NULL,
    p_completed_stages INTEGER DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL,
    p_result JSONB DEFAULT NULL,
    p_processing_stats JSONB DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    updated_rows INTEGER;
BEGIN
    UPDATE public.job_progress 
    SET 
        status = COALESCE(p_status, status),
        progress_percent = COALESCE(p_progress_percent, progress_percent),
        current_stage = COALESCE(p_current_stage, current_stage),
        completed_stages = COALESCE(p_completed_stages, completed_stages),
        error_message = COALESCE(p_error_message, error_message),
        result = COALESCE(p_result, result),
        processing_stats = COALESCE(p_processing_stats, processing_stats),
        started_at = CASE 
            WHEN p_status = 'active' AND started_at IS NULL THEN NOW()
            ELSE started_at 
        END,
        completed_at = CASE 
            WHEN p_status IN ('completed', 'failed', 'cancelled') THEN NOW()
            ELSE completed_at 
        END,
        updated_at = NOW()
    WHERE job_id = p_job_id;
    
    GET DIAGNOSTICS updated_rows = ROW_COUNT;
    RETURN updated_rows > 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission on the update function
GRANT EXECUTE ON FUNCTION update_job_progress TO authenticated, service_role;

-- Create function to clean up old completed jobs
CREATE OR REPLACE FUNCTION cleanup_old_jobs(retention_days INTEGER DEFAULT 7)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete completed/failed jobs older than retention period
    DELETE FROM public.job_progress
    WHERE status IN ('completed', 'failed', 'cancelled')
    AND completed_at < NOW() - INTERVAL '1 day' * retention_days;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Log the cleanup
    INSERT INTO public.audit_logs (
        event_type,
        event_category,
        action,
        description,
        status
    ) VALUES (
        'cleanup',
        'system',
        'Job cleanup completed',
        format('Cleaned up %s old job records older than %s days', deleted_count, retention_days),
        'success'
    );
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission on cleanup function
GRANT EXECUTE ON FUNCTION cleanup_old_jobs TO service_role;

-- Create job queue statistics view
CREATE OR REPLACE VIEW job_queue_stats AS
SELECT 
    org_id,
    job_type,
    status,
    COUNT(*) as count,
    MIN(created_at) as oldest_job,
    MAX(created_at) as newest_job,
    AVG(EXTRACT(EPOCH FROM (COALESCE(completed_at, NOW()) - created_at))) as avg_duration_seconds
FROM public.job_progress
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY org_id, job_type, status;

-- Grant select on the view
GRANT SELECT ON job_queue_stats TO authenticated, service_role;

-- Create indexes to support the view efficiently
CREATE INDEX IF NOT EXISTS idx_job_progress_stats ON public.job_progress(org_id, job_type, status, created_at);

-- Create notification function for job status changes
CREATE OR REPLACE FUNCTION notify_job_status_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Only notify for significant status changes
    IF OLD.status IS DISTINCT FROM NEW.status AND NEW.status IN ('completed', 'failed', 'cancelled') THEN
        PERFORM pg_notify(
            'job_status_change',
            json_build_object(
                'job_id', NEW.job_id,
                'job_type', NEW.job_type,
                'old_status', OLD.status,
                'new_status', NEW.status,
                'org_id', NEW.org_id,
                'user_id', NEW.user_id,
                'resource_id', NEW.resource_id
            )::text
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for job status notifications
CREATE TRIGGER job_status_notification_trigger
    AFTER UPDATE ON public.job_progress
    FOR EACH ROW
    EXECUTE FUNCTION notify_job_status_change();

-- Comments for documentation
COMMENT ON TABLE public.job_progress IS 'Tracks progress of background jobs managed by pg-boss';
COMMENT ON FUNCTION update_job_progress IS 'Updates job progress with new status and metrics';
COMMENT ON FUNCTION cleanup_old_jobs IS 'Cleans up old completed/failed job records';
COMMENT ON VIEW job_queue_stats IS 'Provides statistics on job queue performance by org and type';