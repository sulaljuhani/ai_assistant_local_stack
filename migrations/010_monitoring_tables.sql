-- =============================================================================
-- Migration 010: Monitoring & Backup Tables
-- =============================================================================
-- Purpose: Add tables for backup logs and health check monitoring
-- Created: 2025-11-19 (Phase 2)
-- =============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Backup Log Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS backup_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    backup_type VARCHAR(50) NOT NULL,  -- automated_daily, manual, etc.
    backup_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,  -- completed, failed, in_progress
    backup_path TEXT NOT NULL,
    file_size_mb NUMERIC(10, 2),
    duration_seconds INTEGER,
    notes TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for backup_log
CREATE INDEX IF NOT EXISTS idx_backup_log_user_id ON backup_log(user_id);
CREATE INDEX IF NOT EXISTS idx_backup_log_backup_date ON backup_log(backup_date DESC);
CREATE INDEX IF NOT EXISTS idx_backup_log_status ON backup_log(status);

-- =============================================================================
-- Health Checks Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS health_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    check_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_services INTEGER NOT NULL,
    healthy_count INTEGER NOT NULL,
    down_count INTEGER NOT NULL,
    all_healthy BOOLEAN NOT NULL,
    details JSONB NOT NULL,  -- Array of service check results
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for health_checks
CREATE INDEX IF NOT EXISTS idx_health_checks_user_id ON health_checks(user_id);
CREATE INDEX IF NOT EXISTS idx_health_checks_check_time ON health_checks(check_time DESC);
CREATE INDEX IF NOT EXISTS idx_health_checks_all_healthy ON health_checks(all_healthy);

-- Index for querying recent health issues
CREATE INDEX IF NOT EXISTS idx_health_checks_failures
    ON health_checks(check_time DESC)
    WHERE all_healthy = false;

-- =============================================================================
-- Comments
-- =============================================================================
COMMENT ON TABLE backup_log IS 'Logs all backup operations (automated and manual)';
COMMENT ON COLUMN backup_log.backup_type IS 'Type of backup: automated_daily, manual, etc.';
COMMENT ON COLUMN backup_log.status IS 'Status: completed, failed, in_progress';

COMMENT ON TABLE health_checks IS 'Monitors health of all system services every 5 minutes';
COMMENT ON COLUMN health_checks.details IS 'JSONB array containing status of each service';

-- =============================================================================
-- Grant Permissions
-- =============================================================================
-- Grant permissions to the application user
-- Note: Replace 'aistack_user' with your actual database user if different

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aistack_user') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON backup_log TO aistack_user;
        GRANT SELECT, INSERT, UPDATE, DELETE ON health_checks TO aistack_user;
    END IF;
END $$;

-- =============================================================================
-- Cleanup old records function
-- =============================================================================
CREATE OR REPLACE FUNCTION cleanup_old_monitoring_data()
RETURNS void AS $$
BEGIN
    -- Delete health checks older than 30 days
    DELETE FROM health_checks
    WHERE check_time < CURRENT_TIMESTAMP - INTERVAL '30 days';

    -- Delete backup logs older than 90 days
    DELETE FROM backup_log
    WHERE backup_date < CURRENT_TIMESTAMP - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_monitoring_data() IS 'Cleanup old health check and backup log records';

-- =============================================================================
-- Migration Complete
-- =============================================================================
