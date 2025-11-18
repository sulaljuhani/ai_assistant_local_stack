-- Migration 008: n8n Database Setup
-- AI Stack - Create separate database for n8n workflows

-- Note: This migration creates a separate database for n8n
-- n8n will auto-create its own tables, we just need to ensure the database exists

-- Create n8n database (if not exists)
SELECT 'CREATE DATABASE n8n'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'n8n')\gexec

-- Grant privileges to aistack_user
GRANT ALL PRIVILEGES ON DATABASE n8n TO aistack_user;

-- Connect to n8n database and create schema
\c n8n

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO aistack_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO aistack_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO aistack_user;

-- n8n will create these tables automatically on first run:
-- - credentials
-- - execution_entity
-- - tag_entity
-- - webhook_entity
-- - workflow_entity
-- - workflow_statistics
-- - settings
-- And more...

-- Add comments for documentation
COMMENT ON DATABASE n8n IS 'n8n workflow automation database - managed by n8n, do not modify manually';

-- Return to main database
\c aistack
