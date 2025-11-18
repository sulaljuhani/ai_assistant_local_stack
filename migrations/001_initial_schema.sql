-- Migration 001: Initial Schema Setup
-- AI Stack - PostgreSQL Database Initialization
-- Single-user mode with UUID: 00000000-0000-0000-0000-000000000001

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search optimization

-- Create single user record
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT '00000000-0000-0000-0000-000000000001',
    username TEXT DEFAULT 'default_user',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default user (single-user mode)
INSERT INTO users (id, username)
VALUES ('00000000-0000-0000-0000-000000000001', 'default_user')
ON CONFLICT (id) DO NOTHING;

-- Categories for organizing reminders and notes
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    color TEXT DEFAULT '#3B82F6',  -- Blue default
    icon TEXT DEFAULT '📁',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, name)
);

CREATE INDEX idx_categories_user ON categories(user_id);

-- Insert default categories
INSERT INTO categories (user_id, name, color, icon) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Personal', '#3B82F6', '👤'),
    ('00000000-0000-0000-0000-000000000001', 'Work', '#10B981', '💼'),
    ('00000000-0000-0000-0000-000000000001', 'Health', '#EF4444', '❤️'),
    ('00000000-0000-0000-0000-000000000001', 'Finance', '#F59E0B', '💰'),
    ('00000000-0000-0000-0000-000000000001', 'Learning', '#8B5CF6', '📚')
ON CONFLICT (user_id, name) DO NOTHING;

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

COMMENT ON FUNCTION update_updated_at_column() IS 'Automatically updates updated_at timestamp on row modification';
